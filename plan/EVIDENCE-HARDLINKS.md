# Evidence: why learner-state files get a second hard link

Written 2026-10-18 by an evidence subagent. Probes ran on Prax's Mac (Darwin 27.0.0) without sudo. No settings or backups were changed. Every probe file lived in `~/Developer/.nlink-probe-127848800/` or `01-C/.nlink-probe-127848800/`, and both folders are deleted. Drive had already staged links to some probe files in its own upload folders. I left those alone because they belong to Drive.

## Short answer

Time Machine, backupd and revisiond do not cause it. **Google Drive for desktop does.** It backs up `~/Developer` and `~/Study` as "My Computer" folders. About 0.1 to 1.5 seconds after a file is created, it hard-links the file into `<backup root>/.tmp.driveupload/<number>` and holds that link until the upload finishes. The C study workspace sits inside `~/Study`, which explains why it is affected. The home root, `/tmp`, `~/Documents` and `~/Desktop` are not Drive backup roots, so their files stay at one link.

This matters for privacy more than for correctness. Learner state in those folders is uploaded to a Google account. Deleted or replaced learner files also stay on disk in `.tmp.driveupload` after ptk reports them deleted.

## Part A. The cause

### Proven

**1. Time Machine is not involved.**

```
$ tmutil status          -> Running = 0
$ tmutil destinationinfo -> tmutil: No destinations configured.
$ tmutil listlocalsnapshots / -> (none)
```

The links still appeared with Time Machine idle and no destination configured.

**2. The link appears in about 0.1 s and stays.** I created one file in each probe folder and polled `stat -f %l` every 0.5 s.

```
/Users/prax/Developer/.nlink-probe-127848800       nlink=2 after .55s ino=178073777
.../01-C/.nlink-probe-127848800                     nlink=2 after .55s ino=178073778
.../scratchpad (under /private/tmp)                 nlink stayed 1 for 15s
```

For both files, ctime was about 90 ms after birth time (`birth=…354.074 change=…354.163`). Eleven minutes later both files still had 2 links. Neither file had any xattr, and neither carried a `com.apple.fileprovider` attribute.

**3. The second link is Drive's upload staging.** `lsof` showed the `Google Drive` process (pid 50903) holding `/Users/prax/Developer` open as a directory and holding dozens of files in `/Users/prax/Developer/.tmp.driveupload/`. Searching by inode found both probe files.

```
$ ls -i ~/Developer/.tmp.driveupload | grep -w 178073777
178073777 1681973
$ ls -i ~/Study/.tmp.driveupload | grep -w 178073778
178073778 1681977
$ cmp ~/Developer/.tmp.driveupload/1681973 <probe file> && echo same-content
same-content
```

**4. Drive's config lists exactly these two folders as backup roots.** I read a copy of `~/Library/Application Support/Google/DriveFS/root_preference_sqlite.db` and deleted the copy afterwards.

```
1|…|Study|Users/prax/Study|118367463353458512207|1|1|1|2|0|0||/Users/prax/Study
2|…|Developer|Users/prax/Developer|118367463353458512207|1|1|1|2|0|0||/Users/prax/Developer
```

No other roots are listed. The home root, `~/Documents` and `~/Desktop` are not Drive roots. I did not write probe files into those three. That result comes from the config and from the earlier home-root observation.

**5. Drive's own log names the mechanism.** From `~/Library/Application Support/Google/DriveFS/Logs/drive_fs_28.txt`:

```
2026-10-18T13:29:24.796Z E [3794363:mirror_118367463353458512207] content_sync_manager.cc:255:RegisterUpload
  Creating hard link to /Users/prax/Developer/prax-teach-evaluation-20261016/v2.1/.state/tmp/... returned with NOT_FOUND
```

Only failures print the path. Successful links are not logged with a path, so the probe files do not show up in the log. The same logs mention the v2.1 test tree's `.state/tmp/.../course/state/concepts.json` and contain 327 lines titled `learner.json` or `state-learner.schema.json`. Drive is uploading the test suite's learner fixtures too.

**6. Which files get linked.** These were linked within 1.1 to 1.5 s: `.hidden`, `x.tmp`, a file with no extension, `a.json`, `node_modules/m.js`, `.git/HEAD`, `build/b.o`, `.state/learner.json`, `~$lock.docx`, and a 20 MB binary. Only two files were skipped: an empty file and `.DS_Store`. Drive does not exclude dotfiles, `.git`, `node_modules` or build output.

