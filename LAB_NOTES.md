# Calibration record and exclusions

All work in this package precedes the historical agent study. None of the
following trials is a main-study episode or evidence of the checklist effect.

## Task and environment corrections

- Release tags for L0p4Map and Stellium were version bumps whose parents already
  contained fixes. Trace them to the actual repair commits in the final manifest.
  The related L0p4Map entry-point change shares a prerequisite and is not padded
  into a second independent task.
- RTL source archives contain dangling documentation symlinks. Preserve symlinks
  when copying; their presence is not a runtime packaging failure.
- An implicit host Python 3.11 selected by a repository configuration was broken.
  Build explicitly with the current Python 3.12.14 interpreter.
- A dependency build inherited unavailable clang/clang++; use GCC/G++.
- Add graphviz's Python dependency for older Stellium imports. No graph rendering
  is claimed or required by the selected operation.
- S3's initial empty-result fixture omitted template-required aggregate fields.
  The valid one-bucket fixture makes the upstream fix pass. Its affected source
  still fails, so retain it only as a separate source-failing control.
- Use NumPy 1.26.4 for pixcull, consistent with its bound, rather than unrelated
  shared NumPy 2 import warnings.
- tox source archives lack a generated version.py. A development build produces
  that metadata before source testing, equally for affected and fixed versions.
- Overlapping replays initially reused work directories. The final harness uses
  per-family locks, unique run IDs, fresh consumers and separate build copies.
  Final admitted arm pairs have matching run IDs and freshly executed checks.
- An offline pytest-html preflight found the build-hook npm process selecting the
  inherited uppercase NPM_CONFIG_CACHE rather than the lower-case cache setting.
  Both spellings now point to the same provisioned cache. The earlier mismatch
  is retained under results/calibration-provisioning and excluded from the final
  historical matrix. Producer compilation and consumer-without-npm are distinct
  environments by design. An offline final replay must recover P/P/F vs P/P/P.
- The additional glyph resource-origin control does **not** show that running the
  affected installed wheel from the checkout fixes it. That wheel still fails.
  Preserve the actual negative control rather than inferring resource leakage.

## Live synthetic runner history

v1 used E2B with a constrained JSON response format. Both eight-call checks
failed; the resource checker also had an argument-handling defect. Do not use
that checker outcome as a model capability measurement.

v2 used E2B and bash fences. Function repair passed in six calls. Resource repair
failed after eight calls, but its evaluator had a quoting error. Exclude that
resource outcome from valid capability summaries.

v3 used E4B and bash fences. Function repair passed in four calls. Resource repair
failed after eight calls, but reused workspace files contaminated the setup.
This version is retained for audit, not used as a valid packaging capability
estimate.

v4 used fresh UUID workspaces, E4B and twelve actions. Function repair passed in
four calls. Resource repair failed after twelve calls with the check.py hash
unchanged. The final malformed package-data configuration causes a real build
failure. Affected/no-op and known package-data-fix scorer controls were valid.
This is the final live smoke check, not a treatment comparison. No further model
tuning is performed to obtain a preferred packaging result.

The selected primary model differs from the initial E2B starting configuration.
The change and action limits were chosen during this disclosed synthetic-only
calibration phase. Main Methods fix E4B and a common 24-response episode budget
before any historical main-model call. They make no all-Gemma generalization.

## Final runner preflight

The final study runner has deterministic scripted controls plus actual historical
candidate grading. Its report is results/main_runner_preflight.json. These test
read/edit/execute/stop/export/grade paths; they are not extra model successes.
Zero historical main-study episodes are included in this release.

## Post-freeze agent-tool correction (version 1.1)

A fixed Stellium checkout failed the actual agent's unqualified offline uv build
because .python-version selected unavailable 3.11.4. This was a real setup
failure, despite the pinned grader passing. The controller was interrupted, with
one preliminary pyfiglet trace of eleven responses and 2,255 generated tokens
and no final outcome. Original code, hashes and trace remain under protocol_history
and pilots. The correction explicitly aligns UV_PYTHON and UV_BUILD_CONSTRAINT
with grading. Every fixed reference passes the actual agent build command after
correction. No model/prompt/seed/budget/scoring change or outcome-based selection
is involved. The whole declared grid starts afresh under version 1.1.
