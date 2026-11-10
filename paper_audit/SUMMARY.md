# Daedalus paper audit: patch validity, verification traces and reconciliation

Status: **72 of 72 episodes audited.** No new Gemma attempts were made. No frozen record,
grade, score, exclusion or analysis was changed. Numbers below come from `audit_table.csv`,
`summary_tables.json` and `reconciliation.json`, which the scripts in `tools/` regenerate.

## Review disclosure

This audit is AI-assisted. Claude (Anthropic) wrote the extraction and coding scripts, read every
agent patch, every executed command with its return code and output tail, and every final
message, then assigned the reviewed labels in `tools/reviewed_labels_source.py`, each with a
written rationale. A rule-based first pass (`auto_*` columns) is kept beside the reviewed labels.
There was one reviewer and no independent second coder, so no inter-rater agreement exists.
Labels are a transparent audit, not a validated classifier. Borderline cases carry rationales,
and ambiguous evidence is coded as not established rather than success. Human spot-checking
of `audit_table.csv` against `evidence/*.json` is recommended before publication.

## 1. Reconciliation with the frozen plan, analysis and graders

- **Plan.** There are 72 records. Their IDs, tasks, conditions, seeds and orders equal
  `episode_plan.json`, and the regenerated plan is identical. All records are protocol 1.1, 36 A
  and 36 B, with 0 infrastructure records in the final set.
- **Analysis.** Recomputing with the frozen `analyze.summarize` reproduces
  `results/main_analysis.json` exactly: 0 artifact-contract passes, and every family difference
  is 0.
- **Graders.** Grader, analysis and constraint files match `FREEZE.json`. `run_study.episode`
  calls `verify_freeze()` after the agent finishes and before grading. Records do not store
  per-episode grader hashes, so this rests on the code path and the unchanged freeze.
- **Reference controls.** The frozen v1.1 results match the manifest on 24/24 (affected
  P/F/F or P/P/F; every reference P/P/P). Replays of the unchanged grader also give 24/24:
  - before the grid: offline-1, online-warm-2 and offline-final-container;
  - after the grid: in a fresh container from the same image with no network
    (`post-grid-clean-container`);
  - after the grid: in the post-grid container, with its agent-installed packages still
    present (`post-grid-contaminated-container-2`).

  Two aborted replay attempts are retained with notes.
- **Clean regrade.** Every retained final source was regraded by the frozen grader in the clean,
  network-less container. All 72/72 patterns equal the recorded grades
  (`regrade/clean-container-1/summary.json`). The shared-interpreter contamination described in
  section 6 therefore did not change any grade.

## 2. Outcome patterns (RQ1): source, direct wheel and sdist-wheel

The full family × condition × seed matrix is in `summary_tables.md`.

- **Gap stratum (66 episodes):** P/F/F 41 (A 22, B 19); P/P/F 11 (A 5, B 6); F/F/F 14 (A 6, B 8).
  No episode reached P/P/P, and no episode improved on its affected state.
- **Source-failing control (s3-template, 6 episodes):** F/F/F in all 6, the same as affected.
  It is reported separately and not counted below.
- **Source passed but an installed route failed:** 52 of 66 gap episodes (A 27, B 25). Every
  gap episode whose source passed had an installed-route failure; 41 failed both installed
  routes and 11 failed only the sdist route.
- **Direct-wheel/sdist disagreement:** 11 gap episodes, all P/P/F, all in the three families
  whose affected state is already P/P/F (pixcull, tox, pytest-html).
- **Regressions:** 16 gap episodes are worse than their affected state (14 to F/F/F, 2 from
  P/P/F to P/F/F); see `summary_tables.json` → `regressions`. The other 50 gap episodes keep the
  affected pattern.
- **Where grading failed:** most failures were in the installed probe (wheel 57, sdist-wheel
  59). Agent-induced build or preparation failures account for 19 stage failures.

## 3. Patch validity

| Label | A | B |
| :-- | --: | --: |
| No functional agent change | 18 | 17 |
| Ineffective edit | 6 | 7 |
| Broken edit (syntax/config) | 5 | 7 |
| Fixture-specific or destructive | 7 | 5 |
| Plausible partial / valid repair | 0 | 0 |

