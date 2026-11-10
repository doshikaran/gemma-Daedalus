# Experiment status

Updated: 2026-11-05T13:05:19.942918+00:00 (UTC).

**paused: 54/72 episodes have final records.**

Current episode: `53-pytest-html-npm-A-41`; 1 completed responses, 168 generated tokens.

Automated artifact-contract passes so far: 0; infrastructure outcomes: 1. These are provisional counts, not a final treatment comparison.

All 72 planned episodes use the fixed model, prompts, seeds, tools and budgets. The twelve historical families include eleven artifact-gap cases and one separately analyzed source-failing control. No best-of-attempt selection or silent retries.

One initial v1.0 setup attempt was interrupted after eleven responses before a final outcome. Its trace and the original freeze are retained. Protocol 1.1 aligns agent interpreter/backend selection with the grader; conditions, tasks, model, seeds, budgets and scoring remain fixed.

The controller advances through the entire queue and writes the declared analysis after all 72 valid records. Manual patch and verification-trace audits remain separate. `Daedalus_Experiment_Checkpoint.zip` contains completed trajectories, patches, protocol history and interim evidence.

Execution issue: RuntimeError('Infrastructure outcome retained; review required before continuing')
