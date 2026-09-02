# VLLM Production Pipeline and KB25 Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a resumable vLLM-backed Qwen3.5-4B 4-bit pipeline that augments the validated corpus with the KB25 pack and produces four traced counter-narrative variants for all 1,550 dataset rows.

**Architecture:** Add focused production primitives for corpus acquisition, stage identity, checkpoints, deterministic semantic candidates, and vLLM requests instead of extending the monolithic notebook further. A new production orchestrator reuses the existing scientific retrieval/evaluation cores, stores corpus/KG artifacts independently from dataset runs, and exports through the existing workbook contract.

**Tech Stack:** Python 3.11, pytest/unittest, aiohttp, pypdf/PyMuPDF, pandas, openpyxl, BGE-M3, existing `mpkg_rag_core.py` and `mpkg_eval_core.py`, vLLM OpenAI-compatible API, Qwen3.5-4B with runtime 4-bit quantization.

## Global Constraints

- Use the exact pinned Qwen3.5-4B model and tokenizer revision already recorded by the production project.
- Effective inference weights must be 4-bit and verified in the environment manifest.
- Preserve model-emitted reasoning separately from final content; never synthesize missing reasoning.
- The KB25 archive SHA-256 must equal `a9661a599670e68dce5a915863c7b11e2752a5405bbd6746d1bafc194e5c5227`.
- Quarantined downloads or extraction rows must never enter retrieval.
- Corpus/KG cache identity must not include smoke/full row selection or run name.
- Every accepted evidence citation must resolve to source, page, chunk, span, and hashes.
- All checkpoints are append-only, identity-checked, lock-protected, and resumable.
- Do not launch the 1,550-row paid GPU run until the deterministic 12-row smoke gate passes.
- Do not modify or commit unrelated existing worktree changes.

---

### Task 1: KB25 acquisition, validation, and provenance-preserving merge

**Files:**
- Create: `work/mpkg_production_core.py`
- Create: `work/prepare_kb25.py`
- Create: `tests/test_mpkg_production_core.py`

**Interfaces:**
- Produces: `sha256_file(path: Path) -> str`
- Produces: `load_kb25_catalog(zip_path: Path, expected_sha256: str) -> list[dict[str, str]]`
- Produces: `validate_downloaded_pdf(path: Path, page_counter: Callable[[Path], int]) -> dict[str, Any]`
- Produces: `merge_document_provenance(existing: Iterable[dict], additions: Iterable[dict]) -> list[dict]`
- Produces CLI: `python work/prepare_kb25.py --pack ZIP --corpus-root ROOT --download-root ROOT`

- [ ] **Step 1: Write failing archive/catalog tests**

Add tests that create an in-memory ZIP with `MP_KG_RAG_KB_25_sources.csv`, verify the archive digest, require exactly 25 unique IDs/filenames/URLs, and reject a wrong hash or missing catalog columns.

```python
def test_load_kb25_catalog_requires_hash_and_complete_unique_catalog(tmp_path):
    pack = make_catalog_zip(tmp_path, valid_catalog_rows(25))
    rows = core.load_kb25_catalog(pack, core.sha256_file(pack))
    assert len(rows) == 25
    assert len({row["id"] for row in rows}) == 25
    assert len({row["suggested_filename"] for row in rows}) == 25
    with pytest.raises(ValueError, match="kb25_archive_hash_mismatch"):
        core.load_kb25_catalog(pack, "0" * 64)
```

- [ ] **Step 2: Run the archive test and verify RED**

Run: `pytest -q tests/test_mpkg_production_core.py::test_load_kb25_catalog_requires_hash_and_complete_unique_catalog`

Expected: fail because `mpkg_production_core` or `load_kb25_catalog` does not exist.

- [ ] **Step 3: Implement archive and catalog validation**

Implement canonical CSV decoding with `utf-8-sig`, required columns, path-safe archive member lookup, uniqueness checks, URL scheme checks, and stable catalog ordering by integer ID. Do not extract arbitrary archive paths.

