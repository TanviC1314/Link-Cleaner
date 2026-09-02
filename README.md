# MP-KG-RAG production code archive

This archive contains the local source code used to build and run the four-variant production pipeline: zero-shot, few-shot, KG-RAG, and MP-KG-RAG.

Included:

- Production core, evaluation, export, notebook-builder, visualization, and preview Python modules under `work/`.
- Generated production runtime and notebooks under `outputs/`.
- Locked remote environment requirements.
- Production configuration.
- Automated contract and regression tests.
- Architecture specifications and implementation plans.
- `SHA256SUMS.txt`, which verifies every included file.

Excluded intentionally:

- Input datasets and generated Excel outputs.
- Generation checkpoints, model weights, Hugging Face caches, semantic graph data, and other large runtime artifacts.
- Git history, worktrees, Python caches, screenshots, and browser previews.

Primary production entry point: `outputs/remote_vm_qwen35_mpkg_rag.ipynb`.

Rebuild that notebook with `python work/build_remote_vm_qwen35_mpkg_rag.py`.
