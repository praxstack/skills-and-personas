from pathlib import Path
import pyte, html, re, json
out=Path(__file__).parent
full=(out/'tui-full.ansi').read_bytes()
sections=[]
for name,title in [('theme-picker','Installed theme picker'),('statusline-picker','Installed footer picker')]:
 chunk=(out/(name+'.ansi')).read_bytes(); end=full.index(chunk)+len(chunk)
 screen=pyte.Screen(120,40); stream=pyte.Stream(screen);stream.feed(full[:end].decode(errors='replace'))
 lines=[];plain=[]
 for y in range(40):
  row='';text=''
  for x in range(120):
   c=screen.buffer[y][x];text+=c.data
   fg=c.fg;bg=c.bg
   colors={'default':'#cdd6f4','black':'#11111b','red':'#f38ba8','green':'#a6e3a1','brown':'#f9e2af','blue':'#89b4fa','magenta':'#cba6f7','cyan':'#89dceb','white':'#cdd6f4'}
   f=('#'+fg if re.fullmatch('[0-9a-fA-F]{6}',fg) else colors.get(fg,fg))
   b=('#'+bg if re.fullmatch('[0-9a-fA-F]{6}',bg) else (colors.get(bg,bg) if bg!='default' else '#1e1e2e'))
   if c.reverse:f,b=b,f
   css=f'color:{f};background:{b};'+('font-weight:700;' if c.bold else '')+('opacity:.7;' if c.blink else '')
   row+=f'<span style="{css}">{html.escape(c.data)}</span>'
  lines.append(row);plain.append(text.rstrip())
 (out/(name+'-screen.txt')).write_text('\n'.join(plain)+'\n')
 sections.append(f'<h2>{title}</h2><p>Reconstructed from the real 120 × 40 PTY trace. Terminal default colors are represented with a dark viewer background.</p><pre class="screen">'+ '\n'.join(lines)+'</pre>')
receipt=json.loads((out/'change-receipt.json').read_text()); v=json.loads((out/'verification.json').read_text())
body='''<h1>Codex CLI: supported readability settings</h1><p class="lede">Applied and verified on Codex CLI 0.163.0, 19 October 2026.</p><p>Catppuccin Mocha gives code and diffs a consistent palette. A compact colored footer exposes the model and reasoning level, remaining context, available usage limits, and Git branch. Animations are disabled and formatted output is retained.</p><table><tr><th>Setting</th><th>Applied value</th></tr><tr><td>Syntax theme</td><td>catppuccin-mocha</td></tr><tr><td>Footer order</td><td>model-with-reasoning · context-remaining · five-hour-limit · weekly-limit · git-branch</td></tr><tr><td>Footer theme colors</td><td>true</td></tr><tr><td>Animations</td><td>false</td></tr><tr><td>Raw output mode</td><td>false</td></tr></table><h2>What this improves, and its limit</h2><p>The installed theme picker confirms the current theme and displays a real syntax/diff preview below. The installed status-line picker confirms every selected identifier. Limits and branch disappear when unavailable; testing in /tmp therefore showed no branch.</p><p>Codex does not expose supported settings for arbitrary conversation boxes, message borders, a replacement header, or custom separators between every user, assistant, and tool message. These settings improve the supported syntax and footer surfaces; they do not redesign the conversation layout. The terminal title and terminal-wide theme were preserved.</p><h2>Verification</h2><p>A new disposable session ran with <code>--no-daemon --strict-config -C /tmp</code>, opened <code>/theme</code> and <code>/statusline</code>, then exited normally with <code>/quit</code>. Exit code: <strong>0</strong>. No model request was sent. No existing session was restarted. Startup displayed two warnings before and after the UI edit; unrelated integration warnings were outside this task.</p><p>All content outside the <code>[tui]</code> table remained byte-identical to the private backups. Within the table, only the five intended keys changed. Existing other keys were preserved. The already-managed chezmoi create template has the same five settings.</p>'''
body+=''.join(sections)
body+='<h2>Files and rollback</h2><ul>'+''.join('<li><code>'+html.escape(x)+'</code></li>' for x in receipt['changed'])+'</ul><p>Private original copies: <code>'+html.escape(receipt['backup'])+'</code>. Use <code>python3 rollback-ui.py</code> from this report directory to restore only these five keys from the backups while preserving later unrelated config edits.</p><p>Raw terminal receipts: <a href="tui-full.ansi">tui-full.ansi</a>; machine-readable results: <a href="verification.json">verification.json</a>. This report contains no credentials.</p><h2>Official OpenAI documentation</h2><p><a href="https://learn.chatgpt.com/docs/cli-customization">CLI customization</a> · <a href="https://learn.chatgpt.com/docs/config-file/config-reference">Configuration reference</a>. The installed pickers provide the version-specific confirmation.</p>'
(out/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Codex CLI readability settings</title><style>body{font:16px/1.6 system-ui,sans-serif;color:#273343;background:#f6f5f1;margin:0 auto;padding:44px 28px;max-width:1050px}h1{font-size:34px;letter-spacing:-.8px;line-height:1.2}h2{margin-top:34px;font-size:23px}.lede{color:#596579}p{max-width:85ch}code{font:13px ui-monospace,monospace;background:#e9e8e3;padding:2px 4px;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse;margin:24px 0;background:#fff}th,td{text-align:left;padding:12px;border-bottom:1px solid #ddd}th{background:#e6e9ef}.screen{font:12px/1.3 ui-monospace,monospace;white-space:pre;overflow:auto;background:#1e1e2e;padding:16px;border-radius:8px}a{color:#315d92}</style>'+body+'</html>')
print(out/'report.html')