```python
KB25_REQUIRED_COLUMNS = frozenset({
    "id", "publisher", "title", "year", "primary_topics",
    "verified_or_min_pages", "direct_pdf_url", "suggested_filename",
    "why_useful_for_mpkg_rag",
})

def load_kb25_catalog(zip_path, expected_sha256):
    if sha256_file(zip_path) != expected_sha256:
        raise ValueError("kb25_archive_hash_mismatch")
    with zipfile.ZipFile(zip_path) as archive:
        raw = archive.read("MP_KG_RAG_KB_25_sources.csv")
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if len(rows) != 25 or not rows or not KB25_REQUIRED_COLUMNS <= set(rows[0]):
        raise ValueError("kb25_catalog_invalid")
    _validate_unique_safe_catalog_rows(rows)
    return sorted(rows, key=lambda row: int(row["id"]))
```

- [ ] **Step 4: Write failing PDF-validation and deduplication tests**

Cover valid PDF signature/page count, HTML masquerading as PDF, parser failure, fewer than 50 pages, duplicate SHA-256 with multiple provenance rows, and stable canonical output independent of input order.

```python
def test_duplicate_content_has_one_document_and_all_provenance(tmp_path):
    digest = hashlib.sha256(b"same-pdf").hexdigest()
    merged = core.merge_document_provenance(
        [{"content_sha256": digest, "title": "Old", "source_url": "https://a"}],
        [{"content_sha256": digest, "title": "New", "source_url": "https://b"}],
    )
    assert len(merged) == 1
    assert {row["source_url"] for row in merged[0]["provenance"]} == {"https://a", "https://b"}
```

- [ ] **Step 5: Run PDF/dedup tests and verify RED**

Run: `pytest -q tests/test_mpkg_production_core.py -k 'pdf or duplicate_content'`

Expected: fail because PDF validation and provenance merge are absent.

- [ ] **Step 6: Implement PDF validation, atomic download, and merge**

Use `.part` files followed by `os.replace`, bounded retries, explicit timeouts, `%PDF-` signature validation, parsed page count, SHA-256, and structured quarantine records. Normalize provenance rows to deterministic JSON before deduplication.

```python
def validate_downloaded_pdf(path, page_counter):
    size = path.stat().st_size
    with path.open("rb") as stream:
        signature = stream.read(5)
    if signature != b"%PDF-":
        return {"accepted": False, "reason": "not_pdf_signature"}
    try:
        pages = int(page_counter(path))
    except Exception as exc:
        return {"accepted": False, "reason": "pdf_parse_failed", "error": repr(exc)}
    accepted = size > 1000 and pages >= 50
    return {
        "accepted": accepted,
        "reason": "accepted" if accepted else "pdf_below_minimum",
        "bytes": size,
        "sha256": sha256_file(path),
        "exact_pages": pages,
    }
```

- [ ] **Step 7: Implement the acquisition CLI and manifest**

The CLI must write `kb25_download_manifest.json`, `kb25_download_manifest.csv`, accepted PDFs under a dedicated staging directory, and a merged provenance manifest consumed by the corpus registry. It exits nonzero if any catalog row lacks an accepted or explicitly duplicate canonical document.

- [ ] **Step 8: Verify and commit Task 1**

Run: `pytest -q tests/test_mpkg_production_core.py -k 'kb25 or pdf or provenance or duplicate'`

Expected: all selected tests pass.

Run: `python -m py_compile work/mpkg_production_core.py work/prepare_kb25.py`

Commit: `git commit -m "feat: add validated kb25 corpus acquisition"`

---

### Task 2: Stage identities and append-only resumable checkpoints

**Files:**
- Modify: `work/mpkg_production_core.py`
- Modify: `tests/test_mpkg_production_core.py`

**Interfaces:**
- Produces: `canonical_hash(value: Any) -> str`
- Produces: `corpus_stage_identity(manifest, extraction_config, code_hash) -> dict`
- Produces: `semantic_stage_identity(corpus_identity, selection, model, prompt, schema, code_hash) -> dict`
- Produces: `dataset_stage_identity(workbook_hash, sheet, rows, shard) -> dict`
- Produces: `JsonlCheckpoint(path: Path, identity: dict, key_field: str)` with `read()`, `append(row)`, and `complete(expected_keys)`

