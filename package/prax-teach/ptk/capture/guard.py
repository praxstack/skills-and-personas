"""Source guard for lesson programs (review WP2 P1-1, P1-2).

The UB guard (D17.4) trusts clang's warnings and the sanitizers. A lesson program is agent-written,
so it may not switch either off. Two scans, one rule table:

  scan_source(text)          the program text, after trigraphs, line splices, comments and string
                             literals are handled. Directives can only come from here (a macro can
                             never produce one), so line markers, #line, #embed and #pragma are found
                             here. `ptk validate` runs this scan.
  scan_preprocessed(out, f)  clang -E output, lines that belong to the program file only. A macro can
                             paste `_Prag ## ma` or `no_san ## itize`; clang's own preprocessor shows
                             the result. Capture runs this scan before anything runs.

A construct is allowed only when a claim names it in `overrides`, lists the program in `programs`,
and the program never runs (ub:true or run:false). A running program's facts always come from a
fully guarded compile.

read_program() copies the source with no symlink followed (P1-2), and filter_stderr() keeps only
diagnostics about the lesson's own file, so a compiler quoting another file never reaches a report.
"""
import os
import re
import stat
from pathlib import Path

from .. import errors

CONSTRUCTS = {
    "pragma-diagnostic": "#pragma clang/GCC diagnostic changes which warnings clang reports",
    "pragma-attribute": "#pragma clang attribute applies attributes (no_sanitize) to many declarations",
    "pragma-system-header": "#pragma system_header hides the file's warnings",
    "pragma-operator": "_Pragma(...) is a #pragma that can hide inside a macro",
    "pragma-other": "a #pragma outside the allowed STDC and pack pragmas",
    "line-marker": "a GNU line marker (# N \"file\" 3) makes clang treat the program as a system header",
    "line-directive": "#line relocates diagnostics to another file name",
    "embed": "#embed is C23 (lessons are C17) and reads another file's bytes",
    "no-sanitize": "a no_sanitize-style attribute removes the sanitizers from a function",
    "sanitizer-hook": "a sanitizer runtime hook or option override (__asan_*, __ubsan_*, __sanitizer_*)",
    "asm": "an asm label or inline asm can define sanitizer hooks under another name",
    "dynamic-symbol": "dlsym/dlopen can reach sanitizer hooks by name at run time",
}
ALLOWED_PRAGMAS = ("STDC", "pack")
NO_SANITIZE = {"no_sanitize", "no_sanitize_address", "no_sanitize_undefined", "no_sanitize_memory",
               "no_sanitize_thread", "no_sanitize_coverage", "no_address_safety_analysis",
               "disable_sanitizer_instrumentation", "no_profile_instrument_function"}
HOOK_IDENT = re.compile(r"^_*(asan|ubsan|lsan|msan|tsan|hwasan|sanitizer)_")
HOOK_STRING = re.compile(r"(^|_)(asan|ubsan|lsan|msan|tsan|hwasan|sanitizer)_")
TRIGRAPHS = {"=": "#", "(": "[", "/": "\\", ")": "]", "'": "^", "<": "{", "!": "|", ">": "}", "-": "~"}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
LINE_MARKER = re.compile(r'^#\s*(\d+)\s+"((?:[^"\\]|\\.)*)"(.*)$')
MAX_SOURCE = 256 * 1024


def _phases(text):
    """C translation phases 1-2: trigraphs (on in -std=c17), then line splices. Newlines that a splice
    removes are added back after the joined line, so line numbers stay right."""
    text = re.sub(r"\?\?([=(/)'<!>-])", lambda m: TRIGRAPHS[m.group(1)], text)
    out, buf, carry = [], "", 0
    for line in text.split("\n"):
        m = re.search(r"\\[ \t]*$", line)
        if m:
            buf += line[:m.start()]
            carry += 1
            continue
        out.append(buf + line + "\n" * carry)
        buf, carry = "", 0
    if buf:
        out.append(buf)
    return "\n".join(out)


def _strip(text):
    """Comments become a space, string and char literals become "" / '' with their bodies returned
    separately. Newlines are kept, so line numbers survive. Returns (code, [(line, body), ...])."""
    code, strings = [], []
    i, n, line = 0, len(text), 1
    while i < n:
        c = text[i]
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            line += text.count("\n", i, j)
            code.append(" " + "\n" * text.count("\n", i, j))
            i = j
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            code.append(" ")
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            strings.append((line, text[i + 1:j]))
            code.append(c + c)
            i = j + 1
        else:
            if c == "\n":
                line += 1
            code.append(c)
            i += 1
    return "".join(code), strings


