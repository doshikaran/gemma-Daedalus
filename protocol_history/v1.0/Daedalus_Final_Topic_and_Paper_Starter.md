# Do Coding Agents Test What Users Install?
## Evaluating Gemma 4 Across Python Release Artifacts

Working manuscript, expanded 1 November 2026 (Asia/Kolkata). Introduction and
Related Work are drafted. Twelve historical cases have passed affected/reference
validation, and Methods version 1.0 is frozen before main-study generations.
No historical agent-repair results are asserted.

## 1. Introduction

A software repair reaches its users through a release process. In Python, the
files available to tests in a repository need not be the files included in a
wheel. A wheel built directly from a checkout may also differ from a wheel rebuilt
from a source distribution. A coding agent that edits the repository and observes
passing tests must therefore decide whether those checks establish correctness
for the object users will install. This is a verification decision as well as a
code-generation problem.

The distinction is operationally important. Resources can remain available beside
source modules while packaging rules omit them. A command can work when its
module is invoked directly while its installed console entry point resolves a
different or nonexistent target. A release workflow can build through an archive
whose contents differ from the checkout used during development. Successful
archive creation and installation do not, on their own, establish that the
required public operation works.

Historical reports provide concrete examples. RTLDesignSherpa-DV documented
timing-table CSV files that were present in its checkout but absent from built
wheels [7]. Its public timing loader consequently failed after installation.
L0p4Map's release notes describe an omitted module needed by its console entry
point [8]. Separately, pixcull's maintained packaging configuration records a
release-route discrepancy: direct wheel builds appeared healthy while source
archives omitted Python files needed by the wheel built from them [9]. These are
known upstream defects. They motivate the study and are not presented as our
discoveries or as evidence of a population failure rate.

Existing work already demonstrates that test success can be incomplete evidence
of software engineering success. SWE-Gate measures functional correctness
separately from review-derived acceptance constraints [2]. Building to the Test
shows that a tested demo can bypass the reusable library the task requests [3].
Keystone-Eval investigates tests that execute an installed copy when they should
exercise a checkout, using mutations to check the link between source and
verification [4]. Our question concerns the corresponding release obligation:
when an installed package is the deliverable, does agent verification establish
the behavior of that package, including the route by which it is built?

We study this question using historical Python packaging repairs and a fixed
Gemma-based coding-agent configuration. For each final patch, an independent
evaluator exercises the declared public behavior in the source checkout, an
installed wheel built directly from the checkout, and an installed wheel rebuilt
from a source distribution as required by every task contract. The evaluator
records artifact identities and imported module locations. This separates a
repair's behavior across legitimate artifacts rather than assuming that one
passing command certifies all of them.

The study addresses three research questions:

- **RQ1 — Correctness across artifacts:** How often does apparent source-level
  success disagree with the same repair's behavior after the required build and
  installation routes?
- **RQ2 — Verification behavior:** Which artifacts do agents actually exercise
  before declaring completion, and which failure mechanisms remain undetected?
- **RQ3 — Conventional guidance:** Does an explicit release-verification
  checklist improve complete repair success under the same model and budget?

Our planned contributions are a pinned historical task resource, paired
behavioral measurements across artifact states, and a controlled comparison
against an established engineering workflow. Clean installation tests are
already recommended practice [6]. The contribution must therefore be new
evidence about agent behavior and the remaining verification gap, rather than
a claim that these checks are a new repair algorithm. A null or saturated
comparison remains reportable. Quantitative claims will be written only after
the frozen experiment is complete.

## 2. Related Work

### Agentic build repair

Build-bench evaluates agents repairing genuine package failures during migration
between x86_64 and aarch64 [1]. Its taxonomy includes packaging failures and its
primary success criterion is a successful rebuild on the target architecture.
It is therefore direct prior work for agentic package repair. Our proposed
measurement holds the platform fixed and evaluates a public operation across
the source checkout and two distribution routes from the same final patch.
It asks what a successful build and the agent's selected checks establish about
the installed behavior. This is a narrower, incremental measurement distinction,
not evidence that package repair has previously been ignored.

### Acceptance constraints and delivered behavior