- [ ] **Step 1: Write failing identity-isolation tests**

```python
def test_corpus_and_semantic_identity_ignore_run_and_dataset_selection():
    first = core.corpus_stage_identity(MANIFEST, EXTRACT_CONFIG, "code")
    second = core.corpus_stage_identity(MANIFEST, EXTRACT_CONFIG, "code")
    assert first == second
    semantic = core.semantic_stage_identity(first, SELECTION, MODEL, PROMPT, SCHEMA, "code")
    assert "run_name" not in json.dumps(semantic)
    assert "selected_dataset_rows" not in json.dumps(semantic)
```

Also test that corpus hash changes with document content, semantic hash changes with selected chunk IDs/model/prompt/schema, and dataset identity changes with row membership.

- [ ] **Step 2: Run identity tests and verify RED**

Run: `pytest -q tests/test_mpkg_production_core.py -k identity`

Expected: fail on missing identity functions.

- [ ] **Step 3: Implement canonical stage identities**

Every identity function returns both its canonical payload and a `stage_hash`. Reject unknown/mutable path and run-name fields in corpus/semantic payloads.

```python
def _with_stage_hash(stage, payload):
    canonical = json.loads(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str))
    return {"stage": stage, "payload": canonical, "stage_hash": canonical_hash([stage, canonical])}
```

- [ ] **Step 4: Write failing checkpoint tests**

Test append/read after restart, idempotent identical duplicate, conflicting duplicate rejection, malformed/truncated final line quarantine, locked concurrent append, identity mismatch, and completeness against exact expected keys.

```python
def test_checkpoint_rejects_conflicting_same_key(tmp_path):
    checkpoint = core.JsonlCheckpoint(tmp_path / "rows.jsonl", {"stage_hash": "a"}, "chunk_id")
    checkpoint.append({"chunk_id": "c1", "value": 1})
    checkpoint.append({"chunk_id": "c1", "value": 1})
    with pytest.raises(RuntimeError, match="checkpoint_conflict:c1"):
        checkpoint.append({"chunk_id": "c1", "value": 2})
```

- [ ] **Step 5: Run checkpoint tests and verify RED**

Run: `pytest -q tests/test_mpkg_production_core.py -k checkpoint`

Expected: fail on missing `JsonlCheckpoint`.

- [ ] **Step 6: Implement lock-protected checkpoint storage**

Use a sibling identity JSON, `fcntl.flock`, canonical row equality, `flush` plus `os.fsync`, and atomic identity/summary replacement. Never truncate an accepted JSONL file during resume.

- [ ] **Step 7: Verify and commit Task 2**

Run: `pytest -q tests/test_mpkg_production_core.py`

Expected: all tests pass.

Commit: `git commit -m "feat: add reusable production stage checkpoints"`

---

### Task 3: Deterministic candidates and frozen semantic extraction selection

**Files:**
- Modify: `work/mpkg_production_core.py`
- Modify: `tests/test_mpkg_production_core.py`
- Modify: `work/mpkg_rag_core.py`
- Modify: `tests/test_mpkg_rag_core.py`

**Interfaces:**
- Produces: `page_aware_chunks(pages, tokenizer, min_tokens=500, max_tokens=900, overlap_tokens=100) -> list[dict]`
- Produces: `deterministic_entity_candidates(text, reviewed_entities, controlled_terms, limit=48) -> list[dict]`
- Produces: `select_semantic_chunks(chunks, embeddings, neutral_queries, policy) -> dict`
- Consumes existing: `build_entity_catalog`, `validate_semantic_extraction`, `build_semantic_graph`

- [ ] **Step 1: Write failing page-aware chunk tests**

Require no cross-page/document chunks, stable IDs, exact source/page/hash fields, bounded token sizes except irreducible single-tokenizer units, and deterministic overlap.

- [ ] **Step 2: Run page-aware tests and verify RED**

Run: `pytest -q tests/test_mpkg_production_core.py -k page_aware`

Expected: fail on missing chunker.

- [ ] **Step 3: Implement page-aware chunking**