Flags across all 72 episodes:

- `syntax_or_config_break` 15
- `fixture_hardcoding` 12, including 4 of 6 s3-control episodes that hardcode a synthetic bucket
  and 2 that special-case the Alexandria fixture
- `misdiagnosis` 9
- `destructive_data_loss` 6
- `scratch_file_committed` 2
- `test_added` 1
- `masks_errors` 1

No episode deleted or weakened tests. Because there is no automated pass, no flag changes any
score. The flags are reported as METHODS requires.

## 4. Routes agents actually tested (RQ2)

Build, installation and runtime are coded separately. Known origins are listed in `CODEBOOK.md`.

- **Source route:**
  - The contract operation succeeded from the checkout in 4 episodes (A 2, B 2), all
    l0-module-actual. Its source state already passed when affected.
  - Related but non-contract operations ran in 6 (import only, the default font, `--help`, or
    agent-fabricated data). In 1 more the output showed failure, and in 1 the package came from
    PyPI rather than the candidate.
  - 21 attempts failed, mostly `ModuleNotFoundError` from src layouts or missing pytest. 12
    episodes only inspected files, and 27 did nothing runtime-related.
- **Builds:**
  - 7 episodes produced an artifact (A: 07, 53; B: 30, 33, 41, 61, 71). In 53 and 71 the build
    was of a pre-edit tree that later edits broke.
  - No episode rebuilt a wheel from an sdist of its final state.
- **Installations:** the candidate was installed in 1 episode (61), into the shared container
  interpreter with `--break-system-packages`. There the installed console command was run and
  failed with the real defect.
- **Verified installed operations:** 0. No episode checked an import origin, and none used an
  outside-checkout consumer.
- **By condition, the direct-wheel route was attempted more under B:** 13 of 36 B episodes and
  10 of 36 A episodes made any build or install attempt. Every attempt failed or stopped before
  runtime.
- **Install affordances.** The frozen agent environment had no `pip` on PATH. `python -m pip`,
  `uv pip install` into the interpreter, and `uv venv` with `activate` were refused (PEP 668 /
  `UV_PYTHON`).

  An audit-only probe under the exact agent environment
  (`environment/install_affordance_probe_clean_container.txt`) found two working routes:
  `uv pip install --target DIR` and `uv pip install --python .venv/bin/python`. A consumer in
  `/tmp` then ran the reference operation from the installed copy.

  No agent used either route. The frozen preflight
  (`results/agent_tool_environment_preflight.json`) checked builds only, not installation. This
  constrains RQ2: absent installed verification partly reflects an environment where the common
  install commands fail.

## 5. Completion messages (read in full)

43 episodes stopped on a completion claim (A 23, B 20). They are not all false claims.

| Class | A | B |
| :-- | --: | --: |
| Bare `COMPLETE` (no assertion) | 5 | 3 |
| Explicit non-repair ("cannot perform the required repair") | 1 | 0 |
| Hedged (verification incomplete or impossible) | 4 | 5 |
| Unhedged success claim | 13 | 12 |

- **Unhedged claims:** all 25 are contradicted by the frozen grade.
- **What the 34 success or hedged claims rest on:** inspection or reasoning in 23, a partial
  executed check in 6, and unconditional echo text or no executed command at all in 5 (11, 13,
  15, 22, 53).
- **Claims about installed routes:** 12 messages assert that an installed route was verified or
  works (A: 07, 66, 68; B: 06, 11, 13, 15, 22, 30, 40, 41, 50). None has an installed operation in
  its trace.
- **Edits that never happened:** 7 messages describe an edit absent from the final patch (11,
  15, 22, 25, 37, 40, 42). Typical causes are a multi-line `sed` that silently matched nothing,
  an `echo "Fix applied"`, or comments-only changes.

The checklist condition (B) produced more installed-route assertions (9 vs 3) without more
installed verification. This is descriptive only.

## 6. Infrastructure, sleep, power, load and budget reconciliation

