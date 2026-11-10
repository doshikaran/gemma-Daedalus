# Frozen experimental methods, version 1.1

This is a local, timestamped protocol freeze before the restarted main-study batch. It is not an external preregistration. `FREEZE.json` identifies the exact
files; amendments must preserve this version, give a reason and identify whether
any main outcomes had been viewed. Calibration is a separate disclosed phase.


## Recorded correction after the original freeze

The original version 1.0 and its hash manifest are preserved in
`protocol_history/v1.0/`. An additional audit showed that a fixed Stellium
checkout could not build using the actual agent's bare `uv build`: it selected
unavailable Python 3.11.4, while grading explicitly selected Python 3.12.14.
One initial pyfiglet episode was interrupted after eleven responses and 2,255
generated tokens, with no final outcome. Its entire available trace is retained
under `pilots/v1.0-setup/`; it is not counted as a main repair attempt.

Version 1.1 aligns the agent tool environment with the grader through
`UV_PYTHON` and the task-specific `UV_BUILD_CONSTRAINT`. All twelve known fixed
references then pass direct-wheel and sdist builds using the actual bare agent
tool command, in offline mode. Model, prompts, tasks, seeds, budgets, condition
definitions and scoring are unchanged. No final repair outcome had been viewed
when this correction was specified. This is an explicit setup amendment, not a
silent retry or an outcome-based exclusion. The complete 72-episode grid restarts
from its original randomized order and fresh workspaces.

The runner also records the initial git baseline independently, so an agent's
commit cannot make its captured repair patch appear empty, and retains partial
trajectories on transport errors. A response cut off by the episode wall deadline is a budget outcome; its unreported partial generation cost is marked unknown, not recorded as a measured zero. After a completed grade, expanded temporary
work trees may be compressed; final source, patches, actual release artifacts
and logs are retained. These data-retention changes do not alter agent inputs
or grading. A sequential controller advances the queue, writes live status and
runs the frozen descriptive analysis after 72 valid result records.

## Research questions and estimands

RQ1 measures disagreement among final-patch source, direct-wheel and sdist-wheel
contract checks. RQ2 codes which artifacts agents actually exercised before a
completion claim. RQ3 compares conventional release guidance with ordinary
verification, holding the correctness contract, tools and budgets fixed.

The primary endpoint is **artifact-contract success**, requiring the declared
public operation in all three states, including successful prerequisite builds
and installations. It is deliberately scoped to the stated operation; passing
does not certify the entire GUI, security scanner, language runtime or library.
Do not relabel this endpoint as unrestricted software correctness.

## Cohort and admission

There are twelve historical fix families in ten repositories. Eleven are the
primary artifact-gap stratum, spanning nine repositories. The S3 HTML-template
case also fails in source and is a separate control. Eight primary cases have
affected-state P/F/F; three have P/P/F. Every upstream reference is P/P/P.
P/F refer to source/direct wheel/sdist-to-wheel, in that order. This is purposive
case selection; 11/12 is not an estimated population prevalence.

Each task has exact affected/fixed revisions, source archive hashes, a public
behavior contract, release preparation and executable probes. A version-bump
commit is not used as a fix when its parent already contains the repair. Several
missing files from one commit are one family; the three Stellium cases are
different historical fixes but correlated within one repository.

`task_manifest.json`, `task_validation.csv` and the 24 arm-result JSONs preserve
the complete calibration matrix. These are **72 artifact-state checks**, not 72
model episodes. All reference fixes pass the selected operation. Full upstream
test suites have not been established as passing and are not claimed.

## Model, transport and tools

The main model is Google's instruction-tuned Gemma 4 E4B QAT Q4_0 GGUF:

- Repository: `google/gemma-4-E4B-it-qat-q4_0-gguf`.
- Revision: `4b4a2c1d584be7264f87aac328a1bc739ce81b6c`.
- Filename: `gemma-4-E4B_q4_0-it.gguf`, 5,154,941,280 bytes.
- SHA-256: `676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee`.

llama.cpp b12020 runs on CPU, four compute and batch threads, one slot,
32,768-token context and reasoning budget 128. Temperature is 0.2, thinking is
enabled, and each response is limited to 1,024 generated tokens. Both model
server and client run in the same process tree. Only final response text is used
as an action; hidden reasoning is not a tool command. The runtime release archive
hash is pinned in `protocol.json`; weight and runtime acquisition logs are included.

The agent returns one bash code block or a `COMPLETE` statement. Available tools
are bash, Python, git, uv and npm. The shell runs in the assigned repository with
preinstalled dependency paths and offline build caches. No upstream history or
reference patch is put in the workspace. Instructions prohibit external research
files and network services. This is an **instruction-bounded local runner**, not
a hardened OS sandbox; the simple command guard does not provide security
isolation. The external grader is hashed before and after each episode.

The environment is Python 3.12.14 on Linux. Exact observed tool versions and
dependency sets are in `protocol.json` and `locks/*.txt`. NumPy 1.26.4 is used for
pixcull. Shared dependency directories are explicitly inserted into isolated
Python `-I` processes; target-package import origins are checked. This is not a
claim of a separate complete dependency environment for every application.

## Conditions and allocation

A receives the task's public operation, the requirement to work in all three
artifact states, the repository instructions and ordinary tools. B receives the
identical materials plus a conventional checklist: fresh builds, clean installed
consumers, real public-operation tests, import/resource origins and final retests.
A may choose any of the same checks. Thus the treatment supplies a procedure,
not an extra requirement or exclusive capability.

