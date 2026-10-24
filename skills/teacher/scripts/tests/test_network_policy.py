#!/usr/bin/env python3
"""Behavioral checks for scoped setup/network opt-ins; no network or model setup."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import venv
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / 'skills'


def load(path):
    spec = importlib.util.spec_from_file_location('network_test_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NetworkPolicy(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {'TEACHER_ALLOW_NETWORK': '0'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def voices(self):
        paths = sorted(SKILLS.glob('*/scripts/voice.py'))
        self.assertEqual(len(paths), 11)
        for path in paths:
            deps = load(path.with_name('pydeps.py'))
            with mock.patch.dict(sys.modules, {'pydeps': deps}):
                yield path, load(path)

    def test_all_pydeps_deny_install_allow_installed_and_explicit_setup(self):
        paths = sorted(SKILLS.glob('*/scripts/pydeps.py'))
        self.assertEqual(len(paths), 11)
        for path in paths:
            with self.subTest(path=path):
                deps = load(path)
                with mock.patch.object(deps.subprocess, 'run', side_effect=AssertionError('network installer reached')) as run:
                    self.assertIs(deps.need('json'), __import__('json'))
                    with self.assertRaisesRegex(RuntimeError, 'TEACHER_ALLOW_NETWORK=1'):
                        deps.need('_teacher_nonexistent_dependency_')
                    with self.assertRaisesRegex(RuntimeError, 'TEACHER_ALLOW_NETWORK=1'):
                        deps._pip(sys.executable, 'example')
                    with mock.patch.object(deps, 'VENV', str(self.directory / 'absent')):
                        with self.assertRaisesRegex(RuntimeError, 'TEACHER_ALLOW_NETWORK=1'):
                            deps._make_venv()
                        self.assertFalse((self.directory / 'absent').exists())
                    run.assert_not_called()
                with mock.patch.dict(os.environ, {'TEACHER_ALLOW_NETWORK': '1'}), mock.patch.object(deps.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0)) as run:
                    self.assertIsNone(deps._pip(sys.executable, 'example'))
                    self.assertIn('install', run.call_args.args[0])

    def test_all_pydeps_reuse_real_private_venv_offline(self):
        paths = sorted(SKILLS.glob('*/scripts/pydeps.py'))
        self.assertEqual(len(paths), 11)
        private = self.directory / 'private'
        # Fixture setup only: stdlib venv, no ensurepip or package downloads.
        venv.EnvBuilder(with_pip=False).create(private)
        python = private / 'bin/python'
        probe = subprocess.run([str(python), '-c',
                                'import sysconfig; print(sysconfig.get_path("purelib"))'],
                               check=True, capture_output=True, text=True)
        package = Path(probe.stdout.strip()) / '_teacher_private_engine.py'
        package.write_text('VALUE = "private engine"\n')
        host = self.directory / 'host'
        host.mkdir()
        for name in ('numpy', 'soundfile'):
            (host / (name + '.py')).write_text('VALUE = "host fixture"\n')
        harness = r'''import json, os, pathlib, sys
sys.path.insert(0, os.environ['TEST_HELPERS'])
import pydeps

def prohibit_acquisition(event, args):
    if event in ('subprocess.Popen', 'os.system') or event.startswith('socket.'):
        raise AssertionError('offline acquisition reached: ' + event)
sys.addaudithook(prohibit_acquisition)
trace = pathlib.Path(os.environ['TEST_TRACE'])
with trace.open('a') as f:
    f.write(json.dumps({'prefix': sys.prefix, 'mark': os.environ.get(pydeps._MARK)}) + '\n')
if sys.argv[1] == 'engine_only':
    assert pydeps.need('numpy').VALUE == 'host fixture'
    assert pydeps.need('soundfile').VALUE == 'host fixture'
name = '_teacher_missing_everywhere' if sys.argv[1] == 'missing_everywhere' else '_teacher_private_engine'
try:
    module = pydeps.need(name)
except RuntimeError as exc:
    print(json.dumps({'error': str(exc), 'prefix': sys.prefix}))
    sys.exit(7)
print(json.dumps({'value': module.VALUE, 'file': module.__file__, 'prefix': sys.prefix}))
'''
        for path in paths:
            folder = self.directory / path.parent.parent.name
            folder.mkdir()
            shutil.copy2(path, folder / 'pydeps.py')
            script = folder / 'voice.py'
            script.write_text(harness)
            outside = folder / 'outside'
            outside.mkdir()
            nonsibling = outside / 'voice.py'
            nonsibling.write_text(harness)
            cases = ('missing_host', 'engine_only', 'absent_venv',
                     'missing_everywhere', 'already_switched', 'nonsibling')
            for case in cases:
                with self.subTest(path=path, case=case):
                    trace = folder / (case + '.jsonl')
                    absent = folder / 'absent'
                    env = dict(os.environ, TEACHER_ALLOW_NETWORK='0',
                               VIDEO_SKILLS_VENV=str(absent if case == 'absent_venv' else private),
                               TEST_HELPERS=str(folder), TEST_TRACE=str(trace),
                               PYTHONPATH=str(host), PYTHONNOUSERSITE='1')
                    env.pop('VIDEO_SKILLS_PYDEPS_SWITCHED', None)
                    if case == 'already_switched':
                        env['VIDEO_SKILLS_PYDEPS_SWITCHED'] = '1'
                    result = subprocess.run([sys.executable,
                                             str(nonsibling if case == 'nonsibling' else script), case],
                                            env=env, capture_output=True, text=True, timeout=15)
                    runs = [json.loads(line) for line in trace.read_text().splitlines()]
                    success = case in ('missing_host', 'engine_only')
                    self.assertEqual(result.returncode, 0 if success else 7, result.stderr)
                    output = json.loads(result.stdout)
                    self.assertEqual(len(runs), 2 if success or case == 'missing_everywhere' else 1)
                    if len(runs) == 2:
                        self.assertIsNone(runs[0]['mark'])
                        self.assertEqual(runs[1]['mark'], '1')
                        self.assertEqual(Path(runs[1]['prefix']).resolve(), private.resolve())
                    if success:
                        self.assertEqual(output['value'], 'private engine')
                        self.assertEqual(Path(output['file']), package)
                    else:
                        self.assertIn('TEACHER_ALLOW_NETWORK=1', output['error'])
                    self.assertFalse(absent.exists(), 'offline call created an environment')

    def test_all_voice_downloads_and_edge_are_denied_before_transport(self):
        for path, voice in self.voices():
            with self.subTest(path=path), mock.patch.object(voice.urllib.request, 'urlopen', side_effect=AssertionError('network reached')) as request, mock.patch.object(voice.subprocess, 'run', side_effect=AssertionError('curl reached')) as run:
                with self.assertRaisesRegex(RuntimeError, 'TEACHER_ALLOW_NETWORK=1'):
                    voice.download('https://example.invalid/model', str(self.directory / 'model'))
                with self.assertRaisesRegex(RuntimeError, 'TEACHER_ALLOW_NETWORK=1'):
                    voice.EdgeTTS('en-US-AriaNeural', 1)
                edge = object.__new__(voice.EdgeTTS)
                with self.assertRaisesRegex(RuntimeError, 'TEACHER_ALLOW_NETWORK=1'):
                    edge.say('private words')
                request.assert_not_called()
                run.assert_not_called()

    def test_all_voice_auto_uses_offline_fallback(self):
        for path, voice in self.voices():
            with self.subTest(path=path), mock.patch.object(voice, 'Kokoro', side_effect=RuntimeError('missing cache')), mock.patch.dict(voice.ENGINES, {'edge-tts': mock.Mock(side_effect=AssertionError('online fallback')), 'piper': mock.Mock(return_value=types.SimpleNamespace())}), contextlib.redirect_stdout(io.StringIO()):
                engine, failures = voice.pick_engine('auto', None, 1, None, False)
                self.assertEqual(engine.voice_name, voice.PIPER_VOICE)
                self.assertEqual(len(failures), 1)
                voice.ENGINES['edge-tts'].assert_not_called()

    def test_verified_kokoro_cache_and_opted_download(self):
        for path, voice in self.voices():
            with self.subTest(path=path):
                fake = types.SimpleNamespace(get_voices=lambda: ['af_heart'])
                module = types.SimpleNamespace(Kokoro=mock.Mock(return_value=fake))
                assets = {'kokoro-v1.0.onnx': 'https://example.invalid/model', 'voices-v1.0.bin': 'https://example.invalid/voice'}
                content = b'fixture model bytes'
                hashes = {name: hashlib.sha256(content).hexdigest() for name in assets}
                for name in assets:
                    (self.directory / name).write_bytes(content)
                with mock.patch.dict(sys.modules, {'kokoro_onnx': module}), mock.patch.object(voice, 'need'), mock.patch.object(voice, 'KOKORO_FILES', assets), mock.patch.object(voice, 'KOKORO_SHA256', hashes), mock.patch.object(voice.urllib.request, 'urlopen', side_effect=AssertionError('cache requested network')):
                    self.assertIs(voice.Kokoro('af_heart', 1, str(self.directory)).k, fake)
                with mock.patch.dict(os.environ, {'TEACHER_ALLOW_NETWORK': '1'}), mock.patch.object(voice.urllib.request, 'urlopen', return_value=io.BytesIO(content)) as request:
                    voice.download('https://example.invalid/model', str(self.directory / 'download'), sha256=hashes['kokoro-v1.0.onnx'])
                    request.assert_called_once()
                    self.assertEqual((self.directory / 'download').read_bytes(), content)

    def test_all_piper_cached_assets_and_explicit_online_edge(self):
        for path, voice in self.voices():
            with self.subTest(path=path):
                content = b'cached piper fixture'
                cache = self.directory / '.cache' / 'piper'
                cache.mkdir(parents=True, exist_ok=True)
                for ext in ('.onnx', '.onnx.json'):
                    (cache / (voice.PIPER_VOICE + ext)).write_bytes(content)
                piper = types.SimpleNamespace(PiperVoice=types.SimpleNamespace(load=mock.Mock(return_value='local piper')))
                hashes = {ext: hashlib.md5(content).hexdigest() for ext in ('.onnx', '.onnx.json')}
                with mock.patch.dict(os.environ, {'HOME': str(self.directory)}), mock.patch.dict(sys.modules, {'piper': piper}), mock.patch.object(voice, 'need'), mock.patch.object(voice, 'PIPER_MD5', hashes), mock.patch.object(voice.urllib.request, 'urlopen', side_effect=AssertionError('cached piper requested network')):
                    self.assertEqual(voice.Piper(voice.PIPER_VOICE, 1).v, 'local piper')
                edge = types.SimpleNamespace(Communicate=mock.Mock(return_value=types.SimpleNamespace(save=mock.AsyncMock())))
                with mock.patch.dict(os.environ, {'TEACHER_ALLOW_NETWORK': '1'}), mock.patch.dict(sys.modules, {'edge_tts': edge}), mock.patch.object(voice, 'need'), mock.patch.object(voice, 'decode', return_value='audio'):
                    engine = voice.EdgeTTS('en-US-AriaNeural', 1)
                    self.assertEqual(engine.say('opted-in text'), 'audio')
                    self.assertEqual(edge.Communicate.call_args.args[0], 'opted-in text')

    def narrate(self):
        with mock.patch.dict(sys.modules, {'numpy': mock.MagicMock(), 'soundfile': mock.MagicMock()}):
            return load(SKILLS / 'explorable/scripts/narrate.py')

    def test_narrate_model_missing_denied_cached_accepted_and_setup_allowed(self):
        narrate = self.narrate()
        name = 'kokoro-v1.0.onnx'
        content = b'fixture'
        fake = types.SimpleNamespace(Kokoro=mock.Mock(return_value='local model'))
        with mock.patch.dict(sys.modules, {'kokoro_onnx': fake}), mock.patch.object(narrate, 'KOKORO_DIR', self.directory), mock.patch.object(narrate, 'KOKORO_FILES', {name: ('https://example.invalid/model', hashlib.sha256(content).hexdigest())}), mock.patch.object(narrate.urllib.request, 'urlretrieve', side_effect=AssertionError('network reached')) as request:
            with self.assertRaisesRegex(RuntimeError, 'TEACHER_ALLOW_NETWORK=1'):
                narrate.kokoro()
            request.assert_not_called()
            (self.directory / name).write_bytes(content)
            self.assertEqual(narrate.kokoro(), 'local model')
            request.assert_not_called()
            (self.directory / name).unlink()
            request.side_effect = lambda url, target: target.write_bytes(content)
            with mock.patch.dict(os.environ, {'TEACHER_ALLOW_NETWORK': '1'}):
                self.assertEqual(narrate.kokoro(), 'local model')
                request.assert_called_once()

    def test_chatterbox_default_forces_hf_offline_even_if_preimported(self):
        narrate = self.narrate()
        constants = types.SimpleNamespace(HF_HUB_OFFLINE=False)
        hub = types.SimpleNamespace(_is_offline_mode=False)
        def cached(**kwargs):
            self.assertEqual(os.environ['HF_HUB_OFFLINE'], '1')
            self.assertTrue(constants.HF_HUB_OFFLINE)
            self.assertTrue(hub._is_offline_mode)
            return 'cached chatterbox'
        modules = {'huggingface_hub': types.SimpleNamespace(constants=constants),
                   'transformers.utils.hub': hub,
                   'torch': types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False)),
                   'chatterbox.tts': types.SimpleNamespace(ChatterboxTTS=types.SimpleNamespace(from_pretrained=cached))}
        with mock.patch.dict(sys.modules, modules), mock.patch.dict(os.environ, {'HF_HUB_OFFLINE': '0', 'TRANSFORMERS_OFFLINE': '0'}):
            self.assertEqual(narrate.chatterbox(), 'cached chatterbox')
            modules['chatterbox.tts'].ChatterboxTTS.from_pretrained = mock.Mock(side_effect=FileNotFoundError('cache miss'))
            with self.assertRaisesRegex(RuntimeError, 'TEACHER_ALLOW_NETWORK=1'):
                narrate.chatterbox()

    def test_all_edge_swap_scripts_refuse_before_import_or_artifact_access(self):
        paths = sorted(SKILLS.glob('*/scripts/edge_voice_swap.py'))
        self.assertEqual(len(paths), 11)
        for path in paths:
            with self.subTest(path=path), mock.patch.dict(sys.modules, {'edge_tts': None}):
                with self.assertRaisesRegex(SystemExit, 'TEACHER_ALLOW_NETWORK=1'):
                    runpy.run_path(str(path), run_name='__main__')

    def test_whisper_loader_receives_cache_only_default_and_explicit_opt_in(self):
        speech = load(SKILLS / 'visual-qa/scripts/check_speech.py')
        vtt = self.directory / 'clip.vtt'
        vtt.write_text('WEBVTT\n\n00:00.000 --> 00:02.000\nLearning concepts\n')
        constructor = mock.Mock(return_value=types.SimpleNamespace(transcribe=lambda *a, **k: ([], None)))
        for allowed in ('0', '1'):
            with self.subTest(allowed=allowed), mock.patch.dict(os.environ, {'TEACHER_ALLOW_NETWORK': allowed}), mock.patch.dict(sys.modules, {'numpy': mock.MagicMock(), 'faster_whisper': types.SimpleNamespace(WhisperModel=constructor)}), mock.patch.object(speech.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0, stdout=b'audio', stderr=b'')), mock.patch.object(sys, 'argv', ['check_speech.py', str(self.directory / 'clip.mp4')]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(speech.main(), 1)  # no words heard, not a fake pass
                self.assertEqual(constructor.call_args.kwargs['local_files_only'], allowed != '1')

    @unittest.skipUnless(shutil.which('node'), 'Node required for Remotion acquisition guards')
    def test_remotion_missing_setup_denied_cached_browser_and_online_opt_in(self):
        import json
        source = self.directory / 'source'
        (source / 'src').mkdir(parents=True)
        (source / 'package.json').write_text('{}')
        (source / 'src/timing.json').write_text(json.dumps({'total': 2, 'fps': 30, 'lines': []}))
        bindir = self.directory / 'bin'
        bindir.mkdir()
        log = self.directory / 'commands.jsonl'
        shim = '#!' + sys.executable + '\n' + r"""