SWE-Gate supplies separate executable checks for functional requirements and
review-derived constraints [2]. It establishes the need to evaluate the complete
repair specification. Building to the Test uses behavioral tests and a separate
library audit to show that an apparently successful demo may not exercise the
requested reusable implementation [3]. Both overlap with the broad motivation
that a passing score may certify an incomplete deliverable. Our tasks instead
use historical packaging boundaries and evaluate the same externally specified
operation across explicitly identified artifacts. Whether this supplies a
substantive additional insight depends on the completed cohort and results.

### Correct verification targets and oracle validity

Keystone-Eval studies development-environment configuration and reports cases in
which tests ran against downloaded wheels rather than the intended checkout [4].
It uses breaking mutations to investigate whether verification depends on the
requested source. We take that as an established precedent for recording what
code is actually tested. Here the installed distribution is itself a required
target, so loading the source tree during an installed-package check would be
the mismatch. The evaluator therefore verifies import origins and keeps the
direct-wheel and source-distribution routes separate.

Oracle-integrity auditing also identifies defects inside an evaluator, including
state contamination that changes measured agent outcomes [5]. Our source check
can be internally correct while offering insufficient evidence about a different
artifact. These are distinct failure modes, but both require known-answer
controls, preservation of evaluator integrity, and explicit separation of model
errors from infrastructure and scoring errors.

### Python packaging practice

PyPA guidance recommends complete source distributions and discusses building
wheels through them and validating distribution contents [6]. We use those
conventional practices as a baseline. File presence, archive construction,
installation and public runtime behavior are separate checks: a file omitted
intentionally is not automatically a bug, and a present file need not be usable.
Each admitted task therefore needs a behavior justified by upstream requirements
and an affected/reference distinction. Our proposed resource concerns the
behavior of coding agents under that contract, not the invention of packaging
verification.

## 3. Methods

### 3.1 Historical tasks and admission

We have calibrated twelve historical bug families from ten Python repositories.
Each family has pinned affected and upstream-fixed revisions, archive hashes,
documented release preparation and an executable public-operation check. Eight
affected cases pass in source but fail in both installed routes; three pass in
source and the direct wheel but fail through the sdist. A twelfth case, an S3
reporting template absent even in source, is a separate source-failing control.
All twelve reference revisions pass all three artifact checks. These 72
artifact-state checks validate the resource; they are not model repair episodes.

| Family | Repository | Affected source / wheel / sdist-wheel |
| :-- | :-- | :-- |
| Timing CSVs | RTLDesignSherpa-DV | Pass / Fail / Fail |
| Console module | L0p4Map | Pass / Fail / Fail |
| Font extensions | pyfiglet | Pass / Fail / Fail |
| HTML template | apotrope | Pass / Fail / Fail |
| Transformer data | pynecore | Pass / Fail / Fail |
| Source modules | pixcull | Pass / Pass / Fail |
| Translation catalogs | stellium | Pass / Fail / Fail |
| SVG glyphs | stellium | Pass / Fail / Fail |
| Offline location cache | stellium | Pass / Fail / Fail |
| Build-time manpage | tox | Pass / Pass / Fail |
| Consumer-side npm invocation | pytest-html | Pass / Pass / Fail |
| Missing report template, control | s3-security-scanner | Fail / Fail / Fail |

The primary stratum contains eleven gap families across nine repositories.
Three Stellium cases arise from different commits but remain correlated. This
purposive sample cannot estimate how common packaging failures are. The manifest
records each full revision and operation; no group of missing files from one fix
is counted as multiple families.

### 3.2 Agent and controlled comparison

We fix Google's Gemma 4 E4B instruction QAT Q4_0 GGUF [10] at revision
`4b4a2c1d584be7264f87aac328a1bc739ce81b6c`, with a recorded SHA-256, and
llama.cpp b12020 on CPU. Both conditions use four threads, one inference slot,
a 32,768-token context, thinking enabled with reasoning budget 128, and
temperature 0.2. The sole tool is a shell with Python, git, uv and npm.

Condition A receives the public behavior and the explicit obligation to support
source, direct-wheel and sdist-wheel consumers. B receives the same contract and
tools plus a conventional release checklist covering fresh builds, outside-
checkout installation, real operation checks and import/resource origins. A may
perform every check available to B. Guidance, rather than a hidden additional
correctness requirement, is the treatment.

There are three fresh attempts per task-condition, seeds 19, 23 and 41: 72
planned episodes, including six separate control episodes. A fixed randomized
ordering is preserved. Every episode has at most 24 responses, 8,192 generated
tokens, 20 minutes of interaction and 120 seconds per command; each response is
limited to 1,024 tokens. Provisioning and final independent grading are outside
that interaction budget. Exact prompts, tools, environment, ordering and scoring
are frozen in the reproducibility package before any historical main-study call.