Use tokenizer offsets without truncation. Build IDs from document hash, page, token span, and text hash; preserve page and character spans.

- [ ] **Step 4: Write failing deterministic-candidate tests**

Cover reviewed organization matches, controlled SOGIESC terms, citation spans, exact offsets, normalized deduplication, stable ordering, and hard limit. Assert that candidate extraction does not invoke a model callback.

```python
def test_entity_candidates_are_exact_bounded_spans():
    text = "UNESCO guidance protects transgender people (Smith, 2024)."
    rows = core.deterministic_entity_candidates(text, ["UNESCO"], ["transgender people"], limit=3)
    assert [text[row["start"]:row["end"]] for row in rows] == [row["text"] for row in rows]
    assert len(rows) <= 3
```

- [ ] **Step 5: Implement deterministic candidates**

Combine exact reviewed-entity matching, controlled-term matching, and bounded citation regexes. Sort by `(start, end, normalized_text, type)` and create stable candidate IDs.

- [ ] **Step 6: Write failing selection-policy tests**

Require the selection result to include every chunk score/component/reason, select authority/topic coverage independently of dataset labels and targets, remain input-order invariant, and change its identity when policy/query/embedding content changes.

- [ ] **Step 7: Implement frozen semantic selection**

Return `{"policy", "neutral_query_hash", "selected_chunk_ids", "rows", "selection_hash"}`. Keep all chunks in the embedding index; selection controls only Qwen semantic-claim extraction.

- [ ] **Step 8: Verify and commit Task 3**

Run: `pytest -q tests/test_mpkg_production_core.py tests/test_mpkg_rag_core.py`

Expected: all tests pass.

Commit: `git commit -m "feat: freeze bounded semantic extraction inputs"`

---

### Task 4: Async vLLM client with reasoning and structured-output contracts

**Files:**
- Create: `work/vllm_qwen_client.py`
- Create: `tests/test_vllm_qwen_client.py`
- Modify: `requirements-remote-vm.in`
- Modify: `requirements-remote-vm.lock`

**Interfaces:**
- Produces: `VLLMQwenClient(base_url, model, concurrency, timeout, transport=None)`
- Produces: `GenerationRequest(request_id, messages, max_tokens, temperature, schema, thinking, thinking_token_budget)`
- Produces: `GenerationResult(request_id, reasoning_content, content, reasoning_tokens, answer_tokens, finish_reason, truncated, latency_ms, attempts, raw_usage)`
- Produces: `await client.generate_many(requests) -> list[GenerationResult]`

- [ ] **Step 1: Write failing request-shape tests**

Assert schema requests use `response_format.type=json_schema`, reasoning requests set `chat_template_kwargs.enable_thinking=true` and `thinking_token_budget`, non-thinking requests disable thinking, and stable request IDs are sent as metadata.

- [ ] **Step 2: Run request tests and verify RED**

Run: `pytest -q tests/test_vllm_qwen_client.py -k request`

Expected: fail because the client module does not exist.

- [ ] **Step 3: Implement typed request/result and payload construction**

```python
def request_payload(request, model):
    payload = {
        "model": model,
        "messages": request.messages,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "metadata": {"request_id": request.request_id},
        "chat_template_kwargs": {"enable_thinking": request.thinking},
    }
    if request.thinking:
        payload["thinking_token_budget"] = request.thinking_token_budget
    if request.schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "mpkg_response", "strict": True, "schema": request.schema},
        }
    return payload
```

- [ ] **Step 4: Write failing response/retry/concurrency tests**

Use a fake async transport to cover separate `reasoning_content` and `content`, missing reasoning, length finish/truncation, HTTP 429/500 retry, nonretryable 400, timeout, preserved input ordering, semaphore concurrency, and retry-attempt accounting.

- [ ] **Step 5: Run response tests and verify RED**

Run: `pytest -q tests/test_vllm_qwen_client.py`

Expected: request tests pass; response/retry tests fail on absent behavior.

- [ ] **Step 6: Implement bounded async generation**

Use `aiohttp.ClientSession`, a semaphore, stable ordering via indexed tasks, bounded exponential backoff, and strict response validation. A required reasoning trace that is absent must be returned as an explicit contract failure, never copied from final content.