**7. Backlog and orphans right now.** `~/Developer/.tmp.driveupload` holds 32,730 entries using 1.3 GB. 28,690 still have 2 links. **4,040 have 1 link, 220 MB in total.** Each of those is a staged copy whose original path was deleted or replaced, so the staged copy is the only one left on disk. The oldest staging ctime is 2026-10-18 19:00 IST. My first Study probe was still staged after 20 minutes.

### Likely, not proven

- Drive watches its roots with FSEvents. The roughly 90 ms delay fits that. No Endpoint Security extension is installed (`systemextensionsctl list` shows only Tailscale, Proton VPN and Karabiner).
- revisiond and GenerationalStorage keep their store in `/System/Volumes/Data/.DocumentRevisions-V100`, which is root-only. I cannot see whether they also made links. They are not the cause here, because the second link was found in Drive's folder.
- Drive will probably unlink a staged entry once its upload completes. In Study, earlier entries had been cleared and only the probe entries were left. I could not watch one clear during the session because the queue is backed up.

### Not determinable without root or the Drive web UI

- What Drive does with a file deleted locally after it has been uploaded. Google documents a setting that controls whether deletions propagate to the "My Computer" copy, and I did not read that setting. The cloud copy and Drive's trash cannot be inspected from here.
- Whether Drive uploads xattrs, including `user.praxteach.learner`.
- `fs_usage` and `eslogger` need root, so I could not get a syscall trace of the `link()` call. The inode match plus the log line are enough to prove the cause.

## Part B. What v2.1 changed in learner-state handling

### v2 rule (before b74277b)

v2 refused every state file, journal and workspace lock with more than one link. In `ptk/state/io.py::secure_workspace`, `read_bytes` and `_workspace_inode_lock`, and in the journal loaders in `state.py` and `continuity.py`:

```python
if required_stat.st_nlink != 1:
    raise SafetyError(f"required state file must not be a hardlink: state/{name}")
...
if lock_stat.st_nlink != 1:
    raise SafetyError("workspace lock must not be a hardlink")
```

Exit code 5. With Drive running, every new state file under `~/Developer` or `~/Study` fails this check within about a second.

### b74277b, integration pass (round 15)

Every `st_nlink != 1` became `not link_count_ok(entry, label)`:

```python
def link_count_ok(entry, label):
    if entry.st_nlink == 1:
        return True
    if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode):
        return False
    if geteuid is None or entry.st_uid != geteuid():
        return False
    warnings.warn(f"... has {entry.st_nlink} hard links (macOS backup or versioning adds them); accepted ...")
    return True
```

Accepted: any regular file this user owns, with any number of links, plus a warning. Refused: symlinks, non-regular files, and files owned by another user. Two ported v2 tests were weakened. A link from learner B's `sessions.jsonl` into learner A's workspace was now read and exported as A's.

### e0e1d37, round 17 (D22.3), current HEAD

`link_count_ok` became `link_problem(entry, label, carried=..., expected=...)`:

```python
if entry.st_nlink == 1:
    if not regular or expected is None or expected == ANY_BINDING: return None
    binding = carried()
    if binding is not None and binding != expected:
        return "is bound to another learner workspace"
    return None
if symlink or not regular:            return "is a hardlink and not a regular file"
if entry.st_uid != geteuid():         return "is a hardlink owned by another user"
if expected is None:                  return "is a hardlink, and this workspace has no learner binding ..."
binding = carried()
if binding is None:                   return "is a hardlink that carries no learner binding ... run rebind"
if expected != ANY_BINDING and binding != expected:
                                      return "is a hardlink bound to another learner workspace"
warnings.warn(... HardlinkAccepted)   # accepted
return None
```

Supporting changes:

- `init` puts a random `lw-<32 hex>` in xattr `user.praxteach.learner` on `state/`. `ensure_binding` creates it on older workspaces too, on any command.
- Every write path stamps the binding on a fresh `O_EXCL` temporary file before the rename: `atomic_write`, `atomic_write_anchored`, `make_private_file`, export and rollback.
- The workspace lock is created with `O_EXCL`. An existing lock is checked by path before it is opened.
- A legacy single-link file with no binding is stamped on read. This is called adoption.
- New command `python -m ptk.state rebind <ws> [--confirm]`. It copies unbound multi-link files onto fresh bound inodes.
- The two ported tests are back to v2 bytes, so the cross-learner link exits 5 again.