- **Replacements.** Four infrastructure incidents were replaced, each with its amendment and
  retained attempt: 09 (amendment 1.3), 50 (1.4), 53 (1.5) and 55 (1.7). Each retained original
  and its incident record exist in `pilots/`, and each replacement record exists. The v1.0
  setup attempt and the v1.1 interrupted attempt are retained and not counted.
- **Host sleep.** Episodes 31 (18,734 s asleep inside its window) and 32 (5,790 s) overlapped
  lid-closed sleep. Their recorded interaction times (482 s, 266 s) exclude it. Both were kept
  per amendment 1.4 and are disclosed.
- **Power at start**, from orchestrator-observed windows (macOS logs power only at sleep/wake):
  - AC observed: 34
  - AC, checked at launch only: 9
  - AC, guarded by amendment 1.4: 3
  - battery: 26 (24 in the 2026-11-04/05 window, 2 under amendment 1.6)
- **Load gate.** Amendment 1.5 waits are in `reconciliation.json` → `load_gate`.
- **Throughput.** Model throughput varied from 3.9 to 14.3 generated tokens per model-second
  (median on battery 7.6, AC 7.6–10.5; `environment/throughput_by_episode.json`).
- **Budget stops.** All 7 wall-clock budget stops (36, 43, 44, 45, 49, 57, 60) occurred in
  slower periods, mostly on battery, which is a disclosed confound. 9 other budget stops were
  token-bound.
- **Budget accounting.** Accounting is consistent for all 72:
  - token sums equal the records;
  - no call, token or wall budget was exceeded (max 24 calls, 8,192 tokens, 1,200.1 s);
  - every `action_limit` stop has 24 calls;
  - every `completion_claim` ends in `COMPLETE`.

  The 7 wall stops each end in a deadline-cut request, with `generated_token_accounting =
  lower_bound_partial_timeout`.
- **Format errors.** 384 responses were rejected as malformed. Five episodes executed no
  command at all.

## Unresolved issues and limitations

1. **Shared-interpreter contamination across episodes.**
   - Agents installed packages into the shared container interpreter with
     `pip --break-system-packages`:
     - episode 41: build;
     - episode 57: tox 4.67.13 and hatchling;
     - episode 61: PyQt6 and the candidate l0p4map.
   - Later agents saw a different tool environment. Episodes 53 and 71 used the `build` module
     installed by episode 41.
   - The clean regrade shows grades were unaffected. Agent behaviour after episode 41 may not
     have been. The container diff is retained (`environment/container_diff_after_grid.txt`).
   - The protocol did not anticipate this, and it is not corrected.
2. **Network access during the main study.**
   - The amendment-1.2 container used a bridged network. The protocol's offline intent was
     enforced only through environment variables (`UV_OFFLINE`, npm offline) and command
     blocklist strings.
   - Agents in episodes 41, 57 and 61 downloaded from PyPI, and episode 57's tox run initialized
     pre-commit environments.
   - This departs from `offline_during_main: true` and was not disclosed in amendment 1.2. It
     needs a disclosure amendment.
3. **Install affordances never preflighted.** See section 4. Its effect on RQ2 cannot be
   separated from model capability.
4. **No per-episode grader-hash record.** Integrity rests on the code path and the unchanged
   freezes.
5. **Power and throughput.** Battery operation and host contention changed throughput (3.9–14.3
   tok/s) and plausibly caused the 7 wall-budget stops. Power for 9 episodes was checked only at
   launch, and the AC periods on 2026-11-06 were observed only at manual checks.
6. **Single AI reviewer.** There is no second coder and no human adjudication yet.
7. **All-zero primary result.**
   - 0/66 primary and 0/6 control episodes pass. The B−A difference is 0 in every family, with
     a degenerate [0, 0] interval.
   - This is a floor effect of a small quantized CPU model under short budgets and a constrained
     environment. It does not show that the checklist has no effect, and it does not establish
     equivalence between conditions.
   - Public historical fixes, repository clustering (three Stellium families), purposive case
     selection and the Python/Linux scope also limit interpretation.
