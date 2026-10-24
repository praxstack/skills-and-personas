#!/usr/bin/env python3
"""Assemble a NEW unaccepted local handoff; never modify inputs or old handoffs."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def package(source, media, historical, output, media_provenance):
    if output.exists(): raise ValueError('output must be a new directory')
    if not source.is_dir() or source.is_symlink(): raise ValueError('regular source directory required')
    for path in source.iterdir():
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError(f'source accepts regular files only: {path.name}')
    manifest = json.loads((source/'RELEASE-MANIFEST.json').read_text())
    if manifest.get('status') != 'unaccepted-candidate': raise ValueError('candidate source manifest required')
    names = [asset['name'] for asset in manifest['assets']]
    sidecars = {'RELEASE-MANIFEST.json', 'SHA256SUMS'}
    if len(set(names)) != len(names) or any(Path(name).name != name or name in sidecars for name in names):
        raise ValueError('source asset names must be unique basenames distinct from sidecars')
    if {path.name for path in source.iterdir()} != set(names) | sidecars:
        raise ValueError('source must contain exactly manifest assets and named sidecars')
    for asset in manifest['assets']:
        path = source/asset['name']
        if path.parent != source or digest(path) != asset['sha256']: raise ValueError('source asset mismatch')
    required = ['still.png', 'explorer.html', 'qa.html', 'cards.html', 'lesson.mp4', 'interactive-video.html']
    if any(not (media/name).is_file() for name in required): raise ValueError('six-format bundle incomplete')
    files = []
    for label, root in [('current-source', source), ('unaccepted-demo', media), ('historical-artifacts', historical)]:
        if not root.is_dir() or root.is_symlink(): raise ValueError('regular input directories required')
        for path in sorted(root.rglob('*')):
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ValueError(f'nonregular input: {path}')
            if path.is_file(): files.append((f'{label}/{path.relative_to(root)}', path))
    output.mkdir(parents=True)
    receipt = {'status': 'unaccepted-candidate', 'source_commit': manifest['source_commit'], 'media_provenance': media_provenance, 'historical_notice': 'Historical artifacts retain their original source revisions and are not current acceptance.', 'files': []}
    for name, path in files:
        receipt['files'].append({'name': name, 'bytes': path.stat().st_size, 'sha256': digest(path)})
    notice = ('UNACCEPTED CANDIDATE\nApproval and playback outcomes require evidence for the named source revision. Packaging alone does not establish release or installation eligibility.\nCurrent committed source: '+manifest['source_commit']+'\nMedia provenance: '+media_provenance+'\nHistorical artifacts retain original provenance, not current acceptance.\n').encode()
    # Two assets: current source+six-format demo, and complete historical-inclusive handoff.
    for archive_name, include_history in [('current-source-and-demo.zip', False), ('complete-dot-handoff-candidate.zip', True)]:
        path = output/archive_name
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            info = zipfile.ZipInfo('START-HERE.txt', (1980,1,1,0,0,0)); info.external_attr = 0o100644 << 16
            archive.writestr(info, notice)
            for name, original in files:
                if name.startswith('historical-artifacts/') and not include_history: continue
                info = zipfile.ZipInfo(name, (1980,1,1,0,0,0)); info.create_system = 3
                info.external_attr = (0o100755 if original.stat().st_mode & 0o111 else 0o100644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                with original.open('rb') as src, archive.open(info, 'w', force_zip64=True) as dest:
                    import shutil
                    shutil.copyfileobj(src, dest, 1024*1024)
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None: raise ValueError('CRC failure')
            expected = {f['name']: f['sha256'] for f in receipt['files'] if include_history or not f['name'].startswith('historical-artifacts/')}
            for name, sha in expected.items():
                h = hashlib.sha256()
                with archive.open(name) as src:
                    for chunk in iter(lambda: src.read(1024*1024), b''): h.update(chunk)
                if h.hexdigest() != sha: raise ValueError('input changed during packaging')
        receipt.setdefault('assets', []).append({'name': archive_name, 'sha256': digest(path), 'bytes': path.stat().st_size})
    (output/'HANDOFF-RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n')
    (output/'SHA256SUMS').write_text(''.join(f"{a['sha256']}  {a['name']}\n" for a in receipt['assets']))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'media', 'historical', 'output'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--media-provenance', required=True, help='Actual source revision/run ID and failure evidence; never infer from current HEAD')
    a = p.parse_args(); package(a.source, a.media, a.historical, a.output, a.media_provenance)