Exact common/system/checklist text lives in `prompts/`; task contracts live in the
manifest. Both conditions have three fresh attempts, seeds 19, 23 and 41. The
72 episodes comprise 66 primary and six control episodes. Order is shuffled once
with Python's random generator seeded 20261101 and saved in `episode_plan.json`.
There is no best-of-three selection: every attempt is an observation.

Each episode permits at most 24 model responses, including malformed actions and
completion, 8,192 cumulative generated tokens, 20 minutes of interaction, and
120 seconds per command (bounded by remaining wall time). Tool feedback retains
the final 4,000 characters. Initialization and independent grading are outside
the interaction budget. No main-study generation is used to choose these values.
The synthetic calibration used smaller action limits and is not a treatment run.

## Clean builds, grading and release preparation

Each episode starts from a fresh affected archive. A local git repository records
the baseline without upstream history. Final indexed source, including new
unignored files, is exported; ignored build debris is excluded. No intermediate
patch is selected. Fresh source copies are then used for direct and sdist builds.
The sdist is extracted, rebuilt into a wheel, installed into a fresh target, and
tested from a fresh consumer outside the checkout. Prerequisite failures fail
the corresponding route. Actual wheel and sdist hashes and imported origins are
recorded. These checks establish behavior, not bit-for-bit reproducible builds.

Three preparation rules are explicit: pyfiglet's upstream font sets are copied
to its release fonts directory; tox's generated source version module is produced
by a development build; pytest-html's JavaScript is compiled with npm on the
producer side. Direct and sdist builds receive separate prepared copies. The
pytest-html consumer rebuild has a PATH checked to lack npm. SCM versions are
normalized to `0.0.0+audit` because GitHub archives lack repository metadata.
This normalization does not claim to reproduce the original published version.

Fixtures are offline and exercise actual public operations: real font rendering,
translation lookups, HTML generation, CLI help, SVG parsing, timing loading,
offline location lookup and initialization. Security scans, AWS access, GUIs and
unrelated heavyweight workloads are outside scope. The location fixture rejects
online geocoding and fresh consumers prevent cache contamination.

The glyph source check uses the checkout root, unlike installed consumers. An
additional control runs the affected installed wheel from that same source CWD;
it still fails. Python audit events show source SVGs under checkout `assets/` and
the fixed wheel's SVGs under installed `stellium/data/glyphs/`. This supports a
resource-path/artifact distinction without attributing it solely to CWD.

## Scoring integrity and trace annotation

Every final state is graded, including no-ops, exhausted attempts and unsupported
completion claims. Frozen-grader changes invalidate the run pending an integrity
audit. Patch review separately flags deleted checks, fixture-specific hardcoding
or bypassed public functionality. Automated contract pass and those flags must
both be reported; an apparent pass is not silently promoted to a valid repair.

For RQ2 record source/direct/sdist operations separately. A build command alone
does not count as a runtime check. An installation alone does not count as testing.
Code a verified installed operation only when the trajectory establishes a real
operation, its installed import origin and an outside-checkout consumer. Mark
unclear evidence as unknown, not success. Retain the command and output supporting
each label. Human annotation is a transparent audit, not a claimed validated
automatic classifier; borderline labels receive a written rationale.

Infrastructure/API errors stop the episode and retain its partial log; they are
not automatically retried as fresh model chances. Oracle and provisioning defects
are distinguished from model failures. Any replacement requires an explicit
protocol amendment and a retained original. Analyses refuse an incomplete grid
or unhandled infrastructure errors rather than silently changing denominators.

## Analysis and limitations

Report every family, condition, seed and artifact result first. Primary RQ3 is
the mean within-family B-minus-A success difference over three attempts, in the
eleven-family gap stratum. The source-failing control is separate. Report a
repository-cluster bootstrap interval (10,000 draws, seed 36721), repository-macro
sensitivity and grouping of the three Stellium fixes. Nine primary repositories
provide weak precision; intervals are descriptive and no winning-result threshold
is preselected. Repeated states/attempts are not independent bug families.

Public fixes allow memorization; Python/Linux limits scope; the selected tasks
do not estimate prevalence. Quantization, short budgets, CPU inference and low
model capability may create floor effects. The final synthetic packaging check
failed despite a correct known-answer scorer. That negative result is retained.
If the main comparison is null or saturated, report it. The intervention is
established engineering guidance; the potential contribution is a task resource
and empirical understanding, not invention of clean-install testing.

## Runner checks before freezing

Live synthetic calibration v4 used fresh workspaces: basic function repair passed
in four calls; packaging-resource repair failed after twelve calls. The grader
was unchanged. Known-answer packaging controls reject the affected toy package
and accept a package-data fix. Earlier v1-v3 are retained, including scorer and
workspace corrections, in `results/calibration-v*/` and `LAB_NOTES.md`.

`preflight.py` separately checks the final runner's action parsing, malformed
feedback, edit/execute path, token stop, deterministic balanced episode grid,
patch export and **actual candidate grading** against historical RTL no-op/fix
controls. Scripted responses here test infrastructure, not model capability.
The live checks and deterministic controls do not assert that Gemma will repair
the historical cohort. At the version 1.1 freeze, **zero completed historical main-study outcomes** exist; the interrupted eleven-response setup attempt is disclosed above.
