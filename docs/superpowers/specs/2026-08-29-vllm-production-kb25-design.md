# VLLM Production Pipeline and KB25 Expansion Design

## Purpose

Produce a validated Excel workbook for all 1,550 rows in `dataset (1).xlsx`
using one pinned Qwen3.5-4B base-model revision in 4-bit for four progressively
stronger variants: zero-shot, few-shot, KG-RAG, and MP-KG-RAG. Preserve the
model-emitted reasoning separately from final answers for every variant that
uses reasoning, and expand the existing knowledge corpus with the 25-source
downloader pack at
`/Users/pika/Downloads/MP_KG_RAG_KB_25_downloader_pack.zip`.

The production path must be fast enough to use an NVIDIA RTX PRO 6000
effectively, resumable across interruptible-instance restarts, and fail closed
when corpus, model, schema, checkpoint, citation, or output identities do not
match.

## Evidence from the Abandoned Smoke Path

The Transformers/Unsloth smoke process was stopped without deleting its logs or
partial artifacts. Its first 24-record mention-discovery batch took 8 minutes
9 seconds while the GPU used roughly 11 GiB and 12--24% compute. Eleven of the
first 17 persisted rows were `semantic_invalid`, primarily because 384 output
tokens were insufficient for long mention arrays. At that rate the
mention-discovery pass alone was projected to take about 18 hours and could not
meet its own 98% validation gate.

The root causes were architectural rather than a single batch-size defect:

- Qwen3.5 used its slow PyTorch linear-attention fallback because the required
  optimized path was unavailable.
- Long, unconstrained mention lists made valid completion dependent on an
  arbitrary output-token cap.
- Corpus caches lived inside individual run directories and were coupled to
  dataset selection, preventing safe reuse between smoke and production.
- Query signatures were generated serially.
- The notebook combined corpus acquisition, extraction, graph construction,
  generation, evaluation, and export into one failure chain.

## Approved Architecture

Use a staged hybrid pipeline with a vLLM inference service.

1. Acquire, validate, merge, and freeze the corpus.
2. Extract and chunk all accepted documents on CPU.
3. Embed every accepted chunk and identify bounded entity candidates
   deterministically.
4. Use Qwen only for bounded structured semantic claims on frozen, relevant
   chunks; do not run a separate unbounded generative mention-discovery pass.
5. Freeze the semantic KG and its evidence ledger.
6. Generate query signatures in concurrent batches.
7. Generate all four counter-narrative variants in progressive order.
8. Evaluate, validate, and export one final workbook plus machine-readable
   manifests.

Each stage has a focused interface and an identity-addressed artifact directory.
The corpus and KG stages are independent of smoke/full dataset selection. A
completed corpus artifact can therefore be reused by any run whose corpus,
model, prompt, schema, and code identities match exactly.

## Knowledge-Base Expansion

The supplied ZIP contains a 25-row source catalog and downloader programs, not
the PDFs themselves. Its archive SHA-256 is
`a9661a599670e68dce5a915863c7b11e2752a5405bbd6746d1bafc194e5c5227`.

The pipeline will:

- extract the source catalog and downloader into a controlled staging area;
- download all 25 catalogued PDFs with bounded concurrency and retries;
- require a PDF signature, nontrivial byte size, successful parser open, and an
  exact parsed page count;
- record URL, publisher, title, year, requested filename, byte size, SHA-256,
  parsed page count, status, and error for every catalog row;
- quarantine failed, HTML, interstitial, corrupt, encrypted-unreadable, and
  implausibly short downloads;
- merge accepted documents into the existing 95-file corpus;
- deduplicate document content by SHA-256 while retaining every source URL and
  catalog record as provenance on the canonical document;
- treat declared page counts as advisory and parsed page counts as
  authoritative; and
- freeze a canonical corpus manifest before chunking.

No quarantined file may contribute evidence. Duplicate provenance may appear in
the source audit but must not duplicate retrieval chunks or inflate evidence
rankings.

## Corpus Processing and Semantic KG

Accepted PDFs are extracted page by page. Chunks are page-aware, approximately
500--900 tokens with about 100 tokens of overlap, and never cross a document
boundary. Each chunk retains at least:

- canonical document and source identifiers;
- publisher, title, year, jurisdiction, language, document type, authority
  tier, topics, and source URLs;
