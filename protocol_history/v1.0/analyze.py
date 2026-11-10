"""Frozen descriptive analysis, refuses to present an incomplete grid as complete."""
import json
import random
import statistics
from pathlib import Path
from run_study import ROOT, grid


def summarize(records, tasks, protocol):
    expected={x['episode_id'] for x in grid(protocol,tasks)}
    observed={x['episode_id'] for x in records}
    if expected!=observed or len(records)!=len(expected):
        raise ValueError('The 72-episode grid is incomplete or duplicated; do not infer final effects.')
    if any('infrastructure_error'in x or 'grading_infrastructure_error'in x for x in records):
        raise ValueError('Resolve and disclose infrastructure exclusions/amendments before effect estimation.')
    families=[]
    for task in tasks:
        rates={c:statistics.mean(int(x['artifact_contract_pass'])for x in records
               if x['task']==task['id'] and x['condition']==c)for c in ['A','B']}
        families.append({'id':task['id'],'repository':task['repository'],'stratum':task['stratum'],
                         **rates,'B_minus_A':rates['B']-rates['A']})
    primary=[x for x in families if x['stratum']=='gap']
    repositories=sorted({x['repository'] for x in primary})
    rng=random.Random(36721);samples=[]
    for _ in range(10000):
        sampled=[rng.choice(repositories)for _ in repositories]
        values=[x['B_minus_A']for repo in sampled for x in primary if x['repository']==repo]
        samples.append(statistics.mean(values))
    samples.sort()
    return {'families':families,'primary_family_mean_difference':statistics.mean(x['B_minus_A']for x in primary),
      'repository_macro_difference':statistics.mean(statistics.mean(x['B_minus_A']for x in primary if x['repository']==r)for r in repositories),
      'repository_cluster_percentile_95_interval':[samples[249],samples[9749]],
      'interpretation':'Descriptive paired guidance comparison; small, purposive, correlated cohort.'}


if __name__=='__main__':
    protocol=json.loads((ROOT/'protocol.json').read_text())
    tasks=json.loads((ROOT/'task_manifest.json').read_text())['tasks']
    records=[json.loads(p.read_text())for p in (ROOT/'main_runs').glob('*/result.json')]
    result=summarize(records,tasks,protocol)
    print(json.dumps(result,indent=2))