### Accepted or refused, input by input

| Input | v2 | b74277b | e0e1d37 (now) |
|---|---|---|---|
| Regular file, 1 link, no binding | accept | accept | accept, then stamp |
| Regular file, 1 link, this binding | n/a | n/a | accept |
| Regular file, 1 link, another workspace's binding | accept | accept | **refuse 5** |
| Own file, 2+ links, this binding (Drive staging link) | **refuse 5** | accept + warning | accept + warning |
| Own file, 2+ links, no binding (legacy, or xattrs stripped) | refuse 5 | accept + warning | refuse 5, points to `rebind` |
| Own file, 2+ links, another workspace's binding | refuse 5 | **accept + warning** | refuse 5 |
| 2+ links, owned by another user | refuse 5 | refuse | refuse 5 |
| Symlink, FIFO, device | refuse | refuse | refuse |
| 2+ links on a filesystem without xattrs | refuse 5 | accept | refuse 5, same as v2 |
| Full-deletion journal, 2+ links, any binding | refuse | accept | accept (`ANY_BINDING`) |

Only one input that v2 refused is now accepted: a multi-link regular file you own that carries this workspace's binding. One input that v2 accepted is now refused: a single-link file bound to another workspace.

### Checked live

I ran `init`, `show` and `delete --all-state --confirm` in a Drive-backed probe folder. Six of the eight state files had 2 links within 4 s, and `show` printed `warning: ... state/concepts.json has 2 hard links (macOS backup or versioning adds them); read because it carries this learner workspace's binding`. **The warning text blames the wrong thing.** The cause is Google Drive.

## Part C. Privacy and consent

### 1. Deletion: the data survives

This is proven on disk. After `delete --all-state --confirm` returned `"status":"all_state_deleted"` and the workspace was gone:

```
SURVIVES state/learner.json -> ~/Developer/.tmp.driveupload/1682115 nlink 1  has goal marker: True  has learner id: True
SURVIVES MISSION.md         -> 1682105 nlink 1  has goal marker: True
SURVIVES state/concepts.json, misconceptions.json, sources.json, RESOURCES.md
survivors 6 of 8
```

The learner id and goal are still readable in Drive's staging folder. They were also queued for upload to a Google account, and ptk has no control over that copy. The same thing happened in the study folder (`~/Study/.tmp.driveupload/1682081` kept `{"learner":"OLD-SECRET"}` after `unlink`). After 100 s both copies were still present. The 4,040 orphans already in `~/Developer/.tmp.driveupload` show this is normal Drive behaviour while the queue is backed up.

### 1b. Atomic replace

I wrote "OLD", waited for the staging link, then replaced the file with tmp plus rename. **Drive dropped the staging link to the old inode in that run**, in both folders, so the old bytes were not kept locally. The new inode was staged in its place. A file that is created and then deleted keeps its staged copy, but in this run a replace did not. I would not rely on that. The behaviour is Drive's and could depend on timing. If the old content was already uploaded, Drive's version history keeps it either way.

`test_write_never_goes_through_an_alias` shows the other direction: ptk never writes through a link, so any outside alias keeps the old bytes. That protects another learner's file, and it also means a stale alias keeps the old learner data alive.

### 2. Export and inspect

`export` and `show` only read the workspace. Neither can see `.tmp.driveupload`, Drive's cloud copy, Drive's version history or Drive's trash. A learner who uses "inspect" and "export" is not shown every copy. The consent record lists `location: <workspace path>` and `controls: inspect, correct, export, delete`. With Drive running, the delete control does not do what it says.

### 3. Cross-learner aliasing

