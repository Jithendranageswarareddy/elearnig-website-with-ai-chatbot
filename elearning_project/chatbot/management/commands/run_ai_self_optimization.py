import json
import time
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from chatbot.models import GeneratedQuestion, RetrievalStrategyCache
from chatbot.services.self_improving_service import (
    generate_autonomous_questions,
    run_self_optimization_iteration,
)


class Command(BaseCommand):
    help = "Run autonomous self-optimization loop for AI Digital Library retrieval and synthesis parameters."

    def add_arguments(self, parser):
        parser.add_argument("--max-iterations", type=int, default=100)
        parser.add_argument("--batch-size", type=int, default=10)
        parser.add_argument("--quality-threshold", type=float, default=7.0)
        parser.add_argument("--target-average", type=float, default=8.5)
        parser.add_argument("--sleep-seconds", type=float, default=0.1)
        parser.add_argument("--requeue-limit", type=int, default=50)
        parser.add_argument(
            "--output",
            default=str(Path(settings.BASE_DIR) / "test_logs" / "self_optimization_report.json"),
            help="Path for self optimization JSON report",
        )

    def handle(self, *args, **options):
        max_iterations = max(1, int(options["max_iterations"]))
        batch_size = max(1, int(options["batch_size"]))
        quality_threshold = float(options["quality_threshold"])
        target_average = float(options["target_average"])
        sleep_seconds = max(0.0, float(options["sleep_seconds"]))
        requeue_limit = max(1, int(options["requeue_limit"]))

        if GeneratedQuestion.objects.count() == 0:
            created = generate_autonomous_questions(batch_size=400)
            self.stdout.write(self.style.SUCCESS(f"Generated initial questions: {created}"))

        pending = GeneratedQuestion.objects.filter(is_processed=False).count()
        if pending == 0:
            requeue_ids = list(
                GeneratedQuestion.objects.order_by("last_score", "attempt_count", "id").values_list("id", flat=True)[:requeue_limit]
            )
            requeued = GeneratedQuestion.objects.filter(id__in=requeue_ids).update(is_processed=False)
            self.stdout.write(self.style.WARNING(f"No pending questions found. Requeued {requeued} questions for optimization."))

        iteration_reports = []
        cumulative_scores = []
        improved_concepts = set()

        for iteration in range(1, max_iterations + 1):
            remaining = GeneratedQuestion.objects.filter(is_processed=False).count()
            if remaining <= 0:
                break

            summary = run_self_optimization_iteration(batch_size=batch_size, quality_threshold=quality_threshold)
            processed = int(summary.get("processed", 0))
            if processed <= 0:
                break

            for item in summary.get("results", []):
                cumulative_scores.append(float(item.get("score", 0)))
                if item.get("acceptable"):
                    improved_concepts.add(str(item.get("concept", "")).strip().lower())

            cumulative_average = round(sum(cumulative_scores) / max(1, len(cumulative_scores)), 2)
            iteration_reports.append(
                {
                    "iteration": iteration,
                    "processed": processed,
                    "average_score": summary.get("average_score", 0.0),
                    "cumulative_average_score": cumulative_average,
                    "improved": summary.get("improved", 0),
                    "remaining_after_iteration": max(0, remaining - processed),
                    "results": summary.get("results", []),
                }
            )

            self.stdout.write(
                " | ".join(
                    [
                        f"iter={iteration}",
                        f"processed={processed}",
                        f"iter_avg={summary.get('average_score', 0.0)}",
                        f"cum_avg={cumulative_average}",
                        f"remaining={max(0, remaining - processed)}",
                    ]
                )
            )

            if cumulative_average >= target_average:
                break

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        total_iterations = len(iteration_reports)
        overall_average = round(sum(cumulative_scores) / max(1, len(cumulative_scores)), 2) if cumulative_scores else 0.0
        best_strategies = [
            {
                "concept": row.concept,
                "best_context_chunk_count": row.best_context_chunk_count,
                "best_keyword_weight": row.best_keyword_weight,
                "best_semantic_weight": row.best_semantic_weight,
                "best_rerank_strategy": row.best_rerank_strategy,
                "confidence_score": row.confidence_score,
            }
            for row in RetrievalStrategyCache.objects.order_by("-confidence_score", "concept")[:200]
        ]

        report = {
            "generated_at": timezone.now().isoformat(),
            "command": "python manage.py run_ai_self_optimization",
            "settings": {
                "max_iterations": max_iterations,
                "batch_size": batch_size,
                "quality_threshold": quality_threshold,
                "target_average": target_average,
                "sleep_between_iterations": sleep_seconds,
                "requeue_limit": requeue_limit,
            },
            "summary": {
                "iterations_run": total_iterations,
                "average_score": overall_average,
                "best_strategies_found": len(best_strategies),
                "concepts_improved": sorted([item for item in improved_concepts if item]),
                "remaining_questions": GeneratedQuestion.objects.filter(is_processed=False).count(),
            },
            "iteration_reports": iteration_reports,
            "best_strategies_found": best_strategies,
        }
        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Self optimization report written to {output_path}"))
        self.stdout.write(
            " | ".join(
                [
                    f"iterations_run={total_iterations}",
                    f"average_score={overall_average}",
                    f"best_strategies_found={len(best_strategies)}",
                    f"concepts_improved={len(improved_concepts)}",
                ]
            )
        )

        self.stdout.write("Running evaluator after optimization...")
        try:
            call_command("evaluate_self_improving_pipeline")
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Evaluator skipped (LLM unavailable): {exc.__class__.__name__}: {exc}"))
