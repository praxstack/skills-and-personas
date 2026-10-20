"""Regression tests for live inventory behavior, independent of existing portfolio debt."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import portfolio_audit as audit


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for collection in ('skills', 'new-skills'):
            (self.root / collection).mkdir()

    def skill(self, collection, name, body=''):
        path = self.root / collection / name / 'SKILL.md'
        path.parent.mkdir()
        path.write_text(f'---\nname: {name}\ndescription: Use when testing portfolio diagnostics.\n---\n# Test\n{body}')
        return path

    def test_clean_and_broken_links(self):
        path = self.skill('skills', 'example')
        self.assertTrue(audit.audit(self.root)['summary']['passed'])
        path.write_text(path.read_text() + '\n[Missing](missing.md)\n')
        report = audit.audit(self.root)
        self.assertFalse(report['summary']['passed'])
        self.assertEqual(report['summary']['link_findings'], 1)

    def test_divergent_identity_preserved(self):
        first = self.skill('skills', 'example')
        second = self.skill('new-skills', 'example', 'Different guidance.')
        originals = [p.read_bytes() for p in (first, second)]
        report = audit.audit(self.root)
        self.assertEqual(report['summary']['duplicate_names'], 1)
        self.assertTrue(report['duplicates'][0]['entrypoint_content_differs'])
        self.assertEqual(originals, [p.read_bytes() for p in (first, second)])

    def test_invalid_frontmatter_and_missing_collection_are_errors(self):
        path = self.skill('skills', 'example')
        path.write_text('---\n- invalid\n---\n')
        (self.root / 'new-skills').rmdir()
        self.assertEqual(audit.audit(self.root)['summary']['errors'], 2)

    def test_check_exits_nonzero_but_reporting_does_not_claim_pass(self):
        self.skill('skills', 'example')
        self.skill('new-skills', 'example')
        for check, expected in (([], 0), (['--check'], 1)):
            out = io.StringIO()
            with patch('sys.argv', ['portfolio_audit.py', '--root', str(self.root), *check]), contextlib.redirect_stdout(out):
                self.assertEqual(audit.main(), expected)
            self.assertFalse(json.loads(out.getvalue())['summary']['passed'])

    def test_legacy_tools_use_checkout_relative_paths(self):
        for name in ('check_links', 'fix_lint_issues'):
            self.assertEqual(audit.load_helper(name).ROOT, audit.REPO / 'new-skills')


if __name__ == '__main__':
    unittest.main()
