import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
IMAGE = os.environ.get("TEACHER_SANDBOX_IMAGE")
CONTEXT = os.environ.get("TEACHER_SANDBOX_CONTEXT")


@unittest.skipUnless(IMAGE, "set immutable TEACHER_SANDBOX_IMAGE to run isolation tests")
class SandboxCodeTests(unittest.TestCase):
    def run_lesson(self, js, extra=()):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lesson.js"
            path.write_text(js)
            command = [sys.executable, str(HERE / "sandbox_code.py"), str(path), "--image", IMAGE]
            if CONTEXT:
                command += ["--docker-context", CONTEXT]
            return subprocess.run([*command, *extra], text=True, capture_output=True, timeout=110)

    def lesson(self, python):
        return "window.LESSON = {title:'sandbox', code:{python:" + json.dumps(python) + ", cases:[{}], expect:()=> 'ok'}};"

    def test_legitimate_python_and_cpp_match_model(self):
        js = "window.LESSON = {title:'control',code:{python:'print(7)',cpp:'#include <iostream>\\nint main(){std::cout<<7;}',cases:[{}],expect:()=> '7'}};"
        result = self.run_lesson(js)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("2 runs match", result.stdout)

    def test_host_files_environment_and_network_are_unavailable(self):
        payload = """import os, socket
assert 'TEACHER_HOST_SECRET' not in os.environ
try:
    open('/Users/prax/.ssh/id_ed25519').read()
    raise AssertionError('host readable')
except FileNotFoundError:
    pass
try:
    open('/input/source-0.js', 'w').write('changed')
    raise AssertionError('input writable')
except OSError:
    pass
try:
    socket.create_connection(('8.8.8.8',443), timeout=1)
    raise AssertionError('network available')
except OSError:
    pass
print('ok')
"""
        os.environ['TEACHER_HOST_SECRET'] = 'not-a-credential-test-sentinel'
        try:
            result = self.run_lesson(self.lesson(payload))
        finally:
            os.environ.pop('TEACHER_HOST_SECRET', None)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_infinite_authored_js_is_terminated(self):
        result = self.run_lesson("while(true) {}", ["--timeout", "12"])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(result.returncode, 125, result.stderr)

    def test_memory_exhaustion_fails(self):
        result = self.run_lesson(self.lesson("x = bytearray(1024*1024*1024)\nprint('ok')"))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(result.returncode, 125, result.stderr)

    def test_output_flood_fails(self):
        result = self.run_lesson("while(true) console.log('x'.repeat(65536));")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(result.returncode, 125, result.stderr)
        self.assertLess(len(result.stdout), 2 * 1024 * 1024)

    def test_outer_deadline_stops_model_hang(self):
        js = "window.LESSON={title:'hang',code:{python:'print(1)',cases:[{}],expect(){while(true){}}}};"
        result = self.run_lesson(js, ["--timeout", "3"])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("wall-clock budget", result.stderr)

    def test_process_limit_prevents_fork_exhaustion(self):
        payload = """import subprocess
from pathlib import Path
limits = [Path('/sys/fs/cgroup/pids.max'), Path('/sys/fs/cgroup/pids/pids.max')]
assert any(p.exists() and p.read_text().strip() == '32' for p in limits), 'container process cap missing'
children=[]
try:
    for _ in range(100):
        children.append(subprocess.Popen(['sleep','20']))
except OSError:
    print('ok')
finally:
    for child in children: child.terminate()
    for child in children: child.wait()
"""
        result = self.run_lesson(self.lesson(payload))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_image_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lesson.js"
            path.write_text("throw new Error('must not run')")
            command = [sys.executable, str(HERE / "sandbox_code.py"), str(path), "--image", "sha256:" + "0"*64]
            if CONTEXT:
                command += ["--docker-context", CONTEXT]
            result = subprocess.run(command, text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 2)
            self.assertIn("no authored code ran", result.stderr)


if __name__ == "__main__":
    unittest.main()
