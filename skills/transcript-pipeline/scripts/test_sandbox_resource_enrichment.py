"""Synthetic boundary tests. Docker controls require explicit image/context env vars."""
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest import mock
import sandbox_resource_enrichment as sandbox


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path.home())
        self.root = Path(self.tmp.name)
        self.session = self.root / 'session'
        (self.session / '.pipeline').mkdir(parents=True)
        (self.session / '.pipeline/resource_manifest.json').write_text('{"resources": []}')
    def tearDown(self):
        self.tmp.cleanup()
    def archive(self, items):
        path = self.root / 'out.tar'
        with tarfile.open(path, 'w', format=tarfile.USTAR_FORMAT) as out:
            for name, kind, size in items:
                info = tarfile.TarInfo(name)
                info.type = kind
                info.size = size
                if kind == tarfile.SYMTYPE:
                    info.linkname = '/etc/passwd'
                out.addfile(info, io.BytesIO(b'x' * size))
        return path
    def test_image_timeout_rejected_before_docker(self):
        for image, timeout in [('latest', 1), ('sha256:'+'a'*64, 601), ('sha256:'+'a'*64, float('nan'))]:
            with self.assertRaises(ValueError):
                sandbox.execute(self.session, self.root/'result', image, timeout=timeout)
    def test_input_no_follow_and_hardlinks(self):
        p = self.root/'secret'; p.write_text('hello')
        for target in [self.root/'link', self.root/'hard']:
            if target.name == 'link': target.symlink_to(p)
            else: os.link(p, target)
            with self.assertRaises((OSError, ValueError)):
                sandbox.read_bound_file(target, 32)
        q = self.root/'dirlink'; q.symlink_to(self.session, target_is_directory=True)
        with self.assertRaises(OSError): sandbox.read_bound_file(q/'.pipeline/resource_manifest.json', 100)
    def test_manifest_bounds_and_missing(self):
        manifest = self.session/'.pipeline/resource_manifest.json'
        for data in ['{}', '{"resources":'+json.dumps([{}]*101)+'}', 'x'*1048577]:
            manifest.write_text(data)
            with self.assertRaises(ValueError): sandbox.snapshot(self.session, self.root/'stage')
        manifest.unlink()
        with self.assertRaises(FileNotFoundError): sandbox.snapshot(self.session, self.root/'stage')
    def test_snapshot_scope_and_permissions(self):
        (self.session/'private-media').write_text('must not enter')
        stage = self.root/'stage'; stage.mkdir()
        sandbox.snapshot(self.session, stage)
        self.assertEqual([x.name for x in (stage/'input/session').iterdir()], ['.pipeline'])
        for p in stage.rglob('*'):
            self.assertEqual(p.stat().st_mode & 0o077, 0)
    def test_credential_validation(self):
        p = self.root/'credential'
        for kind, data in [('cookies', {}), ('cookies', [{'name':'a','value':'secret','domain':'.canva.com'}]),
                           ('notion', {'token_v2':'a'}), ('canva', {'cookies':[], 'origins':[{'origin':'http://www.canva.com','localStorage':[]}]}),
                           ('canva', {'cookies':[{'name':'a','value':'x','domain':'www.canva.com','secure':False}],'origins':[]})]:
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'invalid explicit credential'):
                sandbox.credential_data(p, kind)
        p.write_text(json.dumps({'token_v2':'synthetic-token', 'active_user':'synthetic-user'}))
        self.assertIn(b'synthetic-token', sandbox.credential_data(p, 'notion'))
        p.write_bytes(b'x'*65537)
        with self.assertRaises(ValueError): sandbox.credential_data(p, 'notion')
    def test_exact_create_flags_and_no_ambient_secrets(self):
        command = sandbox.container_command(['docker','--context','test'], 'owned', 'sha256:'+'a'*64, self.root, 10)
        for flag in ['--pull=never','--read-only','--cap-drop=ALL','--pids-limit=128','--memory=1g','--memory-swap=1g','--cpus=1','--network=bridge','--log-driver=none']:
            self.assertIn(flag, command)
        mounts = [command[i+1] for i,v in enumerate(command) if v == '--mount']
        self.assertEqual(len(mounts), 3)
        self.assertTrue(all(x.endswith(',readonly') for x in mounts))
        self.assertNotIn(str(Path.home())+',', str(command))
        self.assertNotIn('TOKEN', ' '.join(command))
    def test_unsafe_archives(self):
        for items in [[('../bad',tarfile.REGTYPE,1)], [('/bad',tarfile.REGTYPE,1)], [('link',tarfile.SYMTYPE,0)],
                      [('a',tarfile.REGTYPE,1),('a',tarfile.REGTYPE,1)], [('a',tarfile.REGTYPE,1),('a/b',tarfile.REGTYPE,1)],
                      [('fifo',tarfile.FIFOTYPE,0)], [('a/./b',tarfile.REGTYPE,1)]]:
            with self.subTest(items=items), self.assertRaises(ValueError):
                sandbox.publish_archive(self.archive(items), self.root/'result')
            self.assertFalse((self.root/'result').exists())
    def test_safe_publish_private_and_new_only(self):
        archive = self.archive([('a',tarfile.DIRTYPE,0),('a/result.json',tarfile.REGTYPE,3)])
        dest = self.root/'result'; sandbox.publish_archive(archive,dest)
        self.assertEqual((dest/'a/result.json').read_bytes(),b'xxx')
        self.assertEqual((dest/'a/result.json').stat().st_mode&0o777,0o600)
        with self.assertRaises(FileExistsError): sandbox.publish_archive(archive,dest)
        self.assertEqual((dest/'a/result.json').read_bytes(),b'xxx')
    def test_archive_count_byte_limits(self):
        archive=self.archive([('a',tarfile.REGTYPE,10)])
        with mock.patch.object(sandbox,'OUTPUT_LIMIT',9), self.assertRaises(ValueError): sandbox.publish_archive(archive,self.root/'result')
        with mock.patch.object(sandbox,'FILE_LIMIT',0), self.assertRaises(ValueError): sandbox.publish_archive(archive,self.root/'result')
    def test_capture_log_limit_is_secret_free(self):
        with mock.patch.object(sandbox,'LOG_LIMIT',10), self.assertRaises(RuntimeError):
            sandbox.capture([sys.executable,'-c','import sys;sys.stderr.write("synthetic-secret"*100)'],self.root/'capture',5)
    def test_capture_archive_limit(self):
        with mock.patch.object(sandbox,'ARCHIVE_LIMIT',10), self.assertRaises(RuntimeError):
            sandbox.capture([sys.executable,'-c','print("x"*100)'],self.root/'capture',5)
    def test_signal_handlers_restore_and_cleanup_state(self):
        previous=signal.getsignal(signal.SIGTERM)
        with self.assertRaises(sandbox.SandboxCancelled):
            with sandbox.cancellation_handlers(): os.kill(os.getpid(),signal.SIGTERM)
        self.assertEqual(signal.getsignal(signal.SIGTERM),previous)
    def test_lifecycle_failure_removes_owned_container(self):
        calls=[]
        def run(command, **kwargs):
            calls.append(command)
            if 'create' in command: return subprocess.CompletedProcess(command,1,b'',b'private')
            return subprocess.CompletedProcess(command,0,b'',b'')
        with mock.patch.object(sandbox.subprocess,'run',side_effect=run), mock.patch.object(sandbox.shutil,'which',return_value='/bin/docker'):
            with self.assertRaises(RuntimeError): sandbox.execute(self.session,self.root/'result','sha256:'+'a'*64)
        self.assertTrue(any('rm' in c and '--force' in c for c in calls))
        self.assertTrue(any('ps' in c for c in calls))
        self.assertFalse((self.root/'result').exists())
    def test_runtime_image_missing_no_fallback(self):
        with mock.patch.object(sandbox.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'',b'')), mock.patch.object(sandbox.shutil,'which',return_value='/bin/docker'):
            with self.assertRaisesRegex(RuntimeError,'image unavailable'):
                sandbox.execute(self.session,self.root/'result','sha256:'+'a'*64)
        self.assertFalse((self.root/'result').exists())

    def test_physical_pax_header_rejected(self):
        archive=self.root/'pax.tar'
        with tarfile.open(archive,'w',format=tarfile.PAX_FORMAT) as out:
            info=tarfile.TarInfo('a');info.pax_headers={'comment':'test'}
            out.addfile(info,io.BytesIO())
        with self.assertRaises(ValueError):sandbox.publish_archive(archive,self.root/'result')
    def test_descriptor_snapshot_survives_path_substitution(self):
        target=self.root/'input';target.write_bytes(b'original')
        real_open=os.open
        def swapped(path,*args,**kwargs):
            fd=real_open(path,*args,**kwargs)
            if path=='input':
                target.rename(self.root/'moved')
                target.write_bytes(b'replacement')
            return fd
        with mock.patch.object(sandbox.os,'open',side_effect=swapped):
            self.assertEqual(sandbox.read_bound_file(target,100),b'original')
    def test_all_post_create_failures_cleanup(self):
        for failure in ('capture','inspect','publish'):
            calls=[]
            def run(command,**kwargs):
                calls.append(command)
                if 'inspect' in command and 'image' not in command:
                    return subprocess.CompletedProcess(command,1 if failure=='inspect' else 0,b'{"Running":false,"ExitCode":0,"OOMKilled":false}',b'')
                return subprocess.CompletedProcess(command,0,b'',b'')
            def capture(*args):
                if failure=='capture':raise TimeoutError()
                return 0
            with mock.patch.object(sandbox.subprocess,'run',side_effect=run), mock.patch.object(sandbox,'capture',side_effect=capture), mock.patch.object(sandbox,'publish_archive',side_effect=OSError('synthetic publish failure')),mock.patch.object(sandbox.shutil,'which',return_value='docker'):
                with self.assertRaises((RuntimeError,TimeoutError,OSError)):
                    sandbox.execute(self.session,self.root/'result','sha256:'+'a'*64)
            self.assertTrue(any('rm' in c for c in calls),failure)
            self.assertTrue(any('ps' in c for c in calls),failure)
    def test_cleanup_verification_failure_is_explicit(self):
        def run(command,**kwargs):
            if 'image' in command:return subprocess.CompletedProcess(command,0,b'',b'')
            if 'ps' in command:return subprocess.CompletedProcess(command,0,b'owned-id',b'')
            return subprocess.CompletedProcess(command,1,b'',b'')
        with mock.patch.object(sandbox.subprocess,'run',side_effect=run),mock.patch.object(sandbox.shutil,'which',return_value='docker'):
            with self.assertRaisesRegex(RuntimeError,'could not verify owned sandbox removal'):
                sandbox.execute(self.session,self.root/'result','sha256:'+'a'*64)