- page number, chunk index, character/token spans, and text;
- document, page-text, and chunk SHA-256 values; and
- extraction/filter status and audit reasons.

All accepted chunks are embedded. A frozen selection policy chooses chunks for
semantic-claim extraction using authority, dataset-independent hate-speech and
SOGIESC topic coverage, and embedding relevance to a versioned neutral query
set. Selection thresholds, selected and excluded chunk IDs, component scores,
and reasons are persisted before Qwen inference. This avoids silently extracting
only evidence that favors a particular experimental variant.

Entity candidates are derived without generative output from reviewed source
metadata, known publishers and organizations, dataset-independent controlled
vocabulary, citations, and exact text spans. Candidate lists are bounded and
included in each claim-extraction request. Qwen returns JSON-schema-constrained
claims that reference only supplied candidates and chunk spans. Invalid outputs
receive one bounded repair attempt and then enter an explicit quarantine.

The KG build requires frozen minimum coverage, linkage, parse-success, and
citation-resolvability gates. Every accepted evidence edge resolves to a source,
page, chunk, span, and hash.

## Inference Service

Serve the pinned official Qwen3.5-4B revision through a pinned vLLM environment
on the RTX PRO 6000. Apply 4-bit weight quantization at runtime from that exact
revision unless a separately pinned 4-bit artifact is proven bit-for-bit tied to
the same base revision. Record the quantization configuration, effective weight
types, vLLM version, CUDA/driver information, model revision, tokenizer revision,
and launch arguments in the environment manifest.

The service uses:

- continuous batching with a bounded request queue;
- JSON-schema structured outputs for extraction, signatures, plans, and final
  answers;
- the Qwen3 reasoning parser for separate reasoning and final content;
- explicit per-request thinking-token budgets;
- prefix caching when vLLM reports it active;
- conservative initial GPU-memory utilization, raised only after measured
  smoke stability; and
- deterministic decoding for extraction/signatures and frozen sampling
  parameters for counter-narratives.

The client submits asynchronous bounded-concurrency requests. Concurrency is
tuned from throughput, queue delay, latency percentiles, parse success, and
memory headroom. GPU utilization alone is not an optimization objective.

## Generation Variants

All variants use the same pinned base model, tokenizer, decoding family, input
record identity, target/category fields, safety contract, and maximum final
answer budget. Variant-specific additional information is explicit:

1. **Zero-shot:** instruction and input only.
2. **Few-shot:** the zero-shot information plus a frozen, contamination-safe
   example set whose IDs and hashes are recorded.
3. **KG-RAG:** the shared input plus evidence selected from the frozen KG under
   the planned retrieval policy and an evidence ledger.
4. **MP-KG-RAG:** the same KG evidence plus five bounded perspective analyses,
   a synthesis plan, and final synthesis.

Thinking-enabled generation stores the model-emitted reasoning content verbatim
as returned by the inference service, separate from final content. Each trace
records reasoning and answer token counts, stop reason, truncation status,
latency, request ID, retry count, sampling parameters, and schema status.

The system does not fabricate or rewrite scores to guarantee that every
individual row follows a preferred ranking. “Each better than the previous” is
an aggregate experimental acceptance condition:

- few-shot must match or exceed zero-shot on the frozen composite quality gate;
- KG-RAG must improve grounding and citation validity over few-shot; and
- MP-KG-RAG must improve perspective coverage and the composite gate over
  KG-RAG.

Per-row regressions remain visible. If an aggregate gate fails, the run is
reported as failed and parameters may change only through a new versioned run
identity and a new smoke evaluation.

## Checkpoints and Identity

Artifacts are separated into corpus, KG, dataset-run, evaluation, and export
namespaces. Their identities include only the inputs that semantically affect
them.

- Corpus identity: accepted document hashes, extraction/chunking revisions, and
  audit-policy revision.
- Semantic identity: corpus identity, selected chunk IDs, base model/tokenizer
  revisions, quantization contract, prompt/schema revisions, and semantic code
  hash.
- Dataset identity: workbook/sheet hash, selected row identities, category
  policy, and split/shard assignment.
- Generation identity: dataset identity, semantic identity when applicable,
  variant, prompt revision, decoding parameters, and code hash.
