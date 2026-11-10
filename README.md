# Do Coding Agents Test What Users Install?

Research preparation package, 1 November 2026. Start with the expanded manuscript
`Daedalus_Final_Topic_and_Paper_Starter.md` and the detailed `METHODS.md`.

## Completed and pending

- Introduction and Related Work drafted, with three explicit research questions
  and a bounded distinction from build repair, acceptance constraints and test-
  target/oracle studies.
- Twelve historical bug families validated across ten repositories. All fixed
  references pass source, direct-wheel and sdist-wheel operation checks.
- Eleven families exhibit an artifact gap; one source-failing control is separate.
- Model, prompts, budgets, ordering and scoring fixed in protocol version 1.1.
- Runner infrastructure checked; live synthetic function repair passed and live
  synthetic packaging repair failed. Preserve both outcomes.
- **Main-study historical agent episodes completed: zero.** No intervention gain,
  universal failure rate, novel repair algorithm or prize outcome is claimed.

## Evidence map

| File | Purpose |
| :-- | :-- |
| `task_manifest.json` | Full revisions, archive/tree hashes, contracts and preparation |
| `task_validation.csv` | All twelve affected/reference artifact outcomes |
| `results/*-affected.json`, `*-reference.json` | Executed build/install/probe commands, outputs, artifact hashes |
| `results/glyph_resource_origin_control.json` | Source/installed resource-path and CWD controls |
| `results/runner_calibration.json` | Final live synthetic calibration trajectory |
| `results/calibration-v*/` | Preserved earlier calibration history |
| `results/main_runner_preflight.json` | Final runner infrastructure and historical candidate controls |
| `LAB_NOTES.md` | Corrections, exclusions and scope limits |
| `protocol.json`, `prompts/`, `episode_plan.json` | Exact controlled-study setup |
| `FREEZE.json` | Timestamp and SHA-256 for frozen local inputs |
| `run_study.py`, `analyze.py` | Main runner and declared descriptive analysis |
| `reproduce.py`, `replay*.py`, `locks/` | Public-input restore and historical replay |

## Reproduction

The package excludes downloaded model weights, source archives, upstream fonts,
dependency installations and caches. It records pinned URLs/hashes instead.
Public repositories and model licenses continue to apply. This package does not
relicense or redistribute those upstream resources. Provisioning requires network
access, Python 3.12.14, uv 0.13.4, Node 24.22.1/npm 11.9.0, git and GCC/G++ on Linux.
Use the recorded platform information when diagnosing differences.

From the extracted package directory:

```bash
python3 reproduce.py --fetch --dependencies --replay
python3 bootstrap_model.py
python3 preflight.py
python3 run_study.py --plan
```

The first replay warms the build and npm caches. The main runner sets offline
cache use. `--task TASK_ID` limits historical restore/replay. Upstream tarball
byte drift is an integrity failure, not permission to silently replace an input.
Relocated source-directory pointers in provenance are refreshed by `--fetch`;
the frozen normalized manifest and archive/tree identities remain unchanged.

The bundled `FREEZE.json` describes the original preparation. Replaying or
regenerating local evidence can change run IDs and paths; preserve the original
records before producing a new local freeze. No need to regenerate the manifest
to inspect or run the original episode plan. Model hashes are checked before
main execution.

The following command **starts real main-study episodes**; it is not a smoke test:

```bash
python3 run_batch.py
```

The original v1.0 freeze and one interrupted eleven-response setup attempt are retained. v1.1 corrects interpreter/backend selection in agent tools; all twelve fixed references now pass the actual agent build command. See `PROTOCOL_AMENDMENT_1.1.json`.

The sequential controller updates `Experiment_Status.md`, retains completed evidence and computes the declared analysis after the full grid. `python3 run_batch.py --resume` retains completed valid episodes and never retries an infrastructure outcome silently. The runner refuses to overwrite an existing episode. A declared individual
episode can be selected with `--episode EPISODE_ID`. Run the full retained grid
before final effect estimation. `python3 analyze.py` refuses incomplete grids or
unresolved infrastructure outcomes. It must not be used to turn calibration into
paper results. Trace annotation rules for RQ2 and manual patch-bypass flags are
specified in `METHODS.md`.

## Writing next

Keep the Introduction and Related Work, execute the frozen study, then write
Results, Discussion, Abstract and conclusion from its logs. Describe the released
resource and observed artifact/verification patterns. Clean-install testing is
conventional practice; any claim of additional insight must be supported by the
actual study. A null or floor result is a valid outcome, not grounds for hidden
task removal or a changed denominator.
