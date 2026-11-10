"""Build the auditable task registry and protocol from executed calibration files."""
import csv
import hashlib
import json
import pathlib
import platform
import subprocess
from run_study import tree_digest

ROOT = pathlib.Path(__file__).resolve().parent
DATA = [
 ('rtl-data','bundled tables','gap', 'The public builtin_timings loader must load DDR2 and DDR3 timing tables, including ddr2-650-mt47h64m16hr (tCK_ns 3.077) and ddr3-1600 (1.25).', 'No extra preparation.'),
 ('l0-module-actual','console entry point/module','gap', 'The l0p4map console command must display its normal --help successfully after installation; source main.py --help must also work. No network scan or GUI execution is required.', 'No extra preparation.'),
 ('pyfiglet-154','font resource extensions','gap', 'pyfiglet.figlet_format must render ordinary text with the bundled circle and future fonts. Preserve both font profiles and normal package imports.', 'Copy both upstream fonts-standard and fonts-contrib into pyfiglet/fonts, matching upstream release preparation. Apply equally to both revisions and all build routes.'),
 ('apotrope-template','HTML template','gap', 'Reporter.generate_html_report must create an HTML report containing the hostname from an AuditReport fixture. The scope is offline report export, without a Windows system scan.', 'No extra preparation.'),
 ('pynecore-data','transformer JSON resources','gap', 'The installed pynecore package must import normally and expose callable pynecore.types.Series. Do not remove the transformer initialization to hide its data-loading failure.', 'No extra preparation.'),
 ('pixcull-sdist','missing source modules in sdist','gap', 'pixcull.i18n.load_locale and t must load English and Chinese dictionaries and return a real translated value. Both direct-wheel and source-distribution consumers are supported.', 'Use the separate numpy 1.26.4 dependency directory ahead of shared dependencies; this operation does not launch the GUI or inference models.'),
 ('stellium-locales','translation catalogs','gap', 'stellium.i18n must list zh_CN, translate Chart Overview to 星盘概览, and preserve an unknown translation key.', 'No extra preparation.'),
 ('stellium-glyphs','SVG resources and source-relative paths','gap', 'stellium.visualization.core.get_glyph must return valid SVG data for both Pholus and Eris, rather than its Unicode fallback. Source usage from the checkout root and installed usage outside it must work.', 'Source check runs from the source root; installed checks use clean consumers. An additional installed-wheel/source-CWD control records actual SVG open paths.'),
 ('stellium-cache','offline geolocation cache','gap', 'Native must resolve Alexandria, Egypt at approximately latitude 31.2 and longitude 29.9 from bundled data with online geocoding disabled. Use a fixed date/time and preserve ordinary construction.', 'Patch Nominatim.geocode to raise during grading, preventing an online service from concealing missing cache data. Use fresh consumers to avoid cache leakage.'),
 ('tox-sdist','manpage required during rebuild','gap', 'The tox --help command must succeed from the source, direct wheel and wheel rebuilt from the sdist. The source archive must contain inputs needed for the latter build.', 'Generate the source development version.py through a preparatory wheel build before the source check; use hatchling 1.29.0 constraints. Direct and sdist routes use separate fresh source copies.'),
 ('pytest-html-npm','sdist rebuild invokes absent npm','gap', 'pytest-html must generate a self-contained HTML report for a passing pytest test. A consumer must be able to rebuild its published sdist without npm when the compiled JavaScript asset has been prepared for release.', 'Run npm ci and npm run build as release preparation; make fresh prepared copies for direct and sdist builds. The sdist-to-wheel step uses a PATH verified to contain no npm. Disable pytest plugin autoload and load only metadata and html plugins.'),
 ('s3-template','template absent even in source','source-failing-control', 'HTMLReporter.generate_report must write an HTML report including the name of a synthetic S3 bucket and a valid nonempty summary. No AWS calls or bucket scans are required.', 'Use one offline bucket fixture and all required aggregate fields. This is explicitly a source-failing control, not evidence of source success hiding installation failure.'),
]


