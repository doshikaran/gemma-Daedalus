# Experiment status

Updated: 2026-11-03T19:26:23.555430+00:00 (UTC).

**paused: 9/72 episodes have final records.**

Current episode: `09-tox-sdist-A-41`; 0 completed responses, 0 generated tokens.

Automated artifact-contract passes so far: 0; infrastructure outcomes: 0. These are provisional counts, not a final treatment comparison.

All 72 planned episodes use the fixed model, prompts, seeds, tools and budgets. The twelve historical families include eleven artifact-gap cases and one separately analyzed source-failing control. No best-of-attempt selection or silent retries.

One initial v1.0 setup attempt was interrupted after eleven responses before a final outcome. Its trace and the original freeze are retained. Protocol 1.1 aligns agent interpreter/backend selection with the grader; conditions, tasks, model, seeds, budgets and scoring remain fixed.

The controller advances through the entire queue and writes the declared analysis after all 72 valid records. Manual patch and verification-trace audits remain separate. `Daedalus_Experiment_Checkpoint.zip` contains completed trajectories, patches, protocol history and interim evidence.

Execution issue: RuntimeError('tox version preparation failed: {"args": ["uv", "build", "--python", "/usr/local/bin/python3", "--wheel", "--out-dir", "/workspace/scratch/93af20bbcd93/packaging_study/main_runs/09-tox-sdist-A-41/repo/.agent-source-preparation", "--build-constraints", "/workspace/scratch/93af20bbcd93/packaging_study/build-constraints.txt", "--cache-dir", "/workspace/scratch/93af20bbcd93/packaging_study/.uv-cache"], "returncode": 2, "stdout": "", "stderr": "Building wheel...\\nerror: Failed to build `/workspace/scratch/93af20bbcd93/packaging_study/main_runs/09-tox-sdist-A-41/repo`\\n  cause: Failed to resolve requirements from `build-system.requires`\\n  cause: No solution found when resolving: `docutils>=0.21`, `hatch-vcs>=0.5`, `hatchling>=1.29`\\n  cause: Because you require hatchling>=1.29 and hatchling==1.27.0, we can conclude that your requirements are unsatisfiable.\\n", "seconds": 0.22271071800059872}')
