# Production Four-Variant MP-KG-RAG Run Design

## Goal

Generate complete, resumable outputs for all 1,550 records in `dataset (1).xlsx` using one pinned `unsloth/Qwen3.5-4B` 4-bit generator and four variants: zero-shot, few-shot, KG-RAG, and MP-KG-RAG.

## Isolation and inputs

- Preserve the existing local and remote runs.
- Stage this run under a new remote `mp_kg_rag_production_1550` directory.
- Treat `Final_Dataset` as canonical after verifying that the duplicate workbook sheet is identical.
- Record SHA-256 identities for the input workbook, corpus manifest, code, prompts, model revisions, and environment.

## Generation architecture

- Keep one generator resident on the single RTX6000 Pro GPU; do not load four competing model copies.
- Batch records by prompt-length bucket and tune microbatch size after a GPU smoke benchmark.
- Precompute corpus extraction, semantic KG, query signatures, and retrieval evidence once.
- Release BGE-M3 and reranker GPU allocations before generation unless measured throughput proves concurrent residency beneficial.
- Use isolated, append-only JSONL checkpoints per variant and shard so interrupted runs resume safely.

## Qwen thinking output

- Enable Qwen3.5 thinking for the four user-facing generation variants.
- Parse model-emitted `<think>...</think>` into a separate `reasoning_content` field while retaining the final JSON answer separately.
- Preserve the original raw generation, reasoning token count, answer token count, truncation state, parse status, and repair history.
- For MP-KG-RAG, retain per-perspective reasoning, planner reasoning, grounding-repair reasoning when invoked, and final-synthesis reasoning.
- Keep extraction, entity-linking, schema-repair, and evaluator calls in non-thinking mode unless separately required; they are pipeline machinery rather than compared generation variants.

## Output workbook

Produce one styled XLSX with frozen panes, filters, wrapped narrative columns, explicit run metadata, and these sheets:

1. `Outputs`: one row per input record with all four final counter-narratives and status columns.
2. `Zero-Shot Trace`: emitted reasoning, raw output, token counts, parsing, and validation.
3. `Few-Shot Trace`: emitted reasoning plus frozen example IDs and prompt revision.
4. `KG-RAG Trace`: emitted reasoning, query signature, evidence ledger, KG paths, citations, and validation.
5. `MP-KG-RAG Trace`: perspective, planner, synthesis, and optional repair reasoning with evidence and validation.
6. `Evidence Ledger`: normalized evidence IDs, source metadata, spans, hashes, and graph paths.
7. `Run Manifest`: model/environment/configuration identities and performance statistics.
8. `Quality Summary`: completeness, parse, citation, grounding, safety, latency, and throughput summaries.

The original five input columns remain unchanged. JSONL and Parquet artifacts remain the canonical machine-readable checkpoints; XLSX is the presentation export.

## Quality and execution gates

- CPU stage: inventory the VM, transfer only changed files, create an isolated environment, verify hashes, and download pinned model/corpus dependencies.
- GPU stage: verify the exact GPU, CUDA, effective 4-bit modules, and memory before inference.
- Run representative smoke rows across categories and targets before all 1,550 records.
- Reject malformed structured output, unknown citations, unsupported factual claims, stale checkpoints, duplicate/missing IDs, or truncated reasoning without an explicit status.
- Optimize measured throughput while preserving these gates; no row-wise claim that one method is inherently better is made without evaluation evidence.

## Completion criteria

- Exactly 1,550 unique IDs have terminal records for each of four variants.
- Every accepted result has a separately parsed final answer and reasoning field.
- RAG variants have canonical evidence ledgers and valid citation references.
- Final XLSX, JSONL checkpoints, manifests, logs, and quality summaries pass structural verification and hash checks.
