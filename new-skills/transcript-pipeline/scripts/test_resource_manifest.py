"""Real filesystem attacks against session manifest reads; no network needed."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import resource_enrichment as enrichment
import safe_resource_manifest as reader


class ManifestReads(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path.home())
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.session = self.root / 'session'
        self.pipeline = self.session / '.pipeline'
        self.pipeline.mkdir(parents=True)
        self.manifest = self.pipeline / 'resource_manifest.json'
        self.valid = b'{"resources":[{"name":"inside","url":"https://example.com"}]}'
        self.manifest.write_bytes(self.valid)
        self.outside = self.root / 'outside'
        self.outside.mkdir()
        (self.outside / 'resource_manifest.json').write_text('{"resources":[{"name":"outside-marker","url":"https://example.com"}]}')

    def rejected(self):
        with self.assertRaises((OSError, ValueError)):
            enrichment.parse_manifest(self.session)
        with mock.patch.object(enrichment, '_new_session', side_effect=AssertionError('network session must not start')):
            with self.assertRaises((OSError, ValueError)):
                enrichment.enrich_session(self.session, None, None, None, None, True)
        self.assertFalse((self.session / '.resources').exists())

    def test_valid_missing_and_bounds(self):
        self.assertEqual(enrichment.parse_manifest(self.session)[0].name, 'inside')
        self.manifest.unlink()
        self.assertEqual(enrichment.parse_manifest(self.session), [])
        self.pipeline.rmdir()
        self.assertEqual(enrichment.parse_manifest(self.session), [])
        self.pipeline.mkdir()
        self.manifest.write_bytes(b'x' * (reader.LIMIT + 1))
        with self.assertRaisesRegex(ValueError, '1 MiB'):
            enrichment.parse_manifest(self.session)
        self.manifest.write_text(json.dumps({'resources': [{}] * 101}))
        with self.assertRaisesRegex(ValueError, '100 entries'):
            enrichment.parse_manifest(self.session)

    def test_pipeline_symlink(self):
        self.manifest.unlink(); self.pipeline.rmdir()
        self.pipeline.symlink_to(self.outside, target_is_directory=True)
        self.rejected()

    def test_leaf_symlink_and_dangling_symlink(self):
        self.manifest.unlink()
        for target in (self.outside / 'resource_manifest.json', self.outside / 'missing'):
            self.manifest.symlink_to(target)
            self.rejected()
            self.manifest.unlink()

    def test_hardlink_and_nonregular(self):
        self.manifest.unlink()
        os.link(self.outside / 'resource_manifest.json', self.manifest)
        self.rejected()
        self.manifest.unlink()
        os.mkfifo(self.manifest)
        self.rejected()

    def test_session_ancestor_symlink(self):
        link = self.root / 'linked-session'
        link.symlink_to(self.session, target_is_directory=True)
        with self.assertRaises(OSError): enrichment.parse_manifest(link)

    def test_detect_leaf_and_directory_swaps_and_in_place_write(self):
        real_read = os.read
        for attack in ('leaf', 'directory', 'in-place'):
            with self.subTest(attack=attack):
                attacked = False
                def changed(fd, count):
                    nonlocal attacked
                    data = real_read(fd, count)
                    if not attacked:
                        attacked = True
                        if attack == 'leaf':
                            self.manifest.rename(self.pipeline / 'moved')
                            self.manifest.write_bytes(self.valid)
                        elif attack == 'directory':
                            self.pipeline.rename(self.session / 'moved-pipeline')
                            self.pipeline.mkdir()
                            self.manifest.write_bytes(self.valid)
                        else:
                            self.manifest.write_bytes(self.valid + b' ')
                    return data
                with mock.patch.object(reader.os, 'read', side_effect=changed):
                    with self.assertRaisesRegex(ValueError, 'changed during read'):
                        enrichment.parse_manifest(self.session)
                if attack == 'directory':
                    import shutil
                    shutil.rmtree(self.session / 'moved-pipeline')
                self.manifest.write_bytes(self.valid)

    def test_unsupported_platform_fails_closed(self):
        with mock.patch.object(reader.os, 'supports_dir_fd', set()):
            with self.assertRaisesRegex(RuntimeError, 'no-follow descriptor support'):
                enrichment.parse_manifest(self.session)


if __name__ == '__main__': unittest.main()
