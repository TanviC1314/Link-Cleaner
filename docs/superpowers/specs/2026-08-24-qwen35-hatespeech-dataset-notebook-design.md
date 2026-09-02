# Qwen3.5 Hate-Speech Dataset Kaggle Notebook Design

## Purpose

Create a self-contained Kaggle notebook that uses an abliterated Qwen3.5 model to generate a synthetic, research-oriented hate-speech dataset for training automated detection and reporting systems. The content will represent severe LGBTQIA+-directed abuse found on social platforms while pairing every harmful example with a constructive counter-narrative.

The notebook will not use real people, usernames, phone numbers, addresses, or other victim-identifying information. All posts and targets will be synthetic.

## Deliverables

- A generated Kaggle-ready notebook at `outputs/kaggle_qwen35_lgbtq_hatespeech_dataset.ipynb`.
- A deterministic builder at `work/build_kaggle_qwen35_lgbtq_hatespeech_dataset.py`.
- Contract tests at `tests/test_kaggle_qwen35_lgbtq_hatespeech_dataset.py`.
- Runtime exports named `lgbtq_hatespeech_counter_narratives.csv` and `lgbtq_hatespeech_counter_narratives.xlsx`.
- A resumable JSONL checkpoint retained in `/kaggle/working/qwen35_hatespeech_generation/`.

The exported dataset will contain exactly these columns, in this order:

1. `ID`
2. `Text`
3. `Category`
4. `Target`
5. `Counter Narrative`

## Model Selection