### 3.3 Independent artifact grading

The grader exports the final patch into fresh source copies, builds the direct
wheel separately from the sdist route, installs each into a fresh target and
exercises the selected operation. Isolated Python processes assert target import
origins; installed consumers run outside the checkout. A failed prerequisite
build or installation fails its route. Wheel and sdist hashes are retained.
Successful installation alone is insufficient.

Release preparation is explicit: pyfiglet's upstream font sets are copied into
its release directory, tox's source version module is generated through a
development build, and pytest-html's JavaScript is compiled on the producer side.
Its sdist consumer rebuild has a PATH verified to lack npm. SCM version metadata
is normalized because the pinned archives lack Git history. Preparation and
constraints apply equally to affected, reference and candidate revisions.

The glyph source check uses the repository root. A supplementary control runs
the affected installed wheel from that same directory; it still fails. Resource-
open traces locate the source SVGs in checkout assets and the fixed wheel's SVGs
inside its installed package. This distinguishes the artifact/path mechanism
from a failure explained only by changed current directory.

The primary endpoint is artifact-contract success: all three required public-
operation checks pass. It does not certify unrelated application functionality
or full upstream test suites. Report no-ops, exhausted attempts and unsupported
completion claims. Frozen graders are hashed before and after agent interaction;
patch audit separately flags bypasses or fixture-specific hardcoding. API,
provisioning and oracle errors remain distinct from model failures and receive
no silent fresh attempts.

### 3.4 Analysis, calibration and limitations

Report the complete family-condition-seed-state matrix. Compare the mean
within-family B-minus-A success difference in the eleven-family gap stratum;
analyze the source-failing control separately. Repeated attempts and artifact
checks do not increase the independent family count. Repository-cluster bootstrap
intervals and repository-macro sensitivity acknowledge the correlated Stellium
cases and small sample. They are descriptive, not evidence of universal effects.

Runner calibration is disclosed separately. In its final fresh-workspace live
check, Gemma repaired a basic function in four calls but failed a synthetic
packaging-resource task after twelve calls. The known-answer resource scorer
rejected the affected toy package and accepted its fix. The final runner also
underwent deterministic tool/patch-export checks and historical no-op/reference
grading controls. Earlier calibration corrections are retained. These checks
validate infrastructure without predicting model success or contributing to the
main treatment comparison.

Public historical fixes create contamination risk. The scope is selected
Python/Linux operations with provisioned dependencies, an instruction-bounded
local shell, and one small quantized model. The runner is not a hardened security
sandbox. Low capability may produce a floor effect; null, negative and saturated
results remain reportable. Clean-install checks are established practice, so
claims of novelty must concern the resource and empirical findings.

## 4. Results status

Historical resource calibration is complete: all twelve affected revisions fail
at least one specified state, and all twelve reference fixes pass every state.
Main-study model episodes completed: **zero**. The checklist effect and agent
verification patterns remain unknown. The final Results, Discussion, Abstract
and conclusion must be written from the executed main-study evidence.

## References

1. [Build-bench: author project and protocol](https://aiops-lab-nku.github.io/Build-bench/).
2. [SWE-Gate](https://arxiv.org/abs/2609.04167).
3. [Building to the Test](https://arxiv.org/html/2606.28430v1).
4. [Keystone-Eval](https://imbue.com/blog/keystone-eval).
5. [When Agent Evaluation Becomes Unreliable](https://arxiv.org/abs/2610.16067).
6. [PyPA: Supporting downstream packaging](https://packaging.python.org/en/latest/discussions/downstream-packaging/).
7. [RTLDesignSherpa-DV issue 49](https://github.com/sean-galloway/RTLDesignSherpa-DV/issues/49).
8. [L0p4Map module-packaging fix](https://github.com/HaxL0p4/L0p4Map/commit/5a1d38753beaa1b031c1828701dd3da5f3fe1350).
9. [pixcull packaging configuration](https://github.com/ChrisChen667788/pixcull/blob/2bc2eaeb0ad2e03ec8464c48b50ce43189861828/pyproject.toml).
10. [Google Gemma 4 E4B QAT GGUF](https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf).
