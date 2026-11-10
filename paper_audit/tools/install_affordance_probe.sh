#!/bin/bash
# Audit-only probe (no model calls): which installation routes worked under the frozen agent
# tool environment? Uses the rtl-data *reference* source and the exact environment recorded in
# main_runs/10-rtl-data-A-41/tool_environment.json, in a scratch copy under /tmp of the
# container it runs in. Prints one line per route with its return code.
# Usage (inside a container, from ROOT): bash paper_audit/tools/install_affordance_probe.sh
set -u
ROOT=$(pwd)
ENVJSON=main_runs/10-rtl-data-A-41/tool_environment.json
REF=$(python3 -c "import json;print(json.load(open('sources/rtl-data-provenance.json'))['reference']['directory'])")
W=/tmp/install-affordance; rm -rf $W; mkdir -p $W; cp -r "$REF" $W/repo
AGENT_ENV=$(python3 -c "import json,shlex;print(' '.join(f'{k}={shlex.quote(v)}' for k,v in json.load(open('$ENVJSON')).items()))")
run() { local name=$1; shift; out=$(cd $W/repo && env -i $AGENT_ENV bash -c "$*" 2>&1); rc=$?; printf '%s\trc=%s\t%s\n' "$name" "$rc" "$(echo "$out" | tail -2 | tr '\n' ' ' | cut -c1-220)"; }
run build_wheel          'uv build --wheel --out-dir dist'
run pip_on_path          'pip --version'
run python_m_pip_install 'python3 -m pip install --no-deps dist/*.whl'
run uv_pip_system        'uv pip install --no-deps dist/*.whl'
run uv_venv_activate     'uv venv /tmp/install-affordance/v1 && source /tmp/install-affordance/v1/bin/activate && uv pip install --no-deps dist/*.whl'
run uv_pip_target        'uv pip install --no-deps --target /tmp/install-affordance/t dist/*.whl'
run uv_venv_python_flag  'uv venv /tmp/install-affordance/v2 && uv pip install --no-deps --python /tmp/install-affordance/v2/bin/python dist/*.whl'
run consumer_from_target 'cd /tmp && PYTHONPATH=/tmp/install-affordance/t:$PYTHONPATH python3 -c "import CocoTBFramework.components.dfi.jedec_timings as j; print(j.__file__); print(j.builtin_timings(\"ddr3-1600\").tCK_ns)"'