The primary checkpoint will be [`lukey03/Qwen3.5-9B-abliterated`](https://huggingface.co/lukey03/Qwen3.5-9B-abliterated). It is a text-generation checkpoint derived from Qwen3.5-9B, is marked Apache-2.0 on Hugging Face, documents reduced refusal behavior, and supports direct `transformers` loading. The notebook will load it with 4-bit NF4 quantization through `bitsandbytes` to fit a Kaggle GPU session.

The low-memory fallback will be [`wangzhang/Qwen3.5-4B-abliterated`](https://huggingface.co/wangzhang/Qwen3.5-4B-abliterated). Its model card and configuration explicitly document the same text-only `AutoModelForCausalLM` loading path used by the primary checkpoint. Users can select the fallback by changing one configuration value before model loading. The notebook will not silently switch models after generation begins because mixing checkpoints would reduce dataset reproducibility.

The configuration will record the requested model ID, resolved model ID, model revision when available, quantization settings, random seed, and package versions.

## Dataset Scope

### Row count and balance

- Default total: 2,000 accepted rows.
- Supported reduced run: 1,500 accepted rows.
- Smoke test: 15 accepted rows.
- For 2,000 rows, each category receives exactly 400 rows.
- For 1,500 rows, each category receives exactly 300 rows.
- Any unsupported total will fail validation before model loading. This prevents unclear category remainders.

### Categories

The `Category` column uses this closed set:

1. `Gay Men`
2. `Lesbian Women`
3. `Bisexual People`
4. `Transgender People`
5. `Non-binary/Gender-nonconforming People`

`Target` will contain a concise synthetic target description within the selected category, such as a generic group, community member, couple, student, creator, or public-facing role. It will never contain a real person's identity or handle.

### Language and register

The accepted rows will be balanced as closely as integer quotas allow across:

- English;
- Hindi in Devanagari; and
- Hinglish in Latin script, with natural code-switching.

For 2,000 rows, per-category language quotas will be 134 English, 133 Hindi, and 133 Hinglish rows. For 1,500 rows, each category will contain 100 rows in each language. The internal language label is used for quota enforcement and validation but is removed from final exports to preserve the required five-column schema.

Counter-narratives will use the same language or language mix as their corresponding `Text` value. They will oppose the abusive claim directly, support the targeted person or group, avoid repeating unnecessary slurs, and remain suitable for an automated reply or moderation-assistance workflow.

### Platform styles

Internal generation quotas will rotate through:

- X/Twitter post or reply;
- Instagram comment;
- Instagram-style meme caption;
- YouTube comment or reply;
- public chat or forum message.

Platform style is prompt metadata only and is not exported as an additional column.

### Abuse coverage

The notebook will generate a broad severity distribution, including an explicit extreme tier. Coverage will include:

- coded mockery and insinuation;
- identity-based shaming;
- stereotypes and claims of inferiority;
- misgendering and deadnaming-style constructions using fictional names only;
- profanity, abusive Hindi/Hinglish language, and identity-directed slurs;
- sexualized degradation;
- dehumanization;
- exclusion or denial of rights; and
- threatening or intimidation-style social posts.

The generator prompt will not ask the model to soften or sanitize the harmful `Text`. Severity will be represented honestly for classifier training. The notebook will prohibit real-person targeting, private information, actionable attack coordination, and content that instructs a reader how to commit violence. These exclusions do not remove hostile language or threats as linguistic examples; they prevent the synthetic corpus from becoming operational guidance against real people.

## Notebook Architecture

### 1. Setup and configuration

The first cells will install pinned minimum versions of `transformers`, `accelerate`, `bitsandbytes`, `sentencepiece`, `pandas`, `openpyxl`, `tqdm`, `langdetect`, `scikit-learn`, `matplotlib`, and `seaborn`. A configuration cell will expose total rows, model ID, seed, batch size, sampling values, maximum tokens, checkpoint path, and smoke-test mode.

The notebook will assert that a CUDA GPU is available and display GPU type and memory before downloading the model. It will explain how to enable Kaggle internet access and a GPU accelerator.

### 2. Quota planner

A deterministic quota planner will create the required cells of a category × language × platform × abuse-type × severity schedule. It will distribute the larger balance requirements exactly and rotate the secondary attributes so no single platform or abuse pattern dominates a category.

The planner will assign a stable `request_id` before generation. Resuming a run will reconstruct the same schedule from the configuration and seed.

### 3. Model loading

The primary 9B checkpoint will load using `AutoTokenizer` and `AutoModelForCausalLM` with `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)`, automatic device mapping, and BF16 computation when supported or FP16 otherwise.

The notebook will use the checkpoint's chat template. Thinking will be disabled when supported so the saved response contains only the requested JSON records. No generated chain-of-thought will be persisted.

### 4. Structured batch generation

Each request will ask for a small JSON array. Every object will contain the five export fields plus internal `language`, `platform_style`, `abuse_type`, `severity`, and `request_id` fields. The system prompt will state the research and moderation purpose, require fully synthetic content, require strong variation, and define the closed category vocabulary.

The generation prompt will specify exact quota assignments rather than letting the model choose categories. Sampling will use a fixed seed, controlled temperature, top-p sampling, repetition penalty, and a bounded token budget. Batch size will be configurable and conservative for Kaggle T4 memory.

### 5. Parsing and validation

The parser will extract the first valid JSON array without using `eval`. Records must satisfy all of the following:

- all required fields are present and strings are non-empty;
- `Category` exactly matches the scheduled category;
- internal metadata exactly matches the scheduled quota;
- `Text` and `Counter Narrative` differ;
- `Text` falls within configured character bounds and resembles a short social post;
- `Counter Narrative` falls within configured character bounds;
- neither field contains placeholder language, model disclaimers, refusal text, or prompt leakage;
- neither field contains URLs, email addresses, phone-number-like strings, or `@handles`;
- the output contains no additional export columns;
- a language heuristic agrees with the scheduled language, with Hinglish checked by Latin-script Hindi markers rather than a generic language detector alone.

Invalid objects will be logged with reason codes and returned to the pending quota queue. The notebook will stop with a clear diagnostic if repeated failures exceed the configured per-request limit.

### 6. Deduplication and refill

The pipeline will reject exact duplicates after Unicode normalization and case folding. It will also reject near duplicates within the harmful text and counter-narrative fields using character n-gram TF-IDF cosine similarity. Near-duplicate thresholds will be configuration values shown in the notebook.

Deduplication happens before a row consumes its quota. Rejected rows return their scheduled quota cell to the pending queue. Generation continues until all quotas are filled or the retry budget is exhausted.

### 7. Checkpointing and resume

Every accepted row and rejected-generation event will be appended to separate JSONL files. An atomic manifest will store the configuration hash, schedule hash, model ID, seed, accepted count, and timestamp. A resume is allowed only when the current configuration and schedule hashes match the manifest.

The notebook will never overwrite a mismatched checkpoint. It will instruct the user to choose a new run directory instead.

### 8. Final audit and export

Before export, the notebook will assert:

- total accepted count is exactly the requested total;
- every category quota is exact;
- language quotas are exact;
- IDs are unique and sequential in stable schedule order;
- no required values are missing;
- no exact duplicates remain;
- the final column names and order match the requested schema.

`ID` values will use the stable format `HS000001`, `HS000002`, and so on. Internal metadata will be retained in an audit artifact but excluded from CSV and XLSX exports.

The notebook will display category and inferred-language counts, length summaries, severity/platform audit counts, rejection reasons, and duplicate statistics. It will save a machine-readable run manifest alongside the dataset.

## Error Handling

- Missing GPU: stop before downloading model weights and show Kaggle accelerator instructions.
- Model access or download failure: show the exact model ID and preserve any existing checkpoint.
- CUDA out of memory during loading: recommend selecting the 4B fallback and restarting the kernel; do not silently mix models.
- CUDA out of memory during generation: reduce generation batch size and retry the same scheduled quota without losing accepted rows.
- Malformed JSON: record the failure, retry with a stricter repair prompt once, then return the quota to the pending queue.
- Excessive refusals or invalid content: report failure rates by reason and stop after the configured retry ceiling.
- Checkpoint identity mismatch: fail closed and require a new run directory.
- Incomplete quota at export: refuse to create a final dataset, while retaining checkpoint and diagnostic artifacts.

## Testing Strategy

The notebook will be generated from a Python builder so source cells can be tested without downloading or running the model locally. Tests will verify:

- valid notebook JSON and Kaggle-compatible metadata;
- the primary and fallback Hugging Face model IDs;
- 2,000/1,500/smoke-test quota behavior;
- the exact five categories and final column order;
- presence of 4-bit loading, GPU checks, checkpoint identity, JSON parsing, validation, deduplication, refill, audit, CSV export, and XLSX export;
- absence of unsafe parsing such as `eval`;
- deterministic freshness of the tracked notebook relative to its builder;
- unit behavior for quota construction, row validation, exact deduplication, and final schema checks by extracting pure helper functions from notebook cells.

The verification pass will run the targeted notebook tests, validate the `.ipynb` with Python's JSON parser, compile all ordinary Python source extracted from code cells after excluding notebook magics, and rebuild the tracked notebook to confirm byte-for-byte freshness.

The full 1,500–2,000-row generation will run only on Kaggle because it requires downloading model weights and using a GPU.

## Success Criteria

The work is complete when:

- the tracked notebook is reproducibly generated by its builder;
- all notebook contract and helper tests pass locally;
- the notebook can be uploaded to Kaggle without path edits;
- its default configuration targets exactly 2,000 rows and supports exactly 1,500 rows;
- its export schema is exactly `ID`, `Text`, `Category`, `Target`, `Counter Narrative`;
- all five approved LGBTQIA+ categories have equal representation;
- English, Hindi, and Hinglish quotas are enforced;
- severe and extreme social-media abuse is represented without using real identifiable targets;
- every harmful row has a same-language counter-narrative; and
- interrupted Kaggle sessions can safely resume without duplicating accepted rows.