def _pragma_construct(body):
    words = body.split()
    if not words:
        return "pragma-other"
    if words[0] in ALLOWED_PRAGMAS:
        return None
    if words[0] in ("clang", "GCC") and len(words) > 1:
        if words[1] == "diagnostic":
            return "pragma-diagnostic"
        if words[1] == "attribute":
            return "pragma-attribute"
        if words[1] == "system_header":
            return "pragma-system-header"
    return "pragma-other"


def _directive(line):
    """(name, rest) when the line is a preprocessing directive (`#` or the `%:` digraph)."""
    s = line.lstrip()
    if s.startswith("%:"):
        s = "#" + s[2:]
    if not s.startswith("#"):
        return None
    rest = s[1:].lstrip()
    m = re.match(r"[A-Za-z_]\w*|\d+", rest)
    return (m.group(0), rest[m.end():]) if m else ("", rest)


def _token_findings(code, strings, first_line=1):
    found = []
    for ln, line in enumerate(code.split("\n"), first_line):
        for ident in IDENT.findall(line):
            norm = ident.strip("_") if ident.startswith("__") else ident
            if ident == "_Pragma":
                found.append(("pragma-operator", ln, ident))
            elif norm in NO_SANITIZE or norm.startswith("no_sanitize"):
                found.append(("no-sanitize", ln, ident))
            elif HOOK_IDENT.match(ident):
                found.append(("sanitizer-hook", ln, ident))
            elif ident in ("asm", "__asm", "__asm__"):
                found.append(("asm", ln, ident))
            elif ident in ("dlsym", "dlopen", "dlvsym"):
                found.append(("dynamic-symbol", ln, ident))
    for ln, body in strings:
        if HOOK_STRING.search(body):
            found.append(("sanitizer-hook", ln, f'"{body[:60]}"'))
    return found


def scan_source(text):
    """Constructs in the program text: [{construct, line, text}], in source order."""
    code, strings = _strip(_phases(text))
    found = []
    for ln, line in enumerate(code.split("\n"), 1):
        d = _directive(line)
        if not d:
            continue
        name, rest = d
        if name.isdigit():
            found.append(("line-marker", ln, line.strip()[:80]))
        elif name == "line":
            found.append(("line-directive", ln, line.strip()[:80]))
        elif name == "embed":
            found.append(("embed", ln, line.strip()[:80]))
        elif name == "pragma":
            kind = _pragma_construct(rest)
            if kind:
                found.append((kind, ln, line.strip()[:80]))
    found += _token_findings(code, strings)
    return [{"construct": c, "line": ln, "text": t} for c, ln, t in sorted(found, key=lambda x: x[1])]


def scan_preprocessed(out, main_name):
    """Constructs in clang -E output, only in lines that belong to the program file `main_name`."""
    found, current, line_no = [], None, 0
    for raw in out.split("\n"):
        m = LINE_MARKER.match(raw)
        if m:
            current, line_no = m.group(2), int(m.group(1))
            continue
        if current == main_name:
            s = raw.lstrip()
            if s.startswith("#pragma"):
                kind = _pragma_construct(s[len("#pragma"):])
                if kind:
                    found.append((kind, line_no, s[:80]))
            elif s:
                code, strings = _strip(raw)
                found += [(c, line_no, t) for c, _ln, t in _token_findings(code, [(line_no, b) for _l, b in strings])]
        line_no += 1
    return [{"construct": c, "line": ln, "text": t} for c, ln, t in found]


def allowed_constructs(data, program):
    """Constructs a claim declares for this program. Empty for a program that runs."""
    if program.get("run", True) and not program.get("ub"):
        return set()
    out = set()
    for c in data.get("claims", []):
        if program["id"] in c.get("programs", []):
            out |= set(c.get("overrides", []))
    return out


def refusal(findings, allowed, program_path, pointer, layer):
    """The ModelReferenceError for the first construct not allowed, or None."""
    bad = [f for f in findings if f["construct"] not in allowed]
    if not bad:
        return None
    f = bad[0]
    msg = (f"guard: {program_path}:{f['line']} uses {f['construct']} ({CONSTRUCTS[f['construct']]}); "
           "remove it, or for a program that never runs declare it in a claim's `overrides`")
    return errors.ModelReferenceError(msg, pointer=pointer, construct=f["construct"], layer=layer,
                                      program=program_path, findings=bad[:20])


