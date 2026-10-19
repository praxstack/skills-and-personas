#!/usr/bin/env python3
"""Restore only this change's five UI keys, preserving unrelated current edits."""
from pathlib import Path
import json, sys
out=Path(__file__).parent
receipt=json.loads((out/'change-receipt.json').read_text())
keys=set(receipt['fields'])
def split(s):
 before,body=s.split('[tui]\n',1)
 idx=body.find('\n[')
 return before,body[:idx],body[idx:]
for target,backup_name in zip(receipt['changed'],['config.toml','create_private_config.toml.tmpl']):
 p=Path(target); before,body,after=split(p.read_text())
 _,old,_=split((Path(receipt['backup'])/backup_name).read_text())
 original={l.split('=',1)[0].strip():l for l in old.splitlines() if '=' in l and l.split('=',1)[0].strip() in keys}
 new=[];restored=set()
 for line in body.splitlines():
  key=line.split('=',1)[0].strip() if '=' in line else None
  if key in keys:
   if key in original:new.append(original[key]);restored.add(key)
  else:new.append(line)
 new += [line for key,line in original.items() if key not in restored]
 result=before+'[tui]\n'+'\n'.join(new)+'\n'+after
 if '--check' in sys.argv:
  print('Rollback prepared without writing:',p)
 else:
  p.write_text(result);print('Restored UI keys:',p)
