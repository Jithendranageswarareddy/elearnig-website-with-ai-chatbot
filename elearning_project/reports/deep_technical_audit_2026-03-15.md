# Deep Technical Audit — Curriculum Chatbot (2026-03-15)

## Executive Summary
This system is a strong advanced academic RAG implementation with practical guardrails, deterministic fallback behavior, and measurable retrieval consistency. It is **not yet production-hardened** due to high end-to-end latency variance, limited eval-metric breadth, and missing policy-grade safety/observability controls.

**Weighted maturity score:** **7.1 / 10**

---

## 1) Architecture & Service Boundaries
**Observed:** request orchestration in `views.py`, modular services for retrieval/synthesis/retries, streaming helpers, cache/rate-limit wrappers.

**Strengths**
- Clean staged flow: ingestion → index → retrieval → synthesis → stream.
- Practical decomposition across `search_service`, `answer_synthesis_service`, `self_improving_service`, `chat_stream_service`.

**Gaps**
- Orchestration remains app-coupled instead of pipeline/graph orchestration.
- No formal interface contracts for retriever/reranker/generator swappability.

**Score:** 7.2/10

## 2) Data Model & Knowledge Graph Fitness
**Observed:** rich domain model (`ReferencePDF`, `PDFPageChunk`, `ChunkEmbedding`, concept/link entities, chat history).

**Strengths**
- Good traceability from answers back to source pages.
- Concept graph persistence supports future semantic navigation.

**Gaps**
- Query-time retrieval does not heavily exploit graph edges/relations.
- Limited use of concept confidence/edge weights for ranking.

**Score:** 7.8/10

## 3) Ingestion, OCR, and Chunking Quality
**Observed:** OCR fallback and chunk extraction pipeline in `pdf_processor.py`; image extraction is integrated.

**Strengths**
- Robust against low-quality PDFs and scanned text.
- Handles mixed content and preserves page-level provenance.

**Gaps**
- Chunking is mostly heuristic and page/paragraph based.
- No adaptive chunking strategy per section type (definitions vs examples vs formulas).

**Score:** 7.0/10

## 4) Embedding Strategy & Failure Modes
**Observed:** sentence-transformer embedding with deterministic hash fallback path.

**Strengths**
- High availability on constrained hardware.
- Retrieval pipeline remains functional when embedding backend is unavailable.

**Gaps**
- Hash fallback reduces semantic ranking quality ceiling.
- No embedding drift checks or benchmark thresholds per model/version.

**Score:** 6.6/10

## 5) Retrieval, Ranking, and Context Selection
**Observed:** hybrid TF-IDF + semantic scoring, per-PDF candidate balancing, diversity checks, rerank pass.

**Strengths**
- Strong baseline retrieval behavior for educational corpus.
- Top-5 recall reached 100% in benchmark artifact.

**Gaps vs modern best practice**
- Missing query rewriting/planner stage.
- Missing learned reranker (cross-encoder) and citation-faithfulness rerank objective.

**Score:** 7.4/10

## 6) Prompting, Synthesis, and Output Control
**Observed:** sectioned markdown synthesis, heading-noise suppression, deterministic fallback generation path.

**Strengths**
- Grounded structured output is enforced.
- Heading leakage and slide-noise contamination substantially mitigated.

**Gaps**
- Limited claim-level verification before final text.
- No planner/executor split for complex multi-hop educational questions.

**Score:** 7.1/10

## 7) Self-Improving Retry Pipeline
**Observed:** strategy-based retries, quality gating, model selection/fallback, run logging in `self_improving_service.py`.

**Strengths**
- Clear retry policy and quality acceptance threshold.
- Good telemetry payload (`retry_count`, `context_chunk_count`, `final_quality_score`, `final_model`).

**Gaps**
- Retry strategies are fixed rather than policy-learned.
- No explicit retrieval-critique/correction cycle (CRAG-style) before synthesis.

**Score:** 7.5/10

## 8) Evaluation Framework & Scientific Rigor
**Observed:** nightly evaluator command with automated question generation and stream schema checks.

**Strengths**
- Repeatable local evaluation workflow and persisted JSON reports.
- Captures generation metadata and quality checks per test case.

**Gaps**
- Metric set remains mostly heuristic; lacks RAGAS-style faithfulness/context precision/context recall.
- No statistical confidence intervals or regression gates in CI.

**Score:** 7.3/10

