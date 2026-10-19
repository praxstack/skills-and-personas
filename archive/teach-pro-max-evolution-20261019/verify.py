#!/usr/bin/env python3
"""Verify the publication inventory without running archived code."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
manifest=json.loads((root/"PUBLICATION.json").read_text())
errors=[]
for item in manifest["files"]:
 p=root/item["path"]
 if not p.resolve().is_relative_to(root):errors.append(item["path"]+": outside archive");continue
 if not p.is_file():errors.append(item["path"]+": missing");continue
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 if p.stat().st_size!=item["bytes"] or h.hexdigest()!=item["sha256"]:errors.append(item["path"]+": changed")
if errors:
 print("FAIL\n"+"\n".join(errors));sys.exit(1)
print(f"PASS: {len(manifest['files'])} publication files match bytes and SHA-256")
