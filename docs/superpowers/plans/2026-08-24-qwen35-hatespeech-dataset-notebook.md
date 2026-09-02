# Qwen3.5 Hate-Speech Dataset Kaggle Notebook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible Kaggle notebook that generates 1,500 or 2,000 balanced synthetic LGBTQIA+-directed hate-speech records with same-language counter-narratives and the exact requested five-column export schema.

**Architecture:** A deterministic Python builder emits the tracked `.ipynb`, following the repository's existing generated-notebook pattern. Pure planning, parsing, validation, deduplication, checkpoint, and export helpers live in notebook code cells so contract tests can extract and execute them locally without downloading a model; only the full generation loop requires a Kaggle GPU.

**Tech Stack:** Python 3.11+, Jupyter Notebook JSON, PyTorch, Transformers, Accelerate, bitsandbytes NF4, pandas, openpyxl, scikit-learn, langdetect, matplotlib, seaborn, pytest/unittest-compatible tests.

## Global Constraints

- Work only on `feature/qwen35-lgbtq-hatespeech-notebook`; do not move or amend `master` or `semantic-kg-production`.
- Preserve all unrelated dirty-worktree files and stage only the files listed by each task.
- Primary model: `lukey03/Qwen3.5-9B-abliterated`.
- Text-only fallback: `wangzhang/Qwen3.5-4B-abliterated`.
- Use explicit 4-bit NF4 quantization; never mix model IDs inside one resumed run.
- Supported full totals are exactly 1,500 and 2,000; smoke-test total is exactly 15.
- Categories are exactly `Gay Men`, `Lesbian Women`, `Bisexual People`, `Transgender People`, and `Non-binary/Gender-nonconforming People`.
- Generated languages are English, Hindi in Devanagari, and Hinglish in Latin script.
- Harmful text may cover the approved extreme severity range, but must use synthetic targets and exclude real handles, private information, attack coordination, and operational instructions for violence.
- Final export columns, in order, are exactly `ID`, `Text`, `Category`, `Target`, `Counter Narrative`.
- Full model generation is not part of local verification; local tests validate notebook structure and pure helper behavior.

## File Structure

- `work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py`: deterministic builder and all notebook cell sources; this is the only hand-edited implementation artifact.
- `tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py`: notebook contract tests and AST-extracted pure-helper unit tests.
- `outputs/kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb`: generated Kaggle artifact; never edit it directly.
- `docs/superpowers/specs/2026-08-24-qwen35-hatespeech-dataset-notebook-design.md`: approved requirements source; read-only during implementation unless a contradiction is discovered.

---

### Task 1: Kaggle notebook skeleton and immutable configuration contract

**Files:**
- Create: `tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py`
- Create: `work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py`
- Create: `outputs/kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb`

**Interfaces:**
- Consumes: `pathlib.Path` and Python's standard `json` module.
- Produces: `markdown(source: str) -> dict`, `code(source: str) -> dict`, and `build_notebook(output_path: Path) -> None`.
- Produces notebook globals: `CONFIG`, `CATEGORIES`, `EXPORT_COLUMNS`, and model-ID constants used by later cells.

- [ ] **Step 1: Write the failing skeleton contract tests**

Create `tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py` with:

```python
import json
import tempfile
import unittest
from pathlib import Path


class KaggleHateSpeechNotebookTests(unittest.TestCase):
    def build_notebook_json(self):
        from work.build_kaggle_qwen35_lgbtq_hatespeech_dataset import build_notebook

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "notebook.ipynb"
            build_notebook(output)
            return json.loads(output.read_text(encoding="utf-8"))

    def build_text(self):
        notebook = self.build_notebook_json()
        return "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])

    def test_notebook_has_kaggle_metadata_and_model_choices(self):
        notebook = self.build_notebook_json()
        text = self.build_text()
        self.assertEqual(notebook["nbformat"], 4)
        self.assertEqual(notebook["metadata"]["kaggle"]["accelerator"], "gpu")
        self.assertIn("lukey03/Qwen3.5-9B-abliterated", text)
        self.assertIn("wangzhang/Qwen3.5-4B-abliterated", text)

    def test_notebook_freezes_categories_totals_and_export_schema(self):
        text = self.build_text()
        for value in [
            "Gay Men",
            "Lesbian Women",
            "Bisexual People",
            "Transgender People",
            "Non-binary/Gender-nonconforming People",
            "SUPPORTED_TOTALS = {1500, 2000}",
            "SMOKE_TOTAL = 15",
            "EXPORT_COLUMNS = [\"ID\", \"Text\", \"Category\", \"Target\", \"Counter Narrative\"]",
        ]:
            self.assertIn(value, text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the skeleton tests and verify the expected import failure**

Run:

```bash
python -m pytest tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py -q
```

Expected: collection or test failure with `ModuleNotFoundError: No module named 'work.build_kaggle_qwen35_lgbtq_hatespeech_dataset'`.

- [ ] **Step 3: Implement the minimal deterministic notebook builder**

Create `work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py` with the following builder structure and exact immutable configuration values:

```python
#!/usr/bin/env python3
"""Build the Kaggle Qwen3.5 LGBTQIA+ hate-speech dataset notebook."""

from __future__ import annotations

import json
from pathlib import Path


def markdown(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in source.splitlines()],
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in source.splitlines()],
    }


