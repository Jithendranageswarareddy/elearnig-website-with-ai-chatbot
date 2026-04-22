import json
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from chatbot.models import GeneratedQuestion
from chatbot.services.self_improving_service import (
    generate_autonomous_questions,
    run_self_learning_cycle,
)


class Command(BaseCommand):
    help = "Run autonomous AI library training loop using retrieval-augmented self-learning."

    def add_arguments(self, parser):
        parser.add_argument("--generate-batch", type=int, default=300, help="Max chunks scanned for question generation per cycle.")
        parser.add_argument("--train-batch", type=int, default=20, help="Questions processed per learning cycle.")
        parser.add_argument("--quality-threshold", type=int, default=7, help="Minimum quality score required for answer cache updates.")
        parser.add_argument("--sleep-ms", type=int, default=250, help="Sleep duration between cycles to protect low-resource machines.")
        parser.add_argument(
            "--output",
            default=str(Path(settings.BASE_DIR) / "test_logs" / "ai_library_training_report.json"),
            help="Path to write training summary JSON.",
        )

    def handle(self, *args, **options):
        generate_batch = max(1, int(options["generate_batch"]))
        train_batch = max(1, int(options["train_batch"]))
        quality_threshold = max(1, int(options["quality_threshold"]))
        sleep_ms = max(0, int(options["sleep_ms"]))

        started = time.perf_counter()
        created_questions = generate_autonomous_questions(batch_size=generate_batch)
        self.stdout.write(self.style.SUCCESS(f"Generated questions: {created_questions}"))

        cycle_reports = []
        total_processed = 0
        total_accepted = 0

        while True:
            remaining = GeneratedQuestion.objects.filter(is_processed=False).count()
            if remaining <= 0:
                break

            cycle_index = len(cycle_reports) + 1
            cycle_summary = run_self_learning_cycle(batch_size=train_batch, quality_threshold=quality_threshold)
            processed = int(cycle_summary.get("processed", 0))
            accepted = int(cycle_summary.get("accepted", 0))
            total_processed += processed
            total_accepted += accepted

            cycle_reports.append(
                {
                    "cycle": cycle_index,
                    "processed": processed,
                    "accepted": accepted,
                    "average_quality": cycle_summary.get("average_quality", 0.0),
                    "remaining_after_cycle": max(0, remaining - processed),
                    "items": cycle_summary.get("results", []),
                }
            )

            self.stdout.write(
                " | ".join(
                    [
                        f"cycle={cycle_index}",
                        f"processed={processed}",
                        f"accepted={accepted}",
                        f"avg_quality={cycle_summary.get('average_quality', 0.0)}",
                        f"remaining={max(0, remaining - processed)}",
                    ]
                )
            )

            if processed <= 0:
                break

            if sleep_ms > 0:
                time.sleep(sleep_ms / 1000.0)

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        remaining = GeneratedQuestion.objects.filter(is_processed=False).count()
        total_questions = GeneratedQuestion.objects.count()

        report = {
            "generated_at": timezone.now().isoformat(),
            "command": "python manage.py run_ai_library_training",
            "settings": {
                "generate_batch": generate_batch,
                "train_batch": train_batch,
                "quality_threshold": quality_threshold,
                "sleep_ms": sleep_ms,
            },
            "summary": {
                "total_questions": total_questions,
                "created_questions": created_questions,
                "processed_questions": total_processed,
                "accepted_answers": total_accepted,
                "remaining_questions": remaining,
                "elapsed_ms": elapsed_ms,
            },
            "cycles": cycle_reports,
        }

        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Training report written to {output_path}"))
        self.stdout.write(
            " | ".join(
                [
                    f"Total={total_questions}",
                    f"Processed={total_processed}",
                    f"Accepted={total_accepted}",
                    f"Remaining={remaining}",
                ]
            )
        )