# ---------------------------------------------------------------- P1-2: reading the program

def read_program(lesson_dir, rel_path, pointer):
    """The program's bytes, read with no symlink followed anywhere inside the lesson.

    Refuses when programs/ or the file is a symlink, when the file is not a regular file, or when it is
    larger than MAX_SOURCE. Opens programs/ with O_NOFOLLOW|O_DIRECTORY and the file
    relative to that fd with O_NOFOLLOW, so nothing can swap a link in between the check and the read.
    """
    rel = Path(rel_path)
    if rel.is_absolute() or ".." in rel.parts or len(rel.parts) != 2 or rel.parts[0] != "programs":
        raise errors.ModelReferenceError(f"program path {rel_path} must be programs/<name>.c", pointer=pointer)
    base = Path(lesson_dir)
    for p in (base / rel.parts[0], base / rel):
        if p.is_symlink():
            raise errors.ModelReferenceError(f"{p.relative_to(base)} is a symlink; ptk never follows links out of "
                                             "a lesson. Copy the file in.", pointer=pointer)
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        dfd = os.open(base / rel.parts[0], flags | os.O_DIRECTORY)
    except FileNotFoundError:
        raise errors.ModelReferenceError(f"program file {rel_path} missing", pointer=pointer) from None
    except OSError as e:
        raise errors.ModelReferenceError(f"cannot open programs/ safely: {e.strerror}", pointer=pointer) from None
    try:
        try:
            fd = os.open(rel.parts[1], flags | os.O_NONBLOCK, dir_fd=dfd)
        except FileNotFoundError:
            raise errors.ModelReferenceError(f"program file {rel_path} missing", pointer=pointer) from None
        except OSError as e:
            raise errors.ModelReferenceError(f"cannot open {rel_path} safely ({e.strerror}); a symlink is refused",
                                             pointer=pointer) from None
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                raise errors.ModelReferenceError(f"{rel_path} is not a regular file", pointer=pointer)
            # No st_nlink check: on this Mac a background process gives new files under ~/Developer a
            # second hard link within seconds, so a link count says nothing about provenance. The agent
            # writes the lesson, and a hard link exposes no more than copying the file in would; the
            # protections that matter are no symlink followed, regular file only, size cap, and compiler
            # stderr limited to the lesson's own files.
            if st.st_size > MAX_SOURCE:
                raise errors.ModelReferenceError(f"{rel_path} is {st.st_size} bytes; a lesson program stays under "
                                                 f"{MAX_SOURCE}", pointer=pointer)
            chunks = []
            while True:
                b = os.read(fd, 65536)
                if not b:
                    break
                chunks.append(b)
            return b"".join(chunks)
        finally:
            os.close(fd)
    finally:
        os.close(dfd)


# ---------------------------------------------------------------- P1-2: compiler stderr in reports

HEADER = re.compile(r"^(?P<file>.+?):\d+:\d+: (fatal error|error|warning|note|remark): ")
FUNC_HEADER = re.compile(r"^(?P<file>.+?): (In function|In member function|At top level)")
DRIVER = re.compile(r"^(clang|gcc|gcc-16|cc1|ld|collect2|clang-\d+): |^\d+ (warning|error)s? generated\.$"
                    r"|^Undefined symbols for architecture")


def filter_stderr(stderr, own_names, limit=4000):
    """Keep diagnostic blocks whose file is one of own_names, plus driver lines (linker, summary).
    A block is a `file:line:col: severity:` header and the gutter/caret lines under it. Every other
    line is dropped and counted, so a compiler quoting another file's lines never reaches a report."""
    own = set(own_names)
    kept, dropped, keep = [], 0, False
    for line in (stderr or "").split("\n"):
        if line.startswith("In file included from") or line.startswith("                 from "):
            keep = False
        elif DRIVER.match(line):
            keep = True
        else:
            m = HEADER.match(line) or FUNC_HEADER.match(line)
            if m:
                keep = m.group("file") in own
        if keep:
            kept.append(line)
        elif line.strip():
            dropped += 1
    text = "\n".join(kept).strip("\n")
    if dropped:
        text += f"\n[ptk: {dropped} stderr line(s) about files outside the lesson redacted]"
    return text[-limit:] if len(text) > limit else text