- **A hard link from B's file into A's workspace is refused (exit 5)** when both carry bindings. The test exists, and the logic checks out.
- **B's file with the xattr stripped, then linked into A**: refused with exit 5, and the message points to `rebind`. `rebind --confirm` would copy B's data into A as A's. The only guard is the prompt "check they are this learner's own".
- **B's file copied into A without xattrs** (`cp -X`, Drive download, zip): the copy has one link and no binding, so it is adopted silently and read as A's. I ran this. `show` exited 0 and stamped it with A's binding. v2 also accepted it, so this is not a regression. The binding stops links. It does not stop copies.
- **Restore without xattrs into a Drive-backed folder** breaks the workspace. I ran `cp -RX` of a workspace into the Developer probe folder. Drive linked the files within 4 s, before ptk ran. `show` then exited 5 ("hardlink that carries no learner binding"), and `rebind` listed every file. A learner who restores from Drive, which probably drops xattrs (not verified), gets locked out until they run `rebind --confirm`.
- The binding is a plain label. The same Unix user can read and copy it. It stops accidents. It does not stop a same-user attacker, and PROTECTED-MAP already says so.

### 4. Consent

**Unchanged for content.** `init` without `--consent` still raises `ConsentRequired` and creates nothing. I checked: `ws-noconsent` did not exist afterwards. The same check is at `cli.py:337`, matching v2.

**Changed for metadata.** `ensure_binding` runs inside `secure_workspace` on every command, including `show`, `export` and `delete --dry-run`. Adoption stamps legacy files on read. Both write xattrs, even after `disable-persistence`. PROTECTED-MAP admits this. The learner bytes do not change. It still breaks v2's "read-only commands write nothing" property. More important, consent never covered third-party copies. The consent text says the data stays at `location`. With Drive on, every consented write is also uploaded to Google within seconds. This is not caused by ptk, but ptk is the one telling the learner where the data lives.

### 5. What a learner should be told

Before `init`, in plain words:

- "This folder is backed up by Google Drive for desktop to the account linked to Drive. Your goal, practice evidence and reviews will be copied to Google within seconds."
- "Deleting here does not delete Google's copy, its version history or its trash, and a local copy can stay in `.tmp.driveupload` until Drive finishes uploading. To remove everything, also delete it in Drive and empty Drive's trash."
- "Export shows what is in this workspace. It does not show the copies Drive keeps."

## Recommendation

Safest design, in order:

1. **Keep learner state out of Drive-backed folders by default.** Put workspaces under a path no sync tool watches, for example `~/Library/Application Support/prax-teach/<learner>/` or another non-synced path Prax picks. Lesson sources can stay in `~/Developer` and `~/Study`. Only `state/`, `MISSION.md` and `RESOURCES.md` need to move.
2. **Detect and refuse, with an explanation.** At `init` and at `delete`, look for a `.tmp.driveupload` folder in any ancestor directory, or check the path against Drive's root list. If one is found, refuse with a message naming Google Drive and the folder, unless the learner passes something like `--allow-synced-location` after reading the text from section 5. A learner who chooses a synced folder then consents to it knowingly.
3. **Keep D22.3's binding.** It correctly restores v2's cross-learner refusal and keeps working when Drive is on. Fix the warning text so it names Google Drive or "a sync or backup tool" instead of "macOS backup or versioning".
4. **Make deletion honest.** When `delete` sees that a deleted inode still exists elsewhere, it cannot tell from user space where that is. It can tell when `st_nlink > 1` before the unlink. In that case it should say "another copy of this file exists outside the workspace (link count N); ptk cannot delete it", and it should not report plain `all_state_deleted`.
5. **Stop the test suite writing learner fixtures under `~/Developer`.** The `.state/tmp` fixtures are going to Google now. Use `$TMPDIR` for them.

Prax decides:

- Whether learner state may live in a folder Drive backs up at all. My recommendation is no by default, with an explicit opt-in.
- Whether to approve D22.3, which is pending in PROTECTED-MAP. I recommend approving it with the warning-text fix. Its premise "macOS backupd/revisiond" is wrong and should be corrected in PROTECTED-MAP, README and the code comments.
- Whether read-only commands may write xattrs after consent is withdrawn. If not, `ensure_binding` and adoption should be skipped when `persistent_state` is false.
- Whether to remove `~/Developer` or `~/Study` from Drive backup, or exclude the workspace path. That is Prax's own setting. I did not touch it.
- What to do about the learner data already in Drive and in `~/Developer/.tmp.driveupload`. That includes the test-fixture `learner.json` files and the probe workspace with the fake id `probe-learner`.