- Evaluation identity: generation artifacts, metric models/revisions,
  thresholds, and evaluation code hash.

Checkpoints are append-only JSONL records with file locking, per-record identity,
and atomic summary manifests. Duplicate identical records are idempotent;
conflicting records fail closed. Resume validates every identity before reusing
work. Partial files never advertise a complete state.

## Smoke, Tuning, and Production

A deterministic 12-row stratified smoke set covers categories, available
languages, input-length bands, and representative targets. The smoke run uses
the already-frozen corpus/KG artifacts and exercises all four variants.

The smoke gate requires:

- all 48 final narratives present and schema-valid;
- required reasoning traces and MP perspective/plan traces present;
- valid evidence resolution for every KG citation;
- no checkpoint conflicts or identity mismatches;
- acceptable parse, safety, language, and truncation rates;
- measured stable VRAM headroom without OOM; and
- a credible throughput/ETA estimate for 1,550 rows.

Only after the smoke passes does the 1,550-row production run begin. Monitoring
records requests and tokens per second, queue depth, latency percentiles, GPU
memory/utilization/power, completed/failed/retried rows, parse status, and ETA.
Concurrency reductions after OOM do not change semantic run identity; prompt,
model, decoding, or quality-threshold changes do.

## Failure Handling

- Download/extraction failures are quarantined with evidence and never indexed.
- Structured-output failures retry once with a bounded compact repair request,
  then quarantine without invented fallback content.
- HTTP/server failures retry with bounded exponential backoff and stable request
  IDs.
- OOM reduces request concurrency after recording the event.
- Server exit or VM preemption preserves accepted records and resumes after
  identity validation.
- Missing or truncated reasoning is recorded and fails any variant contract
  that requires reasoning.
- Citation resolution or evidence-hash failure rejects the affected KG result.
- Export failure removes/invalidate the completion manifest so stale workbooks
  cannot appear complete.

## Evaluation and Deliverables

Evaluation uses the existing scientific core with pinned metric models and
explicit denominators. It reports per-variant and paired comparisons for safety,
relevance, fluency, language consistency, diversity, grounding, citation
validity, perspective coverage, latency, and token use. Reference-dependent
metrics exclude missing references explicitly.

The final workbook contains 1,550 rows and at least these sheets:

- `Outputs` with all four final narratives;
- `Zero-Shot Trace`;
- `Few-Shot Trace`;
- `KG-RAG Trace`;
- `MP-KG-RAG Trace`, including individual perspectives and synthesis plan;
- `Evidence Ledger`;
- `Run Manifest`; and
- `Quality Summary`.

Machine-readable deliverables include corpus/download/filter manifests,
semantic KG artifacts, checkpoint summaries, request/timing events, evaluation
tables, and a final export manifest with hashes. Workbook validation requires
exactly one output row per source ID, all 1,550 IDs, all four variants, required
trace joins, resolvable evidence IDs, expected sheet names, and a workbook hash.

## Test and Acceptance Strategy

Implementation is test-driven. Focused tests cover:

- downloader validation and failure quarantine;
- provenance-preserving content deduplication;
- page-aware chunk identity;
- frozen extraction selection and bounded candidates;
- corpus/semantic/dataset cache-identity separation;
- idempotent and conflicting checkpoint appends;
- vLLM reasoning/content parsing and token accounting;
- JSON-schema request/response handling and bounded repair;
- concurrent batched query signatures;
- progressive variant information contracts;
- citation resolution;
- interrupted-run resume;
- aggregate quality gates; and
- workbook completeness, joins, formatting, and manifest invalidation.

Acceptance requires all local focused and regression tests, notebook/runtime
freshness checks if the notebook remains a supported entry point, remote locked
environment validation, the passing 12-row GPU smoke, production checkpoint
integrity, all 1,550 completed rows, final evaluation gates, and independent
artifact verification before completion is claimed.

## Explicit Non-Goals

- Do not change the base model family or parameter size.
- Do not silently replace Qwen reasoning with synthetic summaries.
- Do not ingest unvalidated downloads or interstitial pages.
- Do not force per-row metric ordering by post-editing outputs.
- Do not run duplicate corpus extraction for smoke and production.
- Do not weaken identity or checkpoint validation to reuse stale artifacts.
- Do not start paid GPU production before the smoke gate passes.