- [ ] **Step 7: Pin vLLM client/server dependencies**

Add the exact validated vLLM version and any required OpenAI protocol dependency to the direct input, regenerate hashes with the repository's existing lock process, and retain exact versions for every transitive dependency. Do not hand-edit hashes.

- [ ] **Step 8: Verify and commit Task 4**

Run: `pytest -q tests/test_vllm_qwen_client.py tests/test_remote_vm_mpkg_rag_notebook.py -k 'vllm or lock or requirement'`

Expected: all selected tests pass and the lock integrity tests accept the regenerated lock.

Commit: `git commit -m "feat: add bounded vllm qwen client"`

---

### Task 5: Staged production orchestrator and batched semantic/query work

**Files:**
- Create: `work/run_vllm_production.py`
- Create: `tests/test_run_vllm_production.py`
- Modify: `work/mpkg_production_core.py`

**Interfaces:**
- Produces CLI subcommands: `prepare-corpus`, `build-kg`, `smoke`, `run`, `evaluate`, `export`, `status`
- Produces: `build_semantic_requests(selected_chunks, candidates, identity) -> list[GenerationRequest]`
- Produces: `build_query_signature_requests(records, catalog, identity) -> list[GenerationRequest]`
- Produces: `build_variant_requests(records, variant, evidence, prior_artifacts, identity) -> list[GenerationRequest]`
- Consumes: `JsonlCheckpoint`, `VLLMQwenClient`, existing graph/retrieval/evaluation helpers

- [ ] **Step 1: Write failing stage-routing and dry-run tests**

Use miniature corpus/dataset fixtures and a fake client. Verify that each subcommand reads only its prerequisite namespace, writes only its own namespace, refuses identity mismatch, and reports exact pending/completed keys without model/network access in `status` and `--dry-run`.

- [ ] **Step 2: Run routing tests and verify RED**

Run: `pytest -q tests/test_run_vllm_production.py -k 'routing or dry_run or status'`

Expected: fail because the orchestrator is absent.

- [ ] **Step 3: Implement configuration and stage routing**

Define one validated JSON configuration with project paths, pinned revisions, stage policies, model endpoint, concurrency, budgets, smoke IDs, and quality thresholds. Resolve paths once; store the effective config and its hash in every stage manifest.

- [ ] **Step 4: Write failing batched semantic and signature tests**

Assert one request per selected chunk/row, bounded candidate lists, no serial `await` inside request construction, checkpoint reuse by request ID, quarantined invalid schema after one repair, and corpus semantic checkpoints reused when dataset selection changes.

- [ ] **Step 5: Implement semantic extraction and query signatures**

Submit all pending requests through `generate_many`, validate against existing schemas and candidate/span rules, append accepted/quarantined rows immediately, and atomically publish completion manifests only when exact expected-key completeness holds.

- [ ] **Step 6: Write failing progressive-variant contract tests**

Verify equal base record/category/target fields, frozen few-shot examples, KG evidence only from the frozen ledger, MP using the same KG evidence plus exactly five perspectives and a plan, reasoning required for user-facing variants, and no test reference narrative in any generation prompt.

- [ ] **Step 7: Implement four-variant generation**

Generate variants in order. For MP-KG-RAG, batch the five perspectives across records, then batch plans, then batch syntheses. Persist reasoning and final content separately with timing/token/finish metadata.

- [ ] **Step 8: Implement smoke and production gates**

Freeze 12 stratified smoke IDs. Refuse `run` until a matching passing smoke manifest exists. The production command expects all 1,550 dataset IDs and four variant checkpoints.

- [ ] **Step 9: Verify and commit Task 5**

Run: `pytest -q tests/test_run_vllm_production.py tests/test_mpkg_production_core.py tests/test_vllm_qwen_client.py`

Expected: all tests pass without GPU, network, or model downloads.

Commit: `git commit -m "feat: add staged vllm production orchestrator"`

---

### Task 6: Evaluation ladder, workbook export, and artifact verifier

