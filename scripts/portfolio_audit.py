#!/usr/bin/env python3
"""Current, read-only top-level skill diagnostics. JSON on stdout; --check gates findings.

Requires PyYAML==6.0.3. Does not regenerate historical _audit reports.
Link findings reuse the existing heuristic checker, not a complete Markdown parser.
"""
import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import yaml

REPO = Path(__file__).resolve().parents[1]


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, REPO / 'new-skills/_audit' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit(root):
    lint = load_helper('lint')
    links = load_helper('check_links')
    entries, errors, lint_findings, link_findings = [], [], [], []
    for collection in ('skills', 'new-skills'):
        base = root / collection
        if not base.is_dir():
            errors.append({'path': collection, 'error': 'missing collection'})
            continue
        for path in sorted(base.glob('*/SKILL.md')):
            if path.parent.name.startswith(('.', '_')):
                continue
            relative = path.relative_to(root).as_posix()
            try:
                raw = path.read_text(encoding='utf-8')
                front, _ = lint.split_frontmatter(raw)
                data = yaml.safe_load(front) if front is not None else None
                if not isinstance(data, dict) or not isinstance(data.get('name'), str) or not data['name'].strip():
                    raise ValueError('missing or invalid frontmatter name')
                entry = {'path': relative, 'name': data['name'],
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'allowed_tools_declared': 'allowed-tools' in data}
                entries.append(entry)
                for severity, code, message in lint.lint_skill(path.parent):
                    lint_findings.append({'path': relative, 'severity': severity, 'code': code, 'message': message})
                targets = [path] + sorted((path.parent / 'references').rglob('*.md'))
                for target in targets:
                    for finding in links.scan_file(target, path.parent):
                        finding = dict(finding)
                        resolved = finding.get('resolved')
                        if resolved:
                            try:
                                finding['resolved'] = Path(resolved).relative_to(root).as_posix()
                            except ValueError:
                                finding['resolved'] = '<outside repository>'
                        link_findings.append({'path': target.relative_to(root).as_posix(), **finding})
            except (OSError, UnicodeError, ValueError, yaml.YAMLError, TypeError, AttributeError) as exc:
                errors.append({'path': relative, 'error': str(exc)})
    names = defaultdict(list)
    for entry in entries:
        names[entry['name']].append(entry)
    duplicates = [{'name': name, 'paths': [e['path'] for e in group],
                   'entrypoint_content_differs': len({e['sha256'] for e in group}) > 1}
                  for name, group in sorted(names.items()) if len(group) > 1]
    failures = sum(f['severity'] == 'FAIL' for f in lint_findings)
    return {'schema_version': 1, 'scope': 'skills/*/SKILL.md and new-skills/*/SKILL.md; links also scan references/**/*.md',
            'limitations': ['Nested skill identities and packaged archives are not inventoried.',
                             'Link results are heuristic and need triage; network URLs are not verified.',
                             'Identical entrypoint hashes do not establish identical skill directories.',
                             'allowed-tools metadata is not an enforced authorization boundary.'],
            'summary': {'entries': len(entries), 'unique_names': len(names), 'duplicate_names': len(duplicates),
                        'lint_failures': failures, 'link_findings': len(link_findings), 'errors': len(errors),
                        'allowed_tools_declarations': sum(e['allowed_tools_declared'] for e in entries),
                        'passed': bool(entries) and not (duplicates or failures or link_findings or errors)},
            'entries': entries, 'duplicates': duplicates, 'errors': errors,
            'lint_findings': lint_findings, 'link_findings': link_findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=REPO)
    parser.add_argument('--check', action='store_true', help='exit 1 when any current finding remains')
    args = parser.parse_args()
    report = audit(args.root.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    # Collection failure is always fatal, including report-only mode.
    return 1 if report['errors'] or not report['entries'] or (args.check and not report['summary']['passed']) else 0


if __name__ == '__main__':
    sys.exit(main())