@unittest.skipUnless(os.environ.get('ENRICHMENT_TEST_IMAGE'), 'explicit Docker image required')
class DockerControls(SandboxTests):
    # Inherit host controls too, so an opted-in run still exercises the whole boundary.
    def run_worker(self, code, seconds=15, fails=False):
        dest = self.root/'result'
        prefix = "import os,pathlib,json,time,subprocess\nos.umask(0o077)\nr=pathlib.Path('/tmp/session/.resources');r.mkdir(parents=True)\n"
        original_capture=sandbox.capture
        def observed(command,*args):
            try:
                return original_capture(command,*args)
            finally:
                docker=command[:command.index('start')]
                state=subprocess.run(docker+['inspect','--format','{{json .State}}',command[-1]],capture_output=True,text=True,timeout=5)
                if state.returncode==0:
                    details=json.loads(state.stdout)
                    print('REAL_EXIT_CONTROL',self._testMethodName,json.dumps({k:details.get(k) for k in ['Running','ExitCode','OOMKilled']}))
        with mock.patch.object(sandbox,'WORKER',prefix+code),mock.patch.object(sandbox,'capture',side_effect=observed):
            if fails:
                with self.assertRaises((RuntimeError,TimeoutError)):
                    sandbox.execute(self.session,dest,os.environ['ENRICHMENT_TEST_IMAGE'],context=os.environ.get('ENRICHMENT_TEST_CONTEXT'),timeout=seconds)
                self.assertFalse(dest.exists())
            else:
                sandbox.execute(self.session,dest,os.environ['ENRICHMENT_TEST_IMAGE'],context=os.environ.get('ENRICHMENT_TEST_CONTEXT'),timeout=seconds)
                return json.loads((dest/'control.json').read_text())
    def test_real_limits_browser_and_public_broker(self):
        code=r'''
import resource_enrichment as e
from resource_budget import JobBudget, job_scope
from playwright.sync_api import sync_playwright
cg=pathlib.Path('/sys/fs/cgroup')
limits={n:(cg/n).read_text().strip() for n in ['memory.max','memory.swap.max','pids.max','cpu.max']}
assert limits['memory.max']=='1073741824' and limits['memory.swap.max']=='0' and limits['pids.max']=='128'
assert limits['cpu.max']=='100000 100000'
limits['tmp_bytes']=os.statvfs('/tmp').f_frsize*os.statvfs('/tmp').f_blocks
limits['shm_bytes']=os.statvfs('/dev/shm').f_frsize*os.statvfs('/dev/shm').f_blocks
assert limits['tmp_bytes']==512*1024*1024 and limits['shm_bytes']==64*1024*1024
assert os.getuid()!=0
with job_scope(JobBudget(seconds=60)) as budget:
    response, body=e.fetch_limited(e._new_session(),'https://example.com/')
    assert response.status_code==200 and b'Example Domain' in body
    with sync_playwright() as p:
        browser,context=e.new_public_browser_context(p, executable_path='/tools/chromium',auth_origins=set())
        page=context.new_page()
        page.goto('https://example.com/',wait_until='networkidle')
        assert page.title()=='Example Domain'
        png=page.screenshot();pdf=page.pdf()
        assert png.startswith(b'\x89PNG') and pdf.startswith(b'%PDF')
        e.save_bytes(r/'control.png',png,False);e.save_bytes(r/'control.pdf',pdf,False)
        public=page.evaluate("async()=>{let r=await fetch('https://example.com/?subresource=1');return r.status}")
        private=page.evaluate("async()=>{try{await fetch('http://127.0.0.1/');return false}catch(e){return true}}")
        assert public==200 and private
        context.close();browser.close()
    assert budget.requests >= 3 and budget.transfer > 0
(r/'control.json').write_text(json.dumps({'limits':limits,'requests':budget.requests,'transfer':budget.transfer,'public_subresource':public,'private_blocked':private}))
'''
        result=self.run_worker(code,60)
        print('REAL_NETWORK_CONTROL',json.dumps(result))
    def test_normal_public_manifest(self):
        (self.session/'.pipeline/resource_manifest.json').write_text(json.dumps({'resources':[{'name':'Example','url':'https://example.com/'}]}))
        sandbox.execute(self.session,self.root/'result',os.environ['ENRICHMENT_TEST_IMAGE'],context=os.environ.get('ENRICHMENT_TEST_CONTEXT'),timeout=60)
        report=json.loads((self.root/'result/resource_enrichment_report.json').read_text())
        self.assertEqual(report['results'][0]['status'],'ok')
        self.assertEqual(report['session_dir'],'session')
        self.assertFalse(report['auth']['provider_authentication_verified'])
    def test_cpu_deadline(self): self.run_worker('while True: pass',4,True)
    def test_memory_exhaustion(self): self.run_worker('a=[]\nwhile True: a.append(bytearray(64*1024*1024))',15,True)
    def test_pid_exhaustion(self): self.run_worker("a=[]\nwhile True: a.append(subprocess.Popen(['sleep','60'],start_new_session=True))",15,True)
    def test_tmpfs_exhaustion(self): self.run_worker("i=0\nwhile True:\n (pathlib.Path('/tmp')/str(i)).write_bytes(b'x'*(32*1024*1024));i+=1",20,True)
    def test_log_exhaustion(self): self.run_worker("print('synthetic-private' * 100000)",10,True)
    def test_artifact_exhaustion(self): self.run_worker("for i in range(5): (r/str(i)).write_bytes(b'x'*(60*1024*1024))",20,True)
    def test_detached_descendant_terminated_before_archive(self):
        result=self.run_worker("subprocess.Popen(['python3','-c',\"import time,pathlib;time.sleep(1);pathlib.Path('/tmp/session/.resources/late').write_text('bad');time.sleep(30)\"],start_new_session=True)\n(r/'control.json').write_text('{}')")
        self.assertFalse((self.root/'result/late').exists())

    def test_actual_browser_callback_budget(self):
        self.run_worker("from playwright.sync_api import sync_playwright\nimport resource_enrichment as e\nfrom resource_budget import JobBudget,job_scope,BudgetExceeded\nbudget=JobBudget(max_transfer=10,seconds=20)\ntry:\n with job_scope(budget):\n  with sync_playwright() as p:\n   b,c=e.new_public_browser_context(p,executable_path='/tools/chromium',auth_origins=set())\n   try:\n    c.new_page().goto('https://example.com/',timeout=10000)\n   except Exception:pass\n   finally:c.close();b.close()\nexcept BudgetExceeded:pass\nassert budget.failure and budget.transfer>10\n(r/'control.json').write_text(json.dumps({'failure':budget.failure,'transfer':budget.transfer}))",30)
    def test_browser_javascript_cpu_deadline(self):
        self.run_worker("from playwright.sync_api import sync_playwright\nimport resource_enrichment as e\nwith sync_playwright() as p:\n b,c=e.new_public_browser_context(p,executable_path='/tools/chromium',auth_origins=set())\n page=c.new_page();page.evaluate('()=>{while(true){}}')",6,True)
    def test_browser_javascript_memory_failure(self):
        self.run_worker("from playwright.sync_api import sync_playwright\nimport resource_enrichment as e\nwith sync_playwright() as p:\n b,c=e.new_public_browser_context(p,executable_path='/tools/chromium',auth_origins=set())\n page=c.new_page();page.evaluate('()=>{let a=[];while(true){let b=new Uint8Array(32*1024*1024);b.fill(1);a.push(b)}}')",15,True)
    def host_signal(self, sig):
        docker=['docker','--context',os.environ.get('ENRICHMENT_TEST_CONTEXT','default')]
        script = "import sys;sys.path.insert(0,"+repr(str(sandbox.HERE))+");import sandbox_resource_enrichment as s;s.WORKER='import time;time.sleep(60)';s.execute("+repr(str(self.session))+","+repr(str(self.root/'result'))+","+repr(os.environ['ENRICHMENT_TEST_IMAGE'])+",context="+repr(os.environ.get('ENRICHMENT_TEST_CONTEXT'))+",timeout=7)"
        before=set(subprocess.check_output(docker+['ps','-aq','--filter','name=resource-enrichment-'],text=True).split())
        proc=subprocess.Popen([sys.executable,'-c',script],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        owned=None; staging=None
        try:
            end=time.monotonic()+5
            while time.monotonic()<end:
                current=set(subprocess.check_output(docker+['ps','-q','--filter','name=resource-enrichment-'],text=True).split())-before
                if current:
                    owned=current.pop();break
                time.sleep(0.05)
            self.assertIsNotNone(owned)
            details=json.loads(subprocess.check_output(docker+['inspect',owned]))[0]
            staging=Path(next(m['Source'] for m in details['Mounts'] if m['Destination']=='/tools')).parent
            proc.send_signal(sig);proc.wait(timeout=15)
            if sig==signal.SIGKILL:
                end=time.monotonic()+10
                while time.monotonic()<end:
                    state=json.loads(subprocess.check_output(docker+['inspect','--format','{{json .State}}',owned]))
                    if not state['Running']:break
                    time.sleep(0.1)
                self.assertFalse(state['Running']);self.assertNotEqual(state['ExitCode'],0)
                print('HOST_LOSS_CONTROL',json.dumps({k:state.get(k) for k in ['Running','ExitCode','OOMKilled']}))
            else:
                self.assertNotIn(owned,subprocess.check_output(docker+['ps','-aq','--filter','name=resource-enrichment-'],text=True))
            self.assertFalse((self.root/'result').exists())
        finally:
            if proc.poll() is None:proc.kill();proc.wait()
            if owned:subprocess.run(docker+['rm','-f',owned],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if sig==signal.SIGKILL and staging and staging.name.startswith('.enrichment-'):
                import shutil
                shutil.rmtree(staging)
    def test_sigterm_cleanup(self): self.host_signal(signal.SIGTERM)
    def test_host_loss_internal_deadline(self): self.host_signal(signal.SIGKILL)


if __name__=='__main__': unittest.main()