SETUP_CELL = '''# Run once in a Kaggle GPU notebook with Internet enabled.
%pip install -q -U "transformers>=5.3.0" "accelerate>=1.10.0" "bitsandbytes>=0.46.0" "sentencepiece>=0.2.0" "pandas>=2.2.0" "openpyxl>=3.1.0" "tqdm>=4.67.0" "langdetect>=1.0.9" "scikit-learn>=1.5.0" "matplotlib>=3.9.0" "seaborn>=0.13.0"
'''

CONFIG_CELL = '''import os
from pathlib import Path

PRIMARY_MODEL_ID = "lukey03/Qwen3.5-9B-abliterated"
FALLBACK_MODEL_ID = "wangzhang/Qwen3.5-4B-abliterated"
SUPPORTED_TOTALS = {1500, 2000}
SMOKE_TOTAL = 15
CATEGORIES = (
    "Gay Men",
    "Lesbian Women",
    "Bisexual People",
    "Transgender People",
    "Non-binary/Gender-nonconforming People",
)
EXPORT_COLUMNS = ["ID", "Text", "Category", "Target", "Counter Narrative"]
CONFIG = {
    "model_id": os.environ.get("MODEL_ID", PRIMARY_MODEL_ID),
    "total_rows": 2000,
    "smoke_test": False,
    "seed": 3407,
    "generation_batch_size": 3,
    "temperature": 1.0,
    "top_p": 0.92,
    "repetition_penalty": 1.08,
    "max_new_tokens": 1100,
    "max_request_retries": 6,
    "near_duplicate_threshold": 0.88,
    "run_root": Path("/kaggle/working/qwen35_hatespeech_generation"),
}
'''