**Files:**
- Modify: `work/run_vllm_production.py`
- Modify: `work/mpkg_eval_core.py`
- Create: `work/verify_production_artifacts.py`
- Modify: `tests/test_run_vllm_production.py`
- Modify: `tests/test_mpkg_eval_core.py`

**Interfaces:**
- Produces: `progressive_quality_gate(metrics: dict) -> dict`
- Produces: `export_production_workbook(run_root: Path, output_path: Path) -> dict`
- Produces CLI: `python work/verify_production_artifacts.py --run-root ROOT --workbook FILE --expected-rows 1550`

- [ ] **Step 1: Write failing aggregate quality-ladder tests**

Test few-shot composite >= zero-shot, KG citation/grounding > few-shot, MP perspective/composite > KG, nullable reference metrics with explicit denominators, and visible failure details without score mutation.

- [ ] **Step 2: Run quality tests and verify RED**

Run: `pytest -q tests/test_mpkg_eval_core.py -k progressive_quality_gate`

Expected: fail because the gate is absent.

- [ ] **Step 3: Implement the frozen quality ladder**

Return `pass`, per-transition pass flags, exact deltas, denominators, and threshold identities. Do not round before comparison.

- [ ] **Step 4: Write failing workbook/verifier tests**

Build a three-row fixture and require the eight named sheets, one output per ID, four narratives, separate reasoning traces, five MP perspectives and plan, evidence joins, styled headers/wrapped trace cells/frozen panes/autofilters/column widths, final hash, and stale manifest invalidation on export failure.

- [ ] **Step 5: Implement workbook export**

Reuse existing sheet column contracts where compatible. Write to a temporary workbook, reopen and validate it, atomically replace the destination, fsync the directory, then write the export manifest. On any failure, remove the completion manifest but retain checkpoints.

- [ ] **Step 6: Implement independent artifact verification**

The verifier loads checkpoints and workbook independently, validates exact ID sets/counts/joins/hashes, resolves every evidence reference, and exits nonzero with structured JSON findings.

- [ ] **Step 7: Verify and commit Task 6**

Run: `pytest -q tests/test_mpkg_eval_core.py tests/test_run_vllm_production.py`

Run: `python -m py_compile work/run_vllm_production.py work/verify_production_artifacts.py`

Expected: all tests and compilation pass.

Commit: `git commit -m "feat: validate and export four-variant production results"`

---

### Task 7: Compatibility entry point, documentation, and full local gate

**Files:**
- Modify: `work/build_remote_vm_qwen35_mpkg_rag.py`
- Modify: `work/export_remote_vm_runtime.py`
- Regenerate: `outputs/remote_vm_qwen35_mpkg_rag.ipynb`
- Regenerate: `outputs/remote_vm_qwen35_mpkg_rag_runtime.py`
- Modify: `tests/test_remote_vm_mpkg_rag_notebook.py`
- Modify: `tests/test_production_thinking_contract.py`
- Create: `docs/production-vllm-runbook.md`

**Interfaces:**
- Notebook delegates production execution to the staged CLI or clearly marks the legacy monolithic path unavailable.
- Runbook provides CPU staging, GPU startup, vLLM launch, smoke, production, monitoring, resume, evaluation, export, and verification commands.

- [ ] **Step 1: Write failing notebook-delegation tests**

Require the generated notebook/runtime to reference the staged CLI, never invoke the abandoned generative mention-discovery loop, preserve the four-variant workbook contract, and verify the vLLM environment before a paid run.

- [ ] **Step 2: Run notebook tests and verify RED**

Run: `pytest -q tests/test_remote_vm_mpkg_rag_notebook.py tests/test_production_thinking_contract.py -k 'vllm or mention or production'`

Expected: fail because the builder still emits the old path.

- [ ] **Step 3: Replace the legacy production path with delegation**

Keep notebook generation deterministic. Its executable cells perform environment/config inspection and call the staged CLI; they do not duplicate orchestration logic.

- [ ] **Step 4: Write the exact operational runbook**

Include commands that use explicit project paths and PIDs, persistent `/teamspace` directories, pinned vLLM launch arguments, status checks, safe termination, and artifact verification. Never instruct deletion of run roots to resolve identity failures.