## 9) Streaming Protocol & Client UX Reliability
**Observed:** NDJSON token streaming + normalized done payload in `chat_stream_service.py`.

**Strengths**
- Simple, robust transport model for progressive rendering.
- Done payload includes references/concept links/follow-up suggestions.

**Gaps**
- Limited error taxonomy for degraded mode handling on client.
- No backpressure signaling or adaptive stream chunk policy by latency class.

**Score:** 7.0/10

## 10) Performance, Capacity, and Latency
**Evidence**
- Benchmark report: retrieval latency ~1.35s avg, p95 ~1.43s.
- Nightly logs: end-to-end generation can exceed 100s on local CPU configuration.

**Strengths**
- Retrieval speed is acceptable for local prototype scale.
- Deterministic mode avoids hard model outages.

**Gaps**
- High first-token/overall response latency under local model path.
- No SLA-tiered response budget or adaptive truncation by target latency.

**Score:** 5.9/10

## 11) Security, Safety, and Policy Controls
**Observed:** auth, approval-based corpus gating, rate limiting, conservative local model strategy.

**Strengths**
- Exposure is reduced through approved-syllabus-only retrieval.
- Basic abuse controls are present.

**Gaps**
- Prompt-injection defense is not yet policy-layer complete.
- Missing formal output safety classifier and high-risk query policy branch.

**Score:** 6.8/10

## 12) Reliability, Observability, and Operations
**Observed:** JSON logs and evaluator artifacts are available; deterministic fallback helps reliability.

**Strengths**
- Useful troubleshooting artifacts already generated in `test_logs/`.
- Retry traces improve post-incident diagnosis.

**Gaps**
- No centralized metrics/alerts dashboard.
- No formal runbook with SLOs and incident response thresholds.

**Score:** 6.7/10

## 13) Ecosystem Benchmark Position (OpenAI/LangChain/LlamaIndex/Academic)
**Against modern baseline frameworks**
- **Ahead of basic tutorial-grade RAG** due to integrated retries, structured synthesis, and evaluator automation.
- **Behind production-grade stacks** on advanced retrieval planning, eval standardization, and policy observability.
- **Partially aligned with Self-RAG/CRAG concepts** but not yet implementing full critique/retrieval-correction loops.

**Estimated maturity percentile:** 60–70th among serious academic/early production RAG systems.

**Score:** 6.9/10

## 14) Modernization Roadmap (Prioritized)
### Phase A (1–2 weeks) — Highest ROI
1. Add query rewriting and retrieval planner stage.
2. Add cross-encoder reranking for top-N retrieved chunks.
3. Enforce hard latency budget with graceful degrade path.

### Phase B (3–6 weeks)
1. Add faithfulness/context precision/context recall metrics (RAGAS-like).
2. Add automated regression gates for evaluator metrics.
3. Add dashboard metrics: p50/p95 latency, retry causes, fallback rate, grounding ratio.

### Phase C (6–10 weeks)
1. Add retrieval critique/correction loop (CRAG-inspired).
2. Add graph-aware retrieval fusion using concept relations.
3. Add policy-layer safety classifier and risk-tier routing.

**Expected impact if executed**
- +10–18% answer stability/quality on long-tail queries.
- 30–50% improvement in latency predictability.
- Strong reduction in hallucination risk under retrieval ambiguity.

---

## Consolidated Scorecard
| Area | Score |
|---|---:|
| Architecture | 7.2 |
| Data Model | 7.8 |
| Ingestion/OCR | 7.0 |
| Embeddings | 6.6 |
| Retrieval/Ranking | 7.4 |
| Synthesis | 7.1 |
| Self-Improving Loop | 7.5 |
| Evaluation | 7.3 |
| Streaming UX | 7.0 |
| Performance | 5.9 |
| Security/Safety | 6.8 |
| Reliability/Ops | 6.7 |
| Ecosystem Positioning | 6.9 |
| Roadmap Readiness | 8.0 |

**Weighted overall:** **7.1 / 10**

## Evidence Used
- `reports/final_benchmark_report.md`
- `test_logs/nightly_pipeline_report.json`
- `test_logs/self_improving_pipeline.json`
- `chatbot/services/search_service.py`
- `chatbot/services/answer_synthesis_service.py`
- `chatbot/services/self_improving_service.py`
- `chatbot/services/pdf_processor.py`
- `chatbot/services/embedding_service.py`
- `chatbot/services/chat_stream_service.py`
