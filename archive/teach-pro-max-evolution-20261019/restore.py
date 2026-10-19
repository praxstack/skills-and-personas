#!/usr/bin/env python3
"""Restore one verified archive into a new directory."""
import argparse,subprocess,sys,tarfile,tempfile,shutil
from pathlib import Path
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument("archive");p.add_argument("--dest",type=Path,required=True);a=p.parse_args()
subprocess.run([sys.executable,str(root/"verify.py")],check=True)
if Path(a.archive).name!=a.archive:raise SystemExit("Use an archive basename")
if a.dest.exists():raise SystemExit("Destination exists; refusing overwrite")
source=root/a.archive
with tempfile.TemporaryDirectory(prefix="prax-restore-") as temp:
 if not source.is_file():
  parts=sorted(root.glob(a.archive+".part[0-9][0-9][0-9]"))
  if not parts:raise SystemExit("Archive not found")
  if [p.name[-3:] for p in parts]!=[f"{i:03d}" for i in range(1,len(parts)+1)]:raise SystemExit("Non-contiguous archive parts")
  source=Path(temp)/a.archive
  with source.open("wb") as out:
   for part in parts:
    with part.open("rb") as f:shutil.copyfileobj(f,out)
 a.dest.mkdir(parents=True)
 with tarfile.open(source,"r:gz") as t:t.extractall(a.dest,filter="data")
print("Restored",a.archive,"to",a.dest)
