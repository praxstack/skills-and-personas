#!/usr/bin/env python3
"""Subscription v2 public/held-out transport. Scoring is a separate operation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

VERSION = 2
TEACHING_FILES = ('SKILL.md', 'references/MODE-CONTRACT.md', 'references/TEACHING-PROTOCOL.md',
                  'references/VISUALIZATION-ROUTER.md', 'references/ARTIFACT-CONTRACT.md',
                  'references/LEARNER-STATE.md')
EXCLUDED = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.DS_Store'}
DISABLED_FEATURES = ('shell_tool', 'unified_exec', 'apps', 'plugins', 'hooks', 'memories',
                     'multi_agent', 'browser_use', 'computer_use', 'image_generation',
                     'view_image', 'skill_search', 'sleep_tool', 'goals', 'code_mode')

def bundle(source):
    parts = []
    hashes = {}
    for name in TEACHING_FILES:
        path = source / name
        if path.is_file():
            data = path.read_bytes()
            hashes[name] = digest(data)
            parts.append('FILE: ' + name + '\n' + data.decode('utf-8'))
    text = '\n\n'.join(parts)
    if len(text.encode()) > 200000:
        raise ValueError('teaching bundle exceeds frozen 200KB context limit')
    return text, hashes

def no_tools(events):
    for line in events.splitlines():
        event = json.loads(line)
        if any(word in event.get('type', '').lower() for word in ('tool', 'command', 'mcp')):
            return False
        item = event.get('item', {})
        if item and item.get('type') not in ('agent_message', 'reasoning', 'error'):
            return False
    return True


def digest(data):
    return hashlib.sha256(data).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def tree(root, reject_hardlinks=True):
    result = {}
    for p in sorted(root.rglob('*')):
        if any(part in EXCLUDED for part in p.relative_to(root).parts):
            continue
        if p.is_symlink() or (reject_hardlinks and p.is_file() and p.stat().st_nlink != 1):
            raise ValueError('symlink/hardlink rejected: ' + str(p))
        if p.is_file():
            result[str(p.relative_to(root))] = digest(p.read_bytes())
    return result

def link_counts(root):
    return {str(p.relative_to(root)): p.stat().st_nlink for p in root.rglob('*')
            if p.is_file() and not any(part in EXCLUDED for part in p.relative_to(root).parts)}

def validate_scenario(data):
    if set(data) != {'id', 'turns'} or not isinstance(data['id'], str):
        raise ValueError('teaching scenario accepts only id and turns; no grading data')
    if not data['id'] or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in data['id']):
        raise ValueError('invalid scenario id')
    if not isinstance(data['turns'], list) or not data['turns'] or any(not isinstance(x, str) or not x for x in data['turns']):
        raise ValueError('turns must be nonempty user strings')
    return data

def profile(work, home, binary):
    """Permit provider networking/runtime; deny private source/bank/other arms."""
    exceptions = ' '.join('(require-not (subpath ' + json.dumps(str(x)) + '))' for x in (work, home, binary))
    return '\n'.join(['(version 1)', '(allow default)',
        '(deny file-read-data (require-all (subpath "/Users") ' + exceptions + '))',
        '(deny file-read-data (require-all (subpath "/private/var") (require-not (subpath ' + json.dumps(str(home)) + '))))',
        '(deny file-read-data (subpath "/Volumes") (subpath "/private/tmp"))',
        '(deny file-write*)', '(allow file-write* (subpath ' + json.dumps(str(work)) + ') (subpath ' + json.dumps(str(home)) + ') (subpath "/dev"))'])

def execute(cmd, prompt, env, timeout):
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=env, cwd=env.get('HOME'), start_new_session=True)
    try:
        out, err = process.communicate(prompt.encode(), timeout=timeout)
        return process.returncode, out, err, False
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        out, err = process.communicate()
        return process.returncode, out, err, True

def run(baseline, candidate, scenario, output, model, seconds=600, repetitions=3, auth=None):
    scenario = validate_scenario(scenario)
    baseline, candidate, output = (Path(x).resolve() for x in (baseline, candidate, output))
    if repetitions not in (1, 3) or seconds <= 0:
        raise ValueError('public smoke uses 1 replicate; acceptance uses 3; positive deadline required')
    for source in (baseline, candidate):
        if not (source / 'SKILL.md').is_file():
            raise ValueError('each package root must contain SKILL.md')
        if output == source or source in output.parents or output in source.parents:
            raise ValueError('receipt/source overlap')
    bundles = {name: bundle(p) for name, p in [('baseline', baseline), ('candidate', candidate)]}
    if set(bundles['baseline'][1]) != set(bundles['candidate'][1]):
        raise ValueError('paired teaching bundle path sets differ')
    source_hashes = {name: tree(p) for name, p in [('baseline', baseline), ('candidate', candidate)]}
    source_links_before = {name: link_counts(p) for name, p in [('baseline', baseline), ('candidate', candidate)]}
    output.mkdir(parents=True, exist_ok=False)
    os.chmod(output, 0o700)
    binary = Path(shutil.which('codex')).resolve()
    auth = Path(auth or Path.home() / '.codex/auth.json')
    version = subprocess.check_output([str(binary), '--version'], text=True).strip()
    config = {'version': VERSION, 'model': model, 'seconds_per_arm': seconds, 'repetitions': repetitions,
              'scenario_sha256': digest(json.dumps(scenario, sort_keys=True).encode()),
              'binary': str(binary), 'binary_sha256': digest(binary.read_bytes()), 'cli_version': version,
              'runner_sha256': digest(Path(__file__).read_bytes()), 'source_hashes': source_hashes, 'bundle_hashes': {k: v[1] for k, v in bundles.items()},
              'source_links_before': source_links_before, 'excluded_package_parts': sorted(EXCLUDED), 'transport': 'tool-less subscription broker with sequential role replay', 'disabled_features': DISABLED_FEATURES,
              'eligible_for_held_out_claims': False,
              'eligibility_reason': 'requires independent same-build boundary probe review and sealed-bank freeze'}
    write_json(output / 'config.json', config)
    failed = False
    for rep in range(1, repetitions + 1):
        for arm, source in [('baseline', baseline), ('candidate', candidate)]:
            dest = output / f'{rep}-{arm}'
            dest.mkdir(mode=0o700)
            work = dest / 'workspace'
            work.mkdir()
            shutil.copytree(source, work / 'package', ignore=shutil.ignore_patterns(*EXCLUDED))
            # Model tools are disabled; the retained package is audit material only.
            with tempfile.TemporaryDirectory(prefix='teach-auth-') as tmp:
                home = Path(tmp).resolve()
                os.chmod(home, 0o700)
                shutil.copyfile(auth, home / 'auth.json')
                os.chmod(home / 'auth.json', 0o600)
                env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': str(home), 'CODEX_HOME': str(home),
                       'TMPDIR': str(home), 'LANG': 'en_US.UTF-8'}
                profile_file = dest / 'sandbox.sb'
                profile_file.write_text(profile(work, home, binary))
                cmd = ['/usr/bin/sandbox-exec', '-f', str(profile_file), str(binary), '--no-daemon',
                       '-a', 'never', 'exec', '--ignore-user-config', '--ignore-rules', '--ephemeral',
                       '--skip-git-repo-check', '-C', str(work), '-s', 'read-only', '-m', model,
                       '-c', 'project_doc_max_bytes=0', '-c', 'web_search="disabled"',
                       '--json', '-o', str(work / 'response.txt'), '-']
                cmd[cmd.index('--json'):cmd.index('--json')] = [value for feature in DISABLED_FEATURES for value in ('-c', 'features.' + feature + '=false')]
                write_json(dest / 'command.json', cmd)
                history = []
                started = time.monotonic()
                for index, turn in enumerate(scenario['turns'], 1):
                    remaining = seconds - (time.monotonic() - started)
                    if remaining <= 0:
                        failed = True
                        write_json(dest / f'turn-{index}.json', {'timed_out': True, 'exit_code': None})
                        break
                    prompt = 'You are a teaching assistant operating without ANY tools or filesystem access. Follow the teaching bundle below. Do not claim to read/save/render/inspect files or execute tools. Deliver actual Markdown, SVG or HTML source in your response where useful. Runtime persistence/consent is independently tested; here explain actions honestly without pretending to execute them. The ordered conversation contains only actual prior turns; answer the final user turn.\nTEACHING BUNDLE\n' + bundles[arm][0] + '\nCONVERSATION\n' + json.dumps(history + [{'role': 'user', 'content': turn}])
                    (work / 'response.txt').unlink(missing_ok=True)
                    (dest / f'turn-{index}.prompt.txt').write_text(prompt)
                    code, out, err, timeout = execute(cmd, prompt, env, remaining)
                    (dest / f'turn-{index}.stdout.jsonl').write_bytes(out)
                    (dest / f'turn-{index}.stderr.txt').write_bytes(err)
                    response = (work / 'response.txt').read_text() if (work / 'response.txt').exists() else ''
                    (dest / f'turn-{index}.response.txt').write_text(response)
                    write_json(dest / f'turn-{index}.json', {'exit_code': code, 'timed_out': timeout,
                               'stdout_sha256': digest(out), 'stderr_sha256': digest(err), 'response_sha256': digest(response.encode()), 'no_tool_events': no_tools(out)})
                    history += [{'role': 'user', 'content': turn}, {'role': 'assistant', 'content': response}]
                    if code or timeout or not response or not no_tools(out):
                        failed = True
                        break
                write_json(dest / 'conversation.json', history)
            # Temporary credentials removed before hashing retained artifacts.
            write_json(dest / 'artifacts.json', tree(work, reject_hardlinks=False))
            if tree(work / 'package', reject_hardlinks=False) != source_hashes[arm]:
                failed = True
    if tree(baseline, reject_hardlinks=False) != source_hashes['baseline'] or tree(candidate, reject_hardlinks=False) != source_hashes['candidate']:
        failed = True
    write_json(output / 'source-link-diagnostics.json', {'before': source_links_before,
               'after': {name: link_counts(p) for name, p in [('baseline', baseline), ('candidate', candidate)]},
               'limit': 'Final integrity checks content/path sets and rejects symlinks; metadata-only nlink increases are diagnostic, not inode-immutability evidence.'})
    write_json(output / 'result.json', {'transport_passed': not failed, 'scored': False, 'accepted': False})
    write_json(output / 'manifest.json', tree(output, reject_hardlinks=False))
    return not failed

def validate_grading(data, require_protected_pass=True):
    if data.get('independent_grader') is not True or data.get('inspection_passed') is not True:
        raise ValueError('independent scoring and actual inspection required')
    scores = data.get('dimensions')
    if not isinstance(scores, list) or len(scores) != 5 or any(type(x) is not int or x not in (0, 1, 2) for x in scores):
        raise ValueError('five rubric dimensions required')
    failures = data.get('protected_failures')
    if not isinstance(failures, list) or any(not isinstance(x, str) for x in failures):
        raise ValueError('protected failure assessment required')
    if require_protected_pass and failures:
        raise ValueError('protected critical failure')
    return sum(scores)

def aggregate_scores(records, checks):
    """Apply frozen numeric gates to independent grades, never infer scores."""
    required_checks = {'protected_public_probes_passed', 'deterministic_regressions_passed',
                       'rendered_inspection_passed', 'frozen_boundary_review_passed',
                       'receipts_integrity_passed', 'budget_passed'}
    if set(checks) != required_checks or any(type(x) is not bool for x in checks.values()):
        raise ValueError('all independent nonnumeric gate receipts required')
    if len(records) != 36:
        raise ValueError('exactly six families times three paired repetitions required')
    indexed = {}
    for record in records:
        key = (record['family'], record['replicate'], record['arm'])
        if key in indexed or record['replicate'] not in (1, 2, 3) or record['arm'] not in ('baseline', 'candidate'):
            raise ValueError('duplicate or invalid paired grade')
        indexed[key] = (validate_grading(record, require_protected_pass=record['arm'] == 'candidate'), record['dimensions'])
    families = {key[0] for key in indexed}
    if len(families) != 6:
        raise ValueError('six distinct scenario families required')
    means = {}
    for family in sorted(families):
        means[family] = {}
        for arm in ('baseline', 'candidate'):
            keys = [(family, rep, arm) for rep in (1, 2, 3)]
            if any(key not in indexed for key in keys):
                raise ValueError('missing paired arm/replicate')
            means[family][arm] = sum(indexed[key][0] for key in keys) / 3
    baseline = sum(x['baseline'] for x in means.values()) / 6
    candidate = sum(x['candidate'] for x in means.values()) / 6
    improved = sum(x['candidate'] > x['baseline'] for x in means.values())
    candidate_total = sum(score for key, (score, _) in indexed.items() if key[2] == 'candidate')
    baseline_total = sum(score for key, (score, _) in indexed.items() if key[2] == 'baseline')
    numeric = (candidate_total >= 144 and all(x['candidate'] >= 7 for x in means.values())
               and all(all(v > 0 for v in dims) for key, (_, dims) in indexed.items() if key[2] == 'candidate')
               and candidate_total - baseline_total >= 18 and all(x['candidate'] >= x['baseline'] for x in means.values())
               and improved >= 5)
    return {'family_means': means, 'baseline_mean': baseline, 'candidate_mean': candidate,
            'paired_mean_gain': candidate - baseline, 'improved_families': improved,
            'numeric_gates_passed': numeric, 'accepted': numeric and all(checks.values())}

def main():
    parser = argparse.ArgumentParser()
    for name in ('baseline', 'candidate', 'scenario', 'output', 'model'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--seconds', type=float, default=600)
    parser.add_argument('--repetitions', type=int, default=3)
    args = parser.parse_args()
    data = json.loads(Path(args.scenario).read_text())
    return 0 if run(args.baseline, args.candidate, data, args.output, args.model, args.seconds, args.repetitions) else 1

if __name__ == '__main__':
    raise SystemExit(main())
