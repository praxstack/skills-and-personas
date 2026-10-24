import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path.cwd()
SCRIPTS = ROOT / 'skills/teacher/skills/course/scripts'
FIXTURE = ROOT / 'skills/teacher/skills/explorable/assets/examples/seasons.lesson.js'
EVIDENCE = ROOT / 'docs/teach-resume-20261024/consent'
SCRATCH = ROOT / '.superpowers/sdd/RESUME-20261024/task-1-scratch'
records = []

def run(label, command, expected=0):
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    text = result.stdout + result.stderr
    (EVIDENCE / f'{label}.txt').write_text(''.join(line.rstrip() + '\n' for line in text.splitlines()))
    records.append({'label': label, 'command': command, 'exit_code': result.returncode,
                    'expected_exit_code': expected, 'output': f'{label}.txt', 'raw_output': text})
    assert result.returncode == expected, text
    print(label, result.returncode, text.strip().splitlines()[-1])
    return text

with tempfile.TemporaryDirectory(dir=SCRATCH, prefix='method-fixtures-') as tmp:
    temp = Path(tmp)
    for count in (1, 2):
        course = temp / f'course-{count}'
        course.mkdir()
        (course / 'seasons.lesson.js').write_bytes(FIXTURE.read_bytes())
        lessons = [{'id': f'seasons-{i}', 'title': f'Why seasons happen {i}',
                    'file': 'seasons.lesson.js', 'needs': [] if i == 1 else ['seasons-1'],
                    'minutes': 3, 'summary': 'Tilt changes the light.'} for i in range(1, count + 1)]
        (course / 'course.json').write_text(json.dumps({'id': f'seasons-{count}', 'title': 'Seasons', 'lessons': lessons}))
        if count == 2:
            # Video-offer/caption routing only: no media or narration is generated.
            (course / 'videos').mkdir()
            for lesson in lessons:
                (course / 'videos' / f"{lesson['id']}.vtt").write_text('WEBVTT\n\n00:00.000 --> 00:01.000\nSynthetic routing fixture\n')
            (temp / 'videos.json').write_text(json.dumps({f"seasons-2/{l['id']}.mp4": f"https://fixture.vercel-storage.com/{l['id']}.mp4" for l in lessons}))
        output = temp / f'built-{count}'
        run(f'build-{count}', ['python3', str(SCRIPTS / 'build_course.py'), str(course), '--out', str(output), '--trust-authored-code'])
        records.append({'label': f'html-{count}', 'sha256': hashlib.sha256((output / 'index.html').read_bytes()).hexdigest()})
        passed = run(f'v2-{count}', ['node', str(SCRIPTS / 'check_course_page_v2.mjs'), str(output / 'index.html')])
        assert '0 failed' in passed
        if count == 1:
            old = run('v1-historical', ['node', str(SCRIPTS / 'check_course_page.mjs'), str(output / 'index.html')], expected=1)
            assert [line.strip() for line in old.splitlines()] == ['FAIL status survives a reload', 'course page: 18 passed, 1 failed']
            # Recreate private fixture inputs before the second independent run.
            # Observed host files acquired a second link after direct browser checks;
            # retain the snapshot boundary instead of allowing linked input.
            for source in course.rglob('*'):
                if source.is_file():
                    contents = source.read_bytes()
                    source.unlink()
                    source.write_bytes(contents)
            print('manifest-before-runner', (course / 'course.json').stat(), 'uid', os.getuid(), flush=True)
            old_runner = run('v1-runner-historical', ['python3', str(SCRIPTS / 'test_course.py'), str(course), '--out', str(temp / 'runner-v1'), '--skip-qa', '--trust-authored-code', '--course-checker', 'v1'], expected=1)
            assert 'course page: 18 passed, 1 failed' in old_runner
            assert 'interactions 59/59' in old_runner
(EVIDENCE / 'fixture-receipt.json').write_text(json.dumps({'scope': 'first-party synthetic fixture; no learner state or media generation; temporary inputs removed', 'fixture_sha256': hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), 'records': records}, indent=2) + '\n')
