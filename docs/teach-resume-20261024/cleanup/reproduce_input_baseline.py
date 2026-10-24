import importlib.util,json,os,subprocess,sys,tempfile
from pathlib import Path
from unittest import mock
r=Path.cwd();sys.path.insert(0,str(r/'skills/transcript-pipeline/scripts'))
with tempfile.TemporaryDirectory(dir=Path.home()) as tmp:
 root=Path(tmp);source=root/'baseline.py';source.write_bytes(subprocess.check_output(['git','show','d246f6f:skills/transcript-pipeline/scripts/resource_enrichment.py']))
 spec=importlib.util.spec_from_file_location('attack_baseline',source);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
 result=[]
 for attack in ('pipeline-symlink','leaf-symlink','hardlink','directory-swap-before-open'):
  s=root/attack;p=s/'.pipeline';p.mkdir(parents=True);outside=root/(attack+'-outside');outside.mkdir();target=outside/'resource_manifest.json';target.write_text('{"resources":[{"name":"outside-marker","url":"https://example.com"}]}');leaf=p/'resource_manifest.json'
  if attack=='pipeline-symlink':p.rmdir();p.symlink_to(outside,target_is_directory=True)
  elif attack=='leaf-symlink':leaf.symlink_to(target)
  elif attack=='hardlink':os.link(target,leaf)
  else:leaf.write_text('{"resources":[]}')
  real_open=Path.open
  def swapped(path,*args,**kwargs):
   if path==leaf:
    p.rename(s/'old-pipeline');p.symlink_to(outside,target_is_directory=True)
   return real_open(path,*args,**kwargs)
  with mock.patch.object(Path,'open',swapped if attack=='directory-swap-before-open' else real_open):
   names=[x.name for x in module.parse_manifest(s)]
  assert names==['outside-marker'],(attack,names)
  result.append({'attack':attack,'baselineReadOutsideMarker':True})
 (r/'docs/teach-resume-20261024/cleanup/input-attacks-baseline.json').write_text(json.dumps({'source':'d246f6f','scope':'synthetic parse only; no network; before any manifest fix','controls':result},indent=2)+'\n')
 print(result)