def main():
    tasks, matrix = [], []
    for name, mechanism, stratum, contract, prep in DATA:
        provenance = json.loads((ROOT/'sources'/f'{name}-provenance.json').read_text())
        affected = json.loads((ROOT/'results'/f'{name}-affected.json').read_text())
        reference = json.loads((ROOT/'results'/f'{name}-reference.json').read_text())
        assert affected['run_id'] == reference['run_id']
        assert all(x['pass'] for x in reference['rows']), name
        assert not all(x['pass'] for x in affected['rows']), name
        states = {arm: ''.join('P' if x['pass'] else 'F' for x in result['rows'])
                  for arm, result in [('affected',affected),('reference',reference)]}
        task = {'id':name, 'repository':provenance['repository'], 'mechanism':mechanism,
                'stratum':stratum, 'contract':contract, 'preparation':prep,
                'states':states, 'validation_run_id':affected['run_id'],
                'affected':{k:v for k,v in provenance['affected'].items() if k!='directory'},
                'reference':{k:v for k,v in provenance['reference'].items() if k!='directory'},
                'fix_url':'https://github.com/'+provenance['repository']+'/commit/'+provenance['reference']['sha'],
                'source_url':'https://codeload.github.com/'+provenance['repository']+'/tar.gz/'+provenance['affected']['sha'],
                'required_states':['source','wheel','sdist-wheel']}
        for arm in ['affected','reference']:
            task[arm]['tree_sha256']=tree_digest(provenance[arm]['directory'])
        tasks.append(task)
        matrix.append({'id':name,'repository':task['repository'],'stratum':stratum,
                       'affected_source':affected['rows'][0]['pass'], 'affected_wheel':affected['rows'][1]['pass'],
                       'affected_sdist_wheel':affected['rows'][2]['pass'], 'reference_all':True,
                       'run_id':affected['run_id']})
    out={'version':'1.0','selection':'Purposive historical bug sample; no population prevalence estimate',
         'families':len(tasks),'repositories':len({x['repository'] for x in tasks}),
         'primary_gap_families':11,'source_failing_controls':1,'tasks':tasks}
    (ROOT/'task_manifest.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    with (ROOT/'task_validation.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(matrix[0]));writer.writeheader();writer.writerows(matrix)
    protocol={
      'version':'1.1','main_completed_episodes_at_freeze':0,'historical_model_responses_before_v1_1_freeze':11,
      'model':{'repository':'google/gemma-4-E4B-it-qat-q4_0-gguf',
        'revision':'4b4a2c1d584be7264f87aac328a1bc739ce81b6c',
        'filename':'gemma-4-E4B_q4_0-it.gguf',
        'sha256':'676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee',
        'bytes':5154941280},
      'runtime':{'llama_cpp':'b12020','archive_sha256':'1b69032f9ab60dc6aa909689fda941fa1b9162f6ab46b863582d5649d96ac6be',
        'device':'CPU','threads':4,'batch_threads':4,'parallel':1,'context_tokens':32768,'reasoning_budget':128},
      'endpoint':'http://127.0.0.1:18090','temperature':0.2,'response_tokens':1024,
      'episode_generated_tokens':8192,'max_actions':24,'wall_seconds':1200,'command_seconds':120,
      'tool_output_characters':4000,'attempt_seeds':[19,23,41],'ordering_seed':20261101,
      'episodes':72,'primary_episodes':66,'control_episodes':6,
      'conditions':{'A':'Common contract and tools; ordinary verification',
                    'B':'Identical contract and tools plus conventional release checklist'},
      'scoring':{'primary':'All three required artifact-state probes pass, including successful builds and installs. Label artifact-contract success; it is not whole-program correctness.',
        'primary_population':'11 gap families; the source-failing family is a separate control.',
        'secondary':['Source-pass/installed-fail for final patches','Direct-wheel/sdist-route disagreement','Observed verification actions and their actual targets','Completion claims unsupported by independent grading','Tokens, actions and elapsed time'],
        'integrity':'Hash frozen graders before and after each episode. Export only final indexed source; do not select best intermediate patches. Inspect patches for fixture-specific bypasses and report them separately.',
        'infrastructure':'No silent retries. Preserve failed trajectory and classify API, environment and oracle errors separately from model failures.'},
      'analysis':{'unit':'Historical bug family; attempts and artifact checks are repeated measures.',
        'comparison':'Mean within-family B-minus-A difference over three seeds; full per-family matrix first.',
        'uncertainty':'Repository-cluster bootstrap, 10000 resamples, seed 36721; descriptive with only nine primary repositories. Report repository-macro sensitivity and all three Stellium families together.',
        'no_population_prevalence':True},
      'environment':{'python':platform.python_version(),'platform':platform.platform(),
        'uv':subprocess.check_output(['uv','--version'],text=True).strip(),
        'node':subprocess.check_output(['node','--version'],text=True).strip(),
        'npm':subprocess.check_output(['npm','--version'],text=True).strip(),
        'offline_during_main':True,'compiler':'GCC/G++','version_normalization':'SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0+audit'},
      'scope_limits':['Python/Linux public operations; no claim of full application correctness.',
        'Public historical fixes may be memorized.', 'Three Stellium fixes are correlated at repository level.',
        'Shared installed dependency directories are used with isolated Python -I processes and asserted target import origins; not per-task full dependency environments.',
        'Instruction-bounded shell runner is not a hardened security sandbox.',
        'CPU quantization and low model capability can create floor effects.',
        'No causal claim that checklist guidance is novel; effect remains unknown.']}
    protocol['amendment']='PROTOCOL_AMENDMENT_1.1.json'
    protocol['excluded_setup_attempts']={'count':1,'completed_responses':11,'completed_outcomes':0,'location':'pilots/v1.0-setup'}
    protocol['environment']['agent_interpreter']='UV_PYTHON is the explicit current Python 3.12.14 executable'
    protocol['environment']['agent_backend_constraints']='UV_BUILD_CONSTRAINT selects the same task-specific constraint file used by grading'
    protocol['retention']='After grading, preserve patch, compressed final source, actual release artifacts, complete trajectories and result records; reclaim only expanded generated episode trees.'
    (ROOT/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    (ROOT/'prompts').mkdir(exist_ok=True)
    (ROOT/'prompts/system.txt').write_text('You are a coding agent working inside the current repository. Respond with exactly one bash code block containing the next shell command to execute. You can inspect files and use Python, bash, git, uv and npm to edit and test the project. After testing, respond COMPLETE with a short summary and no code block. All paths are relative to the current repository. Do not inspect parent directories, research logs, hidden evaluators or upstream patches. Do not access network services. Do not alter or delete tests to conceal failures. Repair the implementation or its release configuration; do not hardcode the evaluation fixture. Repository instructions apply. The shell is the only tool.\n')
    (ROOT/'prompts/common.txt').write_text('Repair this historical Python package at the supplied affected revision. Required behavior: {{TASK}}\nThe behavior must work in the source checkout, an installed wheel built directly from it, and an installed wheel rebuilt from its source distribution. Preserve normal behavior. Python runtime dependencies and build caches have been provisioned. Use the repository instructions and any checks you judge necessary. Report what you actually verified. Internet access is outside the task.\n')
    (ROOT/'prompts/checklist.txt').write_text('Conventional release-verification checklist:\n1. Check the required public operation in the source checkout.\n2. Build the direct wheel, install it, and exercise that operation in a fresh consumer directory outside the checkout.\n3. In a fresh source copy, build the sdist; rebuild its wheel without relying on checkout-only files or producer-only tools; install and exercise the same operation.\n4. Check which package file was imported and where required resources were read. A successful build or install alone does not establish runtime behavior.\n5. Retest the required operations after your final edit and state which artifact routes you verified.\n')
    print(json.dumps({'families':len(tasks),'repositories':out['repositories'],'states':{k:sum(x['states']['affected']==k for x in tasks) for k in ['PFF','PPF','FFF']}}))


if __name__=='__main__':main()