- [ ] **Step 5: Regenerate and run the complete local gate**

Run:

```bash
python work/build_remote_vm_qwen35_mpkg_rag.py
python work/export_remote_vm_runtime.py
pytest -q
python -m py_compile work/*.py outputs/remote_vm_qwen35_mpkg_rag_runtime.py
git diff --check
```

Expected: every test passes, generated artifacts are fresh, compilation succeeds, and `git diff --check` is empty.

- [ ] **Step 6: Commit Task 7**

Commit: `git commit -m "docs: route production through staged vllm pipeline"`

---

### Task 8: Remote KB preparation, vLLM benchmark, smoke, production, and final verification

**Files:**
- Remote persistent project: `/teamspace/studios/this_studio/mp_kg_rag_production_1550`
- Final local copy: `outputs/dataset_with_all_rag_counter_narratives.xlsx`
- Final remote workbook: path selected by the committed production configuration

**Interfaces:**
- Consumes all committed code and lockfiles from Tasks 1--7.
- Produces validated corpus/KG caches, smoke manifest, 1,550-row checkpoints, evaluation artifacts, final workbook, and export manifest.

- [ ] **Step 1: Synchronize committed files and verify hashes on CPU**

Transfer only committed production files, the KB25 archive, and configuration. Compare local/remote SHA-256 for every transferred file and retain the existing 95-file corpus/model cache.

- [ ] **Step 2: Download and validate KB25 on CPU**

Run the acquisition CLI, inspect all 25 statuses, parsed page counts, hashes, duplicates, and quarantines, then freeze the merged corpus manifest. Any failure remains visible; retry does not bypass validation.

- [ ] **Step 3: Install and validate the pinned GPU environment**

After the RTX PRO 6000 is turned on, install from the exact lock. Verify CUDA, vLLM model support, 4-bit effective weights, reasoning parser, structured outputs, and persistent cache paths.

- [ ] **Step 4: Benchmark vLLM with representative requests**

Measure non-thinking JSON extraction, thinking JSON generation, concurrent batches, reasoning separation, tokens/sec, request/sec, p50/p95 latency, VRAM, and parse success. Increase concurrency one step at a time until throughput stops improving or safe memory/latency thresholds are reached.

- [ ] **Step 5: Build/reuse corpus and semantic KG**

Run `prepare-corpus` and `build-kg`, monitor checkpoint counts and ETA, and independently verify semantic completeness and citation resolution before dataset generation.

- [ ] **Step 6: Run and approve the 12-row smoke gate**

Require all 48 outputs, traces, evidence, quality results, and a passing smoke manifest. If it fails, preserve the run and return to the failing test/config identity; do not start production.

- [ ] **Step 7: Run and monitor all 1,550 rows**

Start `run`, poll structured status and GPU metrics, adjust only concurrency for runtime stability, and resume after interruption from verified checkpoints.

- [ ] **Step 8: Evaluate, export, and independently verify**

Run `evaluate`, `export`, and `verify_production_artifacts.py`. Confirm exactly 1,550 IDs, four narratives per ID, all required traces/sheets, evidence joins, passing hashes, and an aggregate quality report that truthfully records every transition.

- [ ] **Step 9: Copy back and checksum the final workbook**

Copy the final workbook and machine-readable manifests to the local `outputs/` directory, compare SHA-256 local/remote, and report the absolute local file link plus final row/sheet/quality counts.

- [ ] **Step 10: Commit any verified operational-only corrections**

Only reproducible source/config/test corrections discovered remotely are committed. Runtime data, model caches, credentials, logs, and generated production checkpoints remain outside Git.

## Plan Self-Review

- Every approved design requirement maps to a task: KB25 validation (Task 1), reusable identities/checkpoints (Task 2), bounded semantic inputs (Task 3), vLLM/reasoning/JSON (Task 4), staged generation (Task 5), quality/export (Task 6), compatibility/runbook (Task 7), and remote execution (Task 8).
- Interfaces use consistent names across producer and consumer tasks.
- No task relies on a hidden network/model download during local tests.
- GPU production remains gated on a complete passing smoke run.
- The plan contains no placeholder implementation steps.