import json, os, pathlib, sys
with open(os.environ['NETWORK_TEST_COMMANDS'], 'a') as f:
    f.write(json.dumps({'tool': pathlib.Path(sys.argv[0]).name, 'args': sys.argv[1:], 'offline': os.environ.get('npm_config_offline')}) + '\n')
if pathlib.Path(sys.argv[0]).name == 'npm':
    pathlib.Path('node_modules/remotion').mkdir(parents=True, exist_ok=True)
elif '--out-dir' in sys.argv:
    pathlib.Path(sys.argv[sys.argv.index('--out-dir') + 1]).mkdir(parents=True, exist_ok=True)
"""
        for command in ('npm', 'npx'):
            executable = bindir / command
            executable.write_text(shim)
            executable.chmod(0o755)
        env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ['PATH'], NETWORK_TEST_COMMANDS=str(log), TEACHER_ALLOW_NETWORK='0')
        env.pop('REMOTION_BROWSER_EXECUTABLE', None)
        command = [shutil.which('node'), str(SKILLS / 'remotion-video/scripts/render_remotion.mjs'), '--project', str(self.directory), '--stills', '1']
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing npm dependencies', result.stderr)
        self.assertFalse(log.exists(), 'missing dependencies invoked npm without opt-in')
        (source / 'node_modules/remotion').mkdir(parents=True)
        if not Path('/opt/pw-browsers').exists():
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('TEACHER_ALLOW_NETWORK=1', result.stderr)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertFalse(any('still' in call['args'] for call in calls), 'browser acquisition reached CLI without opt-in')
        cached = source / 'node_modules/.remotion/chrome-headless-shell/test/chrome-headless-shell'
        cached.parent.mkdir(parents=True)
        cached.write_text('#!/bin/sh\nexit 0\n')
        cached.chmod(0o755)
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        stills = [call for call in calls if 'still' in call['args']]
        self.assertTrue(stills)
        self.assertEqual(stills[-1]['offline'], 'true')
        self.assertTrue(any(arg.startswith('--browser-executable=') for arg in stills[-1]['args']))
        shutil.rmtree(source / 'node_modules')
        env['TEACHER_ALLOW_NETWORK'] = '1'
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertTrue(any(call['tool'] == 'npm' for call in calls))
        self.assertIsNone(calls[-1]['offline'])

    @unittest.skipUnless(shutil.which('node'), 'Node required for the learner UI control')
    def test_pyodide_ui_does_not_start_worker_without_consent(self):
        script = r'''
const { createCodePanel } = await import(process.argv[1]);
const elements=[];
function h(tag, attrs={}, ...children) {
 const e={tag, ...attrs, dataset:{lang:attrs['data-lang']}, children:children.flat(), events:{}, checked:false,
 append(...v){this.children.push(...v)}, replaceChildren(...v){this.children=v},
 setAttribute(k,v){this[k]=v}, querySelectorAll(t){return this.children.filter(e=>e.tag===t)},
 querySelector(){return null}, addEventListener(k,f){this.events[k]=f}, focus(){this.focused=true}};
 elements.push(e); return e;
}
let starts=0;
globalThis.Worker=class {constructor(){starts++;throw Error('network denied by test');}};
globalThis.localStorage={getItem(){return null}};
createCodePanel({python:'print(1)'},{h});
const run=elements.find(e=>e.text==='Run');
const consent=elements.find(e=>e.type==='checkbox');
await run.events.click();
if(starts!==0 || !consent.focused) throw Error('runtime started without consent');
consent.checked=true;
await run.events.click();
if(starts!==1) throw Error('explicit consent did not reach runtime loader');
consent.checked=false;
await run.events.click();
if(starts!==1) throw Error('revoked consent ignored');
'''
        path = SKILLS / 'explorable/assets/engine/code.js'
        result = subprocess.run(['node', '--input-type=module', '-e', script, path.as_uri()], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