def build_notebook(output_path: Path) -> None:
    cells = [
        markdown("""# Qwen3.5 LGBTQIA+ Hate-Speech Dataset Generator

This Kaggle notebook creates a synthetic research dataset for automated hate-speech detection and reporting. It produces severe multilingual social-media examples and same-language counter-narratives without using real people or private information.

Enable a GPU accelerator and Internet access before running all cells."""),
        code(SETUP_CELL),
        code(CONFIG_CELL),
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
            "kaggle": {"accelerator": "gpu", "internet": True},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_notebook(
        Path(__file__).resolve().parents[1]
        / "outputs"
        / "kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb"
    )
```

Generate the notebook:

```bash
python work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py
```

Expected: exit code 0 and a new `outputs/kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb`.

- [ ] **Step 4: Run the skeleton tests and verify they pass**

Run:

```bash
python -m pytest tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit the skeleton**

```bash
git add work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py outputs/kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb
git commit -m "feat: scaffold Kaggle hate-speech dataset notebook"
```

---

### Task 2: Deterministic quotas, row validation, and deduplication

**Files:**
- Modify: `tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py`
- Modify: `work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py`
- Regenerate: `outputs/kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb`

**Interfaces:**
- Consumes: notebook globals `CATEGORIES`, `SUPPORTED_TOTALS`, `SMOKE_TOTAL`, and `CONFIG`.
- Produces: `build_quota_schedule(total_rows: int, seed: int) -> list[dict]`.
- Produces: `validate_generated_row(row: dict, scheduled: dict) -> list[str]`.
- Produces: `normalize_for_dedup(value: str) -> str` and `is_near_duplicate(value: str, accepted_values: list[str], threshold: float) -> bool`.

- [ ] **Step 1: Add failing pure-helper tests**

Add these imports and helper to the test file:

```python
import ast
import random
import re
import unicodedata


def extract_notebook_functions(notebook, wanted):
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )
    source = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith(("%", "!"))
    )
    tree = ast.parse(source)
    definitions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted
    ]
    namespace = {
        "random": random,
        "re": re,
        "unicodedata": unicodedata,
        "EXPORT_COLUMNS": ["ID", "Text", "Category", "Target", "Counter Narrative"],
        "CATEGORIES": (
            "Gay Men",
            "Lesbian Women",
            "Bisexual People",
            "Transgender People",
            "Non-binary/Gender-nonconforming People",
        ),
        "SUPPORTED_TOTALS": {1500, 2000},
        "SMOKE_TOTAL": 15,
        "LANGUAGES": ("English", "Hindi", "Hinglish"),
        "PLATFORM_STYLES": (
            "X/Twitter reply",
            "Instagram comment",
            "Instagram meme caption",
            "YouTube reply",
            "Public chat/forum message",
        ),
        "ABUSE_TYPES": (
            "coded mockery",
            "identity shaming",
            "stereotype/inferiority",
            "misgendering",
            "profanity/slur",
            "sexualized degradation",
            "dehumanization",
            "exclusion/rights denial",
            "threat/intimidation",
        ),
        "SEVERITIES": ("coded", "explicit", "severe", "extreme"),
        "REFUSAL_MARKERS": (
            "i cannot assist",
            "i can't assist",
            "i cannot generate",
            "main yeh generate nahi kar sakta",
            "as an ai",
            "language model",
        ),
        "CONTACT_PATTERN": re.compile(
            r"https?://|www\\.|[\\w.+-]+@[\\w.-]+\\.[A-Za-z]{2,}|(?<!\\w)@[A-Za-z0-9_]{2,}|(?:\\+?\\d[ -]?){8,}"
        ),
        "HINGLISH_MARKERS": {
            "hai", "hain", "nahi", "yeh", "woh", "kya", "kyun", "log", "wala", "wali",
            "kar", "mat", "ko", "se", "ka", "ki", "ke", "aur", "bahut", "aisa", "aisi",
        },
    }
    exec(compile(ast.Module(body=definitions, type_ignores=[]), "notebook-functions", "exec"), namespace)
    return namespace
```

Add these test methods to `KaggleHateSpeechNotebookTests`:

```python
    def test_quota_schedule_is_balanced_and_deterministic(self):
        notebook = self.build_notebook_json()
        functions = extract_notebook_functions(
            notebook, {"_language_counts", "build_quota_schedule"}
        )
        first = functions["build_quota_schedule"](2000, 3407)
        second = functions["build_quota_schedule"](2000, 3407)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2000)
        for category in functions["CATEGORIES"]:
            rows = [row for row in first if row["category"] == category]
            self.assertEqual(len(rows), 400)
            language_counts = {
                language: sum(row["language"] == language for row in rows)
                for language in functions["LANGUAGES"]
            }
            self.assertEqual(language_counts, {"English": 134, "Hindi": 133, "Hinglish": 133})
        self.assertEqual(len({row["request_id"] for row in first}), 2000)

    def test_quota_schedule_supports_1500_and_smoke_but_rejects_other_totals(self):
        notebook = self.build_notebook_json()
        functions = extract_notebook_functions(
            notebook, {"_language_counts", "build_quota_schedule"}
        )
        self.assertEqual(len(functions["build_quota_schedule"](1500, 9)), 1500)
        self.assertEqual(len(functions["build_quota_schedule"](15, 9)), 15)
        with self.assertRaisesRegex(ValueError, "unsupported_total_rows"):
            functions["build_quota_schedule"](1700, 9)

    def test_row_validator_rejects_identity_mismatch_refusal_and_private_markers(self):
        notebook = self.build_notebook_json()
        functions = extract_notebook_functions(
            notebook,
            {"normalize_for_dedup", "_language_matches", "validate_generated_row"},
        )
        scheduled = {
            "request_id": "REQ000001",
            "category": "Transgender People",
            "language": "Hinglish",
            "platform_style": "Instagram comment",
            "abuse_type": "identity shaming",
            "severity": "severe",
        }
        row = {
            "ID": "REQ000001",
            "Text": "Main yeh generate nahi kar sakta, contact @realperson at test@example.com",
            "Category": "Gay Men",
            "Target": "a fictional creator",
            "Counter Narrative": "I cannot assist with that request.",
            "language": "Hinglish",
            "platform_style": "Instagram comment",
            "abuse_type": "identity shaming",
            "severity": "severe",
            "request_id": "REQ000001",
        }
        reasons = functions["validate_generated_row"](row, scheduled)
        self.assertIn("category_mismatch", reasons)
        self.assertIn("refusal_or_disclaimer", reasons)
        self.assertIn("private_or_contact_marker", reasons)

    def test_normalization_and_near_duplicate_detection(self):
        notebook = self.build_notebook_json()
        functions = extract_notebook_functions(
            notebook, {"normalize_for_dedup", "is_near_duplicate"}
        )
        normalized = functions["normalize_for_dedup"]("  SAME\u00a0Text!! ")
        self.assertEqual(normalized, "same text!!")
        self.assertTrue(
            functions["is_near_duplicate"](
                "This social media comment repeats almost exactly",
                ["This social-media comment repeats almost exactly"],
                0.80,
            )
        )
```

- [ ] **Step 2: Run the helper tests and verify missing-function failures**

Run:

```bash
python -m pytest tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py -q
```

Expected: the two Task 1 tests pass and the four new tests fail because `build_quota_schedule`, `validate_generated_row`, `normalize_for_dedup`, and `is_near_duplicate` are absent.

- [ ] **Step 3: Add the quota, validation, and deduplication cell**

Define `PLANNING_VALIDATION_CELL` in the builder and include `code(PLANNING_VALIDATION_CELL)` after `code(CONFIG_CELL)`:

```python
PLANNING_VALIDATION_CELL = '''import random
import re
import unicodedata

LANGUAGES = ("English", "Hindi", "Hinglish")
PLATFORM_STYLES = (
    "X/Twitter reply",
    "Instagram comment",
    "Instagram meme caption",
    "YouTube reply",
    "Public chat/forum message",
)
ABUSE_TYPES = (
    "coded mockery",
    "identity shaming",
    "stereotype/inferiority",
    "misgendering",
    "profanity/slur",
    "sexualized degradation",
    "dehumanization",
    "exclusion/rights denial",
    "threat/intimidation",
)
SEVERITIES = ("coded", "explicit", "severe", "extreme")
REFUSAL_MARKERS = (
    "i cannot assist",
    "i can't assist",
    "i cannot generate",
    "main yeh generate nahi kar sakta",
    "as an ai",
    "language model",
)
CONTACT_PATTERN = re.compile(
    r"https?://|www\\.|[\\w.+-]+@[\\w.-]+\\.[A-Za-z]{2,}|(?<!\\w)@[A-Za-z0-9_]{2,}|(?:\\+?\\d[ -]?){8,}"
)
HINGLISH_MARKERS = {
    "hai", "hain", "nahi", "yeh", "woh", "kya", "kyun", "log", "wala", "wali",
    "kar", "mat", "ko", "se", "ka", "ki", "ke", "aur", "bahut", "aisa", "aisi",
}


def _language_counts(total_per_category):
    if total_per_category == 400:
        return {"English": 134, "Hindi": 133, "Hinglish": 133}
    if total_per_category == 300:
        return {"English": 100, "Hindi": 100, "Hinglish": 100}
    if total_per_category == 3:
        return {"English": 1, "Hindi": 1, "Hinglish": 1}
    raise ValueError("unsupported_per_category_total")


def build_quota_schedule(total_rows, seed):
    if total_rows not in SUPPORTED_TOTALS | {SMOKE_TOTAL}:
        raise ValueError("unsupported_total_rows")
    per_category = total_rows // len(CATEGORIES)
    language_counts = _language_counts(per_category)
    schedule = []
    for category_index, category in enumerate(CATEGORIES):
        category_rows = []
        secondary_index = 0
        for language in LANGUAGES:
            for _ in range(language_counts[language]):
                category_rows.append({
                    "category": category,
                    "language": language,
                    "platform_style": PLATFORM_STYLES[(secondary_index + category_index) % len(PLATFORM_STYLES)],
                    "abuse_type": ABUSE_TYPES[(secondary_index + 2 * category_index) % len(ABUSE_TYPES)],
                    "severity": SEVERITIES[(secondary_index + category_index) % len(SEVERITIES)],
                })
                secondary_index += 1
        random.Random(seed + category_index).shuffle(category_rows)
        schedule.extend(category_rows)
    for index, row in enumerate(schedule, 1):
        row["request_id"] = f"REQ{index:06d}"
    return schedule


def normalize_for_dedup(value):
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    return re.sub(r"\\s+", " ", normalized).strip()


def is_near_duplicate(value, accepted_values, threshold):
    if not accepted_values:
        return False
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    values = [normalize_for_dedup(existing) for existing in accepted_values]
    values.append(normalize_for_dedup(value))
    matrix = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit_transform(values)
    similarities = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    return bool(similarities.size and similarities.max() >= threshold)


def _language_matches(text, language):
    value = str(text)
    devanagari = len(re.findall(r"[\\u0900-\\u097F]", value))
    tokens = set(re.findall(r"[a-z]+", value.casefold()))
    if language == "Hindi":
        return devanagari >= 4
    if language == "Hinglish":
        return devanagari == 0 and len(tokens & HINGLISH_MARKERS) >= 2
    return devanagari == 0 and len(tokens & HINGLISH_MARKERS) < 2


def validate_generated_row(row, scheduled):
    reasons = []
    required = EXPORT_COLUMNS + [
        "language", "platform_style", "abuse_type", "severity", "request_id"
    ]
    if not isinstance(row, dict) or any(not isinstance(row.get(key), str) or not row[key].strip() for key in required):
        return ["missing_or_empty_field"]
    mappings = {
        "Category": "category",
        "language": "language",
        "platform_style": "platform_style",
        "abuse_type": "abuse_type",
        "severity": "severity",
        "request_id": "request_id",
    }
    for row_key, schedule_key in mappings.items():
        if row[row_key] != scheduled[schedule_key]:
            reasons.append("category_mismatch" if row_key == "Category" else f"{schedule_key}_mismatch")
    if row["ID"] != scheduled["request_id"]:
        reasons.append("id_mismatch")
    combined = f"{row['Text']} {row['Counter Narrative']}"
    lowered = normalize_for_dedup(combined)
    if any(marker in lowered for marker in REFUSAL_MARKERS):
        reasons.append("refusal_or_disclaimer")
    if CONTACT_PATTERN.search(combined):
        reasons.append("private_or_contact_marker")
    if not 8 <= len(row["Text"].strip()) <= 500:
        reasons.append("text_length")
    if not 15 <= len(row["Counter Narrative"].strip()) <= 700:
        reasons.append("counter_narrative_length")
    if normalize_for_dedup(row["Text"]) == normalize_for_dedup(row["Counter Narrative"]):
        reasons.append("identical_text_and_counter")
    if not _language_matches(row["Text"], scheduled["language"]):
        reasons.append("language_mismatch")
    return sorted(set(reasons))
'''
```

- [ ] **Step 4: Regenerate and run the helper tests**

Run:

```bash
python work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py
python -m pytest tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py -q
```

Expected: `6 passed`.

- [ ] **Step 5: Commit quota and validation behavior**

```bash
git add work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py outputs/kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb
git commit -m "feat: add deterministic hate-speech generation quotas"
```

---

### Task 3: Quantized generation, strict parsing, and resumable checkpoints

**Files:**
- Modify: `tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py`
- Modify: `work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py`
- Regenerate: `outputs/kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb`

**Interfaces:**
- Consumes: `CONFIG`, `build_quota_schedule`, `validate_generated_row`, and `is_near_duplicate` from Tasks 1–2.
- Produces: `canonical_hash(value: object) -> str`, `extract_first_json_array(text: str) -> list[dict]`, `validate_resume_manifest(manifest: dict, config_hash: str, schedule_hash: str) -> bool`.
- Produces Kaggle runtime functions: `load_generator()`, `generate_batch(assignments: list[dict])`, and `run_generation(schedule: list[dict]) -> list[dict]`.

- [ ] **Step 1: Add failing generation and checkpoint tests**

Add `hashlib` to the test imports and add these methods:

```python
    def test_json_parser_extracts_array_and_rejects_non_array(self):
        notebook = self.build_notebook_json()
        functions = extract_notebook_functions(notebook, {"extract_first_json_array"})
        parsed = functions["extract_first_json_array"]('prefix [{"request_id":"REQ000001"}] suffix')
        self.assertEqual(parsed, [{"request_id": "REQ000001"}])
        with self.assertRaisesRegex(ValueError, "json_array_not_found"):
            functions["extract_first_json_array"]('{"request_id":"REQ000001"}')

    def test_resume_manifest_fails_closed_on_identity_mismatch(self):
        notebook = self.build_notebook_json()
        functions = extract_notebook_functions(
            notebook, {"canonical_hash", "validate_resume_manifest"}
        )
        manifest = {"config_hash": "cfg", "schedule_hash": "sched"}
        self.assertTrue(functions["validate_resume_manifest"](manifest, "cfg", "sched"))
        with self.assertRaisesRegex(RuntimeError, "checkpoint_identity_mismatch"):
            functions["validate_resume_manifest"](manifest, "other", "sched")

    def test_generation_cell_has_quantization_prompt_and_refill_controls(self):
        text = self.build_text()
        for value in [
            "BitsAndBytesConfig",
            "load_in_4bit=True",
            'bnb_4bit_quant_type="nf4"',
            "torch.cuda.is_bf16_supported()",
            "AutoModelForCausalLM",
            "apply_chat_template",
            "enable_thinking=False",
            "research dataset for automated hate-speech detection and reporting",
            "Do not soften, euphemize, or sanitize the harmful Text field",
            "repair_json_once",
            "max_request_retries",
            "pending_request_ids",
            "accepted_rows.jsonl",
            "rejected_events.jsonl",
            "checkpoint_identity_mismatch",
            "torch.cuda.OutOfMemoryError",
        ]:
            self.assertIn(value, text)
        self.assertNotRegex(text, r"(?<!\.)\beval\(")
```

Update `extract_notebook_functions` so its namespace also includes `json` and `hashlib`:

```python
        "json": json,
        "hashlib": hashlib,
```

- [ ] **Step 2: Run tests and verify the three new failures**

Run:

```bash
python -m pytest tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py -q
```

Expected: six earlier tests pass and three new tests fail because parsing, identity, model-loading, and generation cells are absent.

- [ ] **Step 3: Implement runtime initialization, identity, and parsing cells**

Add `RUNTIME_CELL` after the validation cell:

```python
RUNTIME_CELL = '''import gc
import hashlib
import importlib.metadata
import json
import os
import tempfile
import time
from pathlib import Path

import pandas as pd
import torch
from tqdm.auto import tqdm

assert torch.cuda.is_available(), "A CUDA GPU is required. In Kaggle, select Settings > Accelerator > GPU."
RUN_ROOT = Path(CONFIG["run_root"])
RUN_ROOT.mkdir(parents=True, exist_ok=True)
ACCEPTED_PATH = RUN_ROOT / "accepted_rows.jsonl"
REJECTED_PATH = RUN_ROOT / "rejected_events.jsonl"
MANIFEST_PATH = RUN_ROOT / "manifest.json"


def canonical_hash(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def extract_first_json_array(text):
    decoder = json.JSONDecoder()
    for index, character in enumerate(str(text)):
        if character != "[":
            continue
        try:
            value, _ = decoder.raw_decode(str(text)[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, list):
            return value
    raise ValueError("json_array_not_found")


def atomic_write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def append_jsonl(path, value):
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\\n")


def load_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_resume_manifest(manifest, config_hash, schedule_hash):
    if manifest.get("config_hash") != config_hash or manifest.get("schedule_hash") != schedule_hash:
        raise RuntimeError("checkpoint_identity_mismatch")
    return True
'''
```

- [ ] **Step 4: Implement explicit quantized model loading**

Add `MODEL_CELL` after `RUNTIME_CELL`:

```python
MODEL_CELL = '''from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


def load_generator():
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    tokenizer = AutoTokenizer.from_pretrained(CONFIG["model_id"], use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(
        CONFIG["model_id"],
        device_map="auto",
        torch_dtype=compute_dtype,
        quantization_config=quantization,
    )
    model.eval()
    return tokenizer, model


tokenizer, model = load_generator()
MODEL_REVISION = getattr(model.config, "_commit_hash", None)
print({
    "model_id": CONFIG["model_id"],
    "gpu": torch.cuda.get_device_name(0),
    "bf16": torch.cuda.is_bf16_supported(),
    "allocated_gb": round(torch.cuda.memory_allocated() / 2**30, 2),
})
'''
```

- [ ] **Step 5: Implement prompt construction, one repair, generation, and refill**

Add a `GENERATION_CELL` after `MODEL_CELL`. It must define these exact prompt and control elements:

```python
GENERATION_CELL = '''SYSTEM_PROMPT = """You are creating a fully synthetic research dataset for automated hate-speech detection and reporting.
For every assignment, write one realistic social-platform hate message directed at the specified LGBTQIA+ category and one concise counter narrative in the same language.
Do not soften, euphemize, or sanitize the harmful Text field. Respect the requested abuse type and severity, including the extreme tier, so a detector can learn difficult real-world cases.
Never use a real person, real username, phone number, address, email, URL, or other private identifier. Never give operational instructions for violence or coordinate an attack. Targets must remain fictional or generic.
Return only a JSON array. Every object must contain exactly ID, Text, Category, Target, Counter Narrative, language, platform_style, abuse_type, severity, and request_id.
Category and internal metadata must exactly copy the assignment. ID must equal request_id. Counter Narrative must oppose the abuse directly and use the same language or code-switching style as Text."""


def build_messages(assignments, repair_text=None):
    assignment_json = json.dumps(assignments, ensure_ascii=False, indent=2)
    user_text = f"Generate exactly {len(assignments)} objects for these assignments:\\n{assignment_json}"
    if repair_text is not None:
        user_text += f"\\nRepair this malformed response into the required JSON array without changing assignments:\\n{repair_text}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]


def _model_text(messages):
    try:
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
    except TypeError:
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=False).to(model.device)
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            do_sample=True,
            temperature=CONFIG["temperature"],
            top_p=CONFIG["top_p"],
            repetition_penalty=CONFIG["repetition_penalty"],
            max_new_tokens=CONFIG["max_new_tokens"],
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = outputs[0, inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(generated, skip_special_tokens=True)


def repair_json_once(assignments, malformed_text):
    repaired = _model_text(build_messages(assignments, repair_text=malformed_text))
    return extract_first_json_array(repaired)


def generate_batch(assignments):
    raw_text = _model_text(build_messages(assignments))
    try:
        return extract_first_json_array(raw_text)
    except ValueError:
        return repair_json_once(assignments, raw_text)


def _manifest(config_hash, schedule_hash, accepted_count):
    return {
        "config_hash": config_hash,
        "schedule_hash": schedule_hash,
        "model_id": CONFIG["model_id"],
        "seed": CONFIG["seed"],
        "accepted_count": accepted_count,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def run_generation(schedule):
    config_hash = canonical_hash({key: str(value) for key, value in CONFIG.items()})
    schedule_hash = canonical_hash(schedule)
    if MANIFEST_PATH.exists():
        validate_resume_manifest(json.loads(MANIFEST_PATH.read_text(encoding="utf-8")), config_hash, schedule_hash)
    accepted = load_jsonl(ACCEPTED_PATH)
    accepted_by_id = {row["request_id"]: row for row in accepted}
    accepted_texts = [row["Text"] for row in accepted]
    accepted_counters = [row["Counter Narrative"] for row in accepted]
    schedule_by_id = {row["request_id"]: row for row in schedule}
    pending_request_ids = [request_id for request_id in schedule_by_id if request_id not in accepted_by_id]
    retry_counts = {request_id: 0 for request_id in pending_request_ids}
    batch_size = CONFIG["generation_batch_size"]
    while pending_request_ids:
        request_ids = pending_request_ids[:batch_size]
        assignments = [schedule_by_id[request_id] for request_id in request_ids]
        try:
            candidates = generate_batch(assignments)
        except torch.cuda.OutOfMemoryError as error:
            torch.cuda.empty_cache()
            gc.collect()
            batch_size = max(1, batch_size // 2)
            append_jsonl(REJECTED_PATH, {"request_ids": request_ids, "reason": "cuda_out_of_memory", "error": str(error)})
            continue
        except Exception as error:
            candidates = []
            append_jsonl(REJECTED_PATH, {"request_ids": request_ids, "reason": "batch_generation_failed", "error": str(error)})
        candidates_by_id = {
            row.get("request_id"): row for row in candidates if isinstance(row, dict)
        }
        for request_id in request_ids:
            scheduled = schedule_by_id[request_id]
            candidate = candidates_by_id.get(request_id)
            reasons = ["missing_candidate"] if candidate is None else validate_generated_row(candidate, scheduled)
            if candidate is not None and not reasons:
                if is_near_duplicate(candidate["Text"], accepted_texts, CONFIG["near_duplicate_threshold"]):
                    reasons.append("near_duplicate_text")
                if is_near_duplicate(candidate["Counter Narrative"], accepted_counters, CONFIG["near_duplicate_threshold"]):
                    reasons.append("near_duplicate_counter")
            if reasons:
                retry_counts[request_id] += 1
                append_jsonl(REJECTED_PATH, {"request_id": request_id, "reasons": reasons})
                if retry_counts[request_id] > CONFIG["max_request_retries"]:
                    raise RuntimeError(f"retry_budget_exhausted:{request_id}:{','.join(reasons)}")
                continue
            accepted_by_id[request_id] = candidate
            accepted_texts.append(candidate["Text"])
            accepted_counters.append(candidate["Counter Narrative"])
            append_jsonl(ACCEPTED_PATH, candidate)
            pending_request_ids.remove(request_id)
        atomic_write_json(MANIFEST_PATH, _manifest(config_hash, schedule_hash, len(accepted_by_id)))
        tqdm.write(f"accepted={len(accepted_by_id)}/{len(schedule)} pending={len(pending_request_ids)} batch_size={batch_size}")
    return [accepted_by_id[row["request_id"]] for row in schedule]


TOTAL_ROWS = SMOKE_TOTAL if CONFIG["smoke_test"] else CONFIG["total_rows"]
SCHEDULE = build_quota_schedule(TOTAL_ROWS, CONFIG["seed"])
ACCEPTED_ROWS = run_generation(SCHEDULE)
'''
```

Ensure the builder's `cells` list includes `RUNTIME_CELL`, `MODEL_CELL`, and `GENERATION_CELL` in that order.

- [ ] **Step 6: Regenerate and run the generation/checkpoint tests**

Run:

```bash
python work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py
python -m pytest tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py -q
```

Expected: `9 passed` and no model download because tests inspect cell source and execute only pure helpers.

- [ ] **Step 7: Commit the resumable generator**

```bash
git add work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py outputs/kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb
git commit -m "feat: add resumable quantized Qwen generation"
```

---

### Task 4: Final audit, exact exports, notebook compilation, and freshness

**Files:**
- Modify: `tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py`
- Modify: `work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py`
- Regenerate: `outputs/kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb`

**Interfaces:**
- Consumes: `ACCEPTED_ROWS`, `SCHEDULE`, `EXPORT_COLUMNS`, and `RUN_ROOT`.
- Produces: `finalize_dataset(rows: list[dict], schedule: list[dict]) -> pandas.DataFrame`.
- Produces runtime files `lgbtq_hatespeech_counter_narratives.csv`, `lgbtq_hatespeech_counter_narratives.xlsx`, `generation_audit.csv`, and `run_manifest.json`.

- [ ] **Step 1: Add failing final-audit and freshness tests**

Add these methods:

```python
    def test_finalize_dataset_enforces_exact_schema_ids_and_quotas(self):
        notebook = self.build_notebook_json()
        functions = extract_notebook_functions(notebook, {"finalize_dataset"})
        schedule = []
        rows = []
        for index, category in enumerate(functions["CATEGORIES"], 1):
            request_id = f"REQ{index:06d}"
            scheduled = {
                "request_id": request_id,
                "category": category,
                "language": "English",
                "platform_style": "X/Twitter reply",
                "abuse_type": "coded mockery",
                "severity": "coded",
            }
            schedule.append(scheduled)
            rows.append({
                "ID": request_id,
                "Text": f"Synthetic harmful sample {index}",
                "Category": category,
                "Target": "a fictional community member",
                "Counter Narrative": f"Synthetic supportive response {index}",
                "language": "English",
                "platform_style": "X/Twitter reply",
                "abuse_type": "coded mockery",
                "severity": "coded",
                "request_id": request_id,
            })
        frame = functions["finalize_dataset"](rows, schedule)
        self.assertEqual(list(frame.columns), ["ID", "Text", "Category", "Target", "Counter Narrative"])
        self.assertEqual(frame["ID"].tolist(), [f"HS{index:06d}" for index in range(1, 6)])
        with self.assertRaisesRegex(RuntimeError, "incomplete_generation"):
            functions["finalize_dataset"](rows[:-1], schedule)

    def test_export_cell_contains_audit_outputs_and_exact_names(self):
        text = self.build_text()
        for value in [
            "lgbtq_hatespeech_counter_narratives.csv",
            "lgbtq_hatespeech_counter_narratives.xlsx",
            "generation_audit.csv",
            "run_manifest.json",
            "category_counts",
            "language_counts",
            "rejection_reason_counts",
            "near_duplicate_threshold",
            "seaborn",
        ]:
            self.assertIn(value, text)

    def test_all_ordinary_python_cells_compile(self):
        notebook = self.build_notebook_json()
        source = "\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        )
        source = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith(("%", "!"))
        )
        compile(source, "kaggle-notebook", "exec")

    def test_tracked_notebook_is_byte_fresh_from_builder(self):
        from work.build_kaggle_qwen35_lgbtq_hatespeech_dataset import build_notebook

        tracked = (
            Path(__file__).resolve().parents[1]
            / "outputs"
            / "kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb"
        )
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / tracked.name
            build_notebook(generated)
            self.assertEqual(tracked.read_bytes(), generated.read_bytes())
```

Update `extract_notebook_functions` with the runtime namespace entries needed by `finalize_dataset`:

```python
        "pd": __import__("pandas"),
        "validate_generated_row": lambda row, scheduled: [],
        "normalize_for_dedup": lambda value: re.sub(r"\\s+", " ", str(value).casefold()).strip(),
```

- [ ] **Step 2: Run tests and verify four new failures**

Run:

```bash
python -m pytest tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py -q
```

Expected: nine earlier tests pass; failures identify the absent `finalize_dataset`, export/audit cell, or stale tracked notebook.

- [ ] **Step 3: Implement fail-closed finalization and exports**

Add `EXPORT_CELL` after `GENERATION_CELL`:

```python
EXPORT_CELL = '''import matplotlib.pyplot as plt
import seaborn as sns


def finalize_dataset(rows, schedule):
    if len(rows) != len(schedule):
        raise RuntimeError(f"incomplete_generation:{len(rows)}/{len(schedule)}")
    schedule_by_id = {row["request_id"]: row for row in schedule}
    row_ids = [row.get("request_id") for row in rows]
    if len(set(row_ids)) != len(schedule) or set(row_ids) != set(schedule_by_id):
        raise RuntimeError("request_id_coverage_mismatch")
    ordered = sorted(rows, key=lambda row: int(row["request_id"][3:]))
    for row in ordered:
        reasons = validate_generated_row(row, schedule_by_id[row["request_id"]])
        if reasons:
            raise RuntimeError(f"final_validation_failed:{row['request_id']}:{','.join(reasons)}")
    if len({normalize_for_dedup(row["Text"]) for row in ordered}) != len(ordered):
        raise RuntimeError("exact_text_duplicate")
    if len({normalize_for_dedup(row["Counter Narrative"]) for row in ordered}) != len(ordered):
        raise RuntimeError("exact_counter_duplicate")
    frame = pd.DataFrame(ordered)
    frame["ID"] = [f"HS{index:06d}" for index in range(1, len(frame) + 1)]
    final = frame.loc[:, EXPORT_COLUMNS].copy()
    if list(final.columns) != EXPORT_COLUMNS or final.isna().any().any():
        raise RuntimeError("final_schema_validation_failed")
    return final


FINAL_DATASET = finalize_dataset(ACCEPTED_ROWS, SCHEDULE)
AUDIT_DATASET = pd.DataFrame(ACCEPTED_ROWS)
category_counts = FINAL_DATASET["Category"].value_counts().sort_index()
language_counts = AUDIT_DATASET["language"].value_counts().sort_index()
platform_counts = AUDIT_DATASET["platform_style"].value_counts().sort_index()
severity_counts = AUDIT_DATASET["severity"].value_counts().sort_index()
rejected_events = load_jsonl(REJECTED_PATH)
rejection_reason_counts = pd.Series(
    [reason for event in rejected_events for reason in event.get("reasons", [event.get("reason", "unknown")])]
).value_counts()

expected_category_count = len(FINAL_DATASET) // len(CATEGORIES)
if any(category_counts.get(category, 0) != expected_category_count for category in CATEGORIES):
    raise RuntimeError("category_quota_mismatch")
expected_language_counts = {
    language: sum(item["language"] == language for item in SCHEDULE) for language in LANGUAGES
}
if language_counts.to_dict() != expected_language_counts:
    raise RuntimeError("language_quota_mismatch")

FINAL_DATASET.to_csv(RUN_ROOT / "lgbtq_hatespeech_counter_narratives.csv", index=False, encoding="utf-8")
FINAL_DATASET.to_excel(RUN_ROOT / "lgbtq_hatespeech_counter_narratives.xlsx", index=False)
AUDIT_DATASET.to_csv(RUN_ROOT / "generation_audit.csv", index=False, encoding="utf-8")
run_manifest = {
    "model_id": CONFIG["model_id"],
    "model_revision": MODEL_REVISION,
    "seed": CONFIG["seed"],
    "total_rows": len(FINAL_DATASET),
    "export_columns": EXPORT_COLUMNS,
    "category_counts": category_counts.to_dict(),
    "language_counts": language_counts.to_dict(),
    "platform_counts": platform_counts.to_dict(),
    "severity_counts": severity_counts.to_dict(),
    "rejection_reason_counts": rejection_reason_counts.to_dict(),
    "near_duplicate_threshold": CONFIG["near_duplicate_threshold"],
    "config_hash": canonical_hash({key: str(value) for key, value in CONFIG.items()}),
    "schedule_hash": canonical_hash(SCHEDULE),
    "package_versions": {
        package: importlib.metadata.version(package)
        for package in ["transformers", "accelerate", "bitsandbytes", "pandas", "scikit-learn"]
    },
}
atomic_write_json(RUN_ROOT / "run_manifest.json", run_manifest)

display(FINAL_DATASET.head())
display(category_counts.rename("count").to_frame())
display(language_counts.rename("count").to_frame())
display(rejection_reason_counts.rename("count").to_frame())
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.barplot(x=category_counts.values, y=category_counts.index, ax=axes[0])
axes[0].set_title("Accepted rows by category")
sns.barplot(x=language_counts.index, y=language_counts.values, ax=axes[1])
axes[1].set_title("Accepted rows by language")
plt.tight_layout()
plt.show()
print("Saved exports to", RUN_ROOT)
'''
```

Include `code(EXPORT_CELL)` as the final notebook code cell.

- [ ] **Step 4: Regenerate the notebook and run targeted verification**

Run:

```bash
python work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py
python -m pytest tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py -q
python -m json.tool outputs/kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb >/dev/null
```

Expected: `13 passed`; JSON validation exits 0.

- [ ] **Step 5: Run repository-level verification and inspect scope**

Run:

```bash
python -m pytest -q
git diff --check
git status --short
git diff --stat semantic-kg-production..HEAD
```

Expected: the full test suite reports zero failures; `git diff --check` exits 0; status shows only pre-existing unrelated changes plus the three notebook feature files; branch diff includes this feature's specification, plan, builder, tests, and generated notebook.

- [ ] **Step 6: Commit the completed notebook**

```bash
git add work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py outputs/kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb
git commit -m "feat: complete Kaggle LGBTQIA hate-speech generator"
```

- [ ] **Step 7: Perform a final requirements audit**

Read `docs/superpowers/specs/2026-08-24-qwen35-hatespeech-dataset-notebook-design.md` and confirm each success criterion against a test or notebook cell. Record the final evidence in the handoff: branch name, commit IDs, targeted/full test counts, notebook JSON validation, exact output path, chosen primary/fallback model IDs, and the fact that the 1,500–2,000-row GPU run remains for Kaggle.
