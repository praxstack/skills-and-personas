#!/usr/bin/env python3
"""Exercise only local TUI menus in a disposable no-daemon session. No model prompt."""
import os, pty, subprocess, select, time, termios, fcntl, struct, json, re
from pathlib import Path
out=Path(__file__).parent
pid,master=pty.fork()
if pid==0:
 fcntl.ioctl(0,termios.TIOCSWINSZ,struct.pack("HHHH",40,120,0,0))
 env=dict(os.environ,TERM="xterm-256color",COLORTERM="truecolor")
 os.execve("/Users/prax/.local/bin/codex",["codex","--no-daemon","--strict-config","-C","/tmp"],env)
all_data=b""
def read_for(seconds):
 global all_data
 deadline=time.monotonic()+seconds; data=b""
 while time.monotonic()<deadline:
  ready,_,_=select.select([master],[],[],min(.1,max(0,deadline-time.monotonic())))
  if ready:
   try: chunk=os.read(master,65536)
   except OSError: break
   if not chunk:break
   data+=chunk
 all_data+=data
 (out/"tui-live.ansi").write_bytes(all_data)
 return data
def send(s):
 try: os.write(master,s.encode())
 except OSError: pass
startup=read_for(8)
(out/"startup.ansi").write_bytes(startup)
send("\x1b");read_for(.7)
send("\x15/theme");read_for(.7);send("\r"); theme=read_for(2)
send("\x1b");read_for(.5)
send("\x15/statusline");read_for(.7);send("\r"); status=read_for(2)
send("\x1b");read_for(.5)
send("\x15/quit");read_for(.7);send("\r");read_for(4)
_,wait_status=os.waitpid(pid,0)
code=os.waitstatus_to_exitcode(wait_status)
for name,data in [("startup",startup),("theme-picker",theme),("statusline-picker",status),("tui-full",all_data)]:
 (out/(name+".ansi")).write_bytes(data)
 plain=re.sub(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)","",data.decode(errors="replace"))
 plain=re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]","",plain)
 (out/(name+".txt")).write_text(plain)
result={"exit_code":code,"no_daemon":True,"strict_config":True,"model_prompt_submitted":False,"dimensions":"120 columns x 40 rows","theme_picker_opened":b"theme" in theme.lower(),"statusline_picker_opened":b"status" in status.lower(),"theme_picker_bytes":len(theme),"statusline_picker_bytes":len(status)}
(out/"verification.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
print("THEME:", (out/"theme-picker.txt").read_text()[-7000:])
print("STATUS:", (out/"statusline-picker.txt").read_text()[-7000:])
