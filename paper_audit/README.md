# paper_audit/

This folder holds the declared patch-validity and verification-trace audit of all 72 main-study
episodes, plus the reconciliation and sensitivity checks. Start with `SUMMARY.md`.

| Path | Content |
| :-- | :-- |
| `SUMMARY.md` | Findings, review disclosure, unresolved issues and limitations |
| `CODEBOOK.md` | Label definitions and decision rules |
| `EXAMPLES.md` | Trace-backed examples with step citations |
| `audit_table.csv` / `.json` | Episode-level table: frozen outcomes, patch stats, first-pass (`auto_*`) and reviewed labels with rationale |
| `summary_tables.md` / `.json` | Aggregates by family, condition and seed |
| `reconciliation.json` | Plan, analysis recomputation, grader hashes, controls, budgets, incidents, host sleep/power, load gate |
| `evidence/<episode>.json` | Per-episode evidence: grade steps, patch inventory and agent lines, every command with return code and output tail, verbatim final message, source paths |
| `regrade/clean-container-1/` | Frozen-grader regrade of all 72 final sources in a fresh, network-less container (`summary.json`: 72/72 match) |
| `environment/` | Container diff after the grid, install-affordance probe, pmset extract, per-episode throughput |
| `tools/` | Scripts that regenerate everything (read-only over `main_runs/`, `results/`, `pilots/`) |
| `reviewed_labels.json` | Reviewed labels as data (generated from `tools/reviewed_labels_source.py`) |

The control replays are in `../restoration_1.2/controls/post-grid-*`, and the logs are in
`../logs/paper_audit/`.

To regenerate, run these from the project root:

```
python3 -I paper_audit/tools/extract_evidence.py
python3 -I paper_audit/tools/reviewed_labels_source.py
python3 -I paper_audit/tools/code_episodes.py
python3 paper_audit/tools/reconcile.py
python3 -I paper_audit/tools/summarize_audit.py
# container-only, no model calls:
python3 paper_audit/tools/regrade_clean.py LABEL
python3 amendment_1.2/control_replay.py LABEL --offline
bash paper_audit/tools/install_affordance_probe.sh
```

The audit itself was done by an AI. See the disclosure in `SUMMARY.md`.
