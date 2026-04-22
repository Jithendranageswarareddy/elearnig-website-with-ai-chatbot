# Final Benchmark Report

- Embedding backend: `fallback-hash::all-MiniLM-L6-v2`
- Corpus: `80 PDFs x 25 pages x 5 chunks`
- Questions: `20`
- TF-IDF top-1 accuracy: `80.00%`
- Hybrid top-1 accuracy: `80.00%`
- TF-IDF top-5 recall: `100.00%`
- Hybrid top-5 recall: `100.00%`
- Average retrieval latency: `1350.38 ms`
- P95 retrieval latency: `1426.97 ms`
- Average response build latency: `114.71 ms`
- Concept coverage: `100.00%`
- Response quality pass rate: `100.00%`
- Peak traced memory: `147.44 MB`

## Architecture Diagram

```text
Approved Syllabus PDFs
        |
        v
Faculty Upload -> Celery Processing -> Paragraph Chunks -> Chunk Embeddings
        |                     |                 |                 |
        |                     |                 +--> Chunk Concepts
        |                     +--> OCR Fallback                |
        |                     +--> Diagram Extraction          v
        |                                               Knowledge Graph
        |                                                    |
        v                                                    v
Principal Approval ------------------------------> Hybrid Retrieval Pipeline
                                                            |
Student Question -> Query Analysis -> Cache -> Ranked Chunks + Diagrams
                                                            |
                                                            v
                                           Structured PDF-Grounded Answer
```

## Notes

- Retrieval remains restricted to approved syllabus PDFs.
- The benchmark corpus is synthetic and generated inside a rollback-only transaction.
- Semantic ranking quality depends on the embedding backend available at runtime.
