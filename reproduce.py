"""Restore pinned public inputs and replay the historical artifact matrix.

Provisioning uses the network; study episodes use provisioned offline caches.
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import subprocess

from acquire import checkout
from replay import ROOT, replay
import replay_pytesthtml
from run_study import tree_digest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fetch',action='store_true')
    parser.add_argument('--dependencies',action='store_true')
    parser.add_argument('--replay',action='store_true')
    parser.add_argument('--task')
    args=parser.parse_args()
    tasks=json.loads((ROOT/'task_manifest.json').read_text())['tasks']
    if args.task:
        tasks=[x for x in tasks if x['id']==args.task]
        if not tasks:raise SystemExit('Unknown task')
    for folder in ['runtime','sources','results','logs','calibration','artifacts']:
        (ROOT/folder).mkdir(exist_ok=True)
    if args.fetch:
        for task in tasks:
            data={'id':task['id'],'repository':task['repository']}
            for arm in ['affected','reference']:
                row=checkout(task['repository'],task[arm]['sha'])
                if row['archive_sha256']!=task[arm]['archive_sha256']:
                    raise RuntimeError('Upstream archive bytes changed: '+task['id']+' '+arm)
                if tree_digest(row['directory'])!=task[arm]['tree_sha256']:
                    raise RuntimeError('Source tree differs from frozen baseline: '+task['id']+' '+arm)
                data[arm]=row
            (ROOT/'sources'/(task['id']+'-provenance.json')).write_text(json.dumps(data,indent=2)+'\n')
    if args.dependencies:
        env={**os.environ,'CC':'gcc','CXX':'g++'}
        for name in ['probe-deps','build-env','pixcull-deps','tox-deps','pytesthtml-deps']:
            subprocess.run(['uv','pip','install','--target',str(ROOT/'runtime'/name),'--no-deps',
                            '-r',str(ROOT/'locks'/(name+'.txt'))],check=True,env=env)
    if args.replay:
        names=[x['id'] for x in tasks if x['id']!='pytest-html-npm']
        with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:
            list(pool.map(replay,names))
        if any(x['id']=='pytest-html-npm' for x in tasks):replay_pytesthtml.main()


if __name__=='__main__':main()
