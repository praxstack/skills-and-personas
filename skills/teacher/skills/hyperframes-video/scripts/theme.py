#!/usr/bin/env python3
"""theme.py: the film's colour theme, from one registry (themes.json) to the token file a kit reads.

Every theme is a family (Catppuccin, Tokyo Night, ...) in three slots: light, mid (in between) and dark. The
registry keeps each palette as its maker ships it (sources are in themes.json). Shipped text colours often miss
the quality bar's 4.5:1 (Tokyo Night Day's orange is 3.6:1 on its own background), so this script SOLVES the ink
for every role: same hue and saturation, lightness pushed away from the background until the colour reaches
INK_TARGET against every surface the kit paints text on. Fills keep the shipped colour; text uses the ink.

Tokens (every format carries the same keys):
  surfaces  bg, bg2 (gradient partner), deep (full-screen shade under chapter cards), panel, panel2, line, line2
  text      text (>= TEXT_TARGET, and >= INK_TARGET stepped back to STEP_BACK), muted (>= MUTED_TARGET), dim (>= INK_TARGET)
  fills     accent, warm, good, bad, cool, gold, violet          (shapes, bars, glows: the shipped colour)
  inks      accentInk, warmInk, ... violetInk                   (text and thin strokes in that colour)
  on-fills  onAccent, onWarm, ... onViolet                      (text placed ON a filled shape of that colour)
  meta      id, name, family, slot, tone ('light' or 'dark'), lights (6 chapter key lights), shadow

Usage:
  python3 theme.py list                                  every theme id, slot and tone
  python3 theme.py show catppuccin-latte                 tokens + contrast table
  python3 theme.py emit catppuccin-latte --format js --out source/src/theme.js
          formats: json | js (ES module) | ts | global (window.THEME = ...) | css (:root vars) | py
  python3 theme.py check                                 every theme: every text token >= INK_TARGET on every surface
  python3 theme.py selftest

'original' is not a theme here: it means the kit's own shipped palette, untouched (the default).
"""
import argparse
import colorsys
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "themes.json")
INK_TARGET = 4.6     # a hair over the quality bar's 4.5:1, so video encoding and anti-aliasing cannot dip it under
STEP_BACK = 0.8      # the opacity kits use for stepped-back context text (ladder rungs, idle code lines)
TEXT_TARGET = 7.0    # body text aims higher (WCAG AAA), so text > muted > dim stays a visible hierarchy
MUTED_TARGET = 5.5   # secondary text sits between the two
HUES = ["accent", "warm", "good", "bad", "cool", "gold", "violet"]
TEXT_ROLES = ["text", "muted", "dim"]
SURFACES = ["bg", "bg2", "deep", "panel", "panel2"]


# ----------------------------------------------------------------------------- colour maths (sRGB, WCAG 2.x)
def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def hexc(c):
    return "#" + "".join(f"{max(0, min(255, round(v * 255))):02X}" for v in c)


def lum(h):
    def ch(v):
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a, b, t):
    """t = 0 gives a, t = 1 gives b (straight sRGB blend, what alpha compositing does)."""
    return hexc(tuple(x + (y - x) * t for x, y in zip(rgb(a), rgb(b))))


def worst(ink, surfaces, opacity=1.0):
    """Lowest contrast of ink over any surface, with ink composited at the given opacity."""
    return min(contrast(mix(s, ink, opacity), s) for s in surfaces)


def solve(ink, surfaces, dark, target=INK_TARGET, opacity=1.0):
    """Push lightness away from the background (up on dark themes, down on light) until worst() >= target.
    Hue and saturation stay; the shipped colour is returned unchanged when it already passes."""
    if worst(ink, surfaces, opacity) >= target:
        return ink
    h, l, s = colorsys.rgb_to_hls(*rgb(ink))
    step = 0.004 if dark else -0.004
    while 0.0 <= l <= 1.0:
        l += step
        c = hexc(colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), s))
        if worst(c, surfaces, opacity) >= target:
            return c
    return "#FFFFFF" if dark else "#000000"


def on_fill(fill, text, bg):
    """Text colour for a label sitting on a filled shape: the theme's text or background if one passes,
    else the nearer of near-black / near-white, else pure black or white."""
    for c in (text, bg, "#111111", "#F7F7F7", "#000000", "#FFFFFF"):
        if contrast(c, fill) >= INK_TARGET:
            return c
    return max(("#000000", "#FFFFFF"), key=lambda c: contrast(c, fill))


# ----------------------------------------------------------------------------- registry
def registry():
    with open(REGISTRY, encoding="utf-8") as f:
        return json.load(f)


def variants():
    for fam in registry()["families"]:
        for v in fam["variants"]:
            yield fam, v


def find(theme_id):
    for fam, v in variants():
        if v["id"] == theme_id:
            return fam, v
    ids = ", ".join(v["id"] for _, v in variants())
    raise SystemExit(f"unknown theme '{theme_id}'. Known: original, {ids}")


def resolve(theme_id):
    """Every token for one theme, with solved inks. Pure function of the registry entry."""
    fam, v = find(theme_id)
    c = dict(v["colors"])
    dark = lum(c["bg"]) < 0.18
    t = {"id": v["id"], "name": v["name"], "family": fam["name"], "slot": v["slot"],
         "tone": "dark" if dark else "light", "source": fam["source"]}
    t["bg"] = c["bg"]
    t["bg2"] = mix(c["bg"], c["accent"], 0.06)
    t["deep"] = mix(c["bg"], "#000000", 0.35) if dark else mix(c["bg"], c["line"], 0.45)
    t["panel"] = c["panel"]
    t["panel2"] = mix(c["panel"], c["text"], 0.06)
    t["line"] = c["line"]
    t["line2"] = mix(c["line"], c["text"], 0.22)
    surf = [t[k] for k in SURFACES]
    # text must also survive being stepped back (STEP_BACK opacity); muted and dim are already the quiet colours,
    # so kits step back text-coloured things only.
    t["text"] = solve(solve(c["text"], surf, dark, target=TEXT_TARGET), surf, dark, opacity=STEP_BACK)
    t["muted"] = solve(c["muted"], surf, dark, target=MUTED_TARGET)
    # dim: the dimmest text, never stepped back further. A third of the way from muted toward the background,
    # then back up until it passes at full opacity.
    t["dim"] = solve(mix(t["muted"], c["bg"], 0.33), surf, dark)
    for k in HUES:
        t[k] = c[k]
        t[k + "Ink"] = solve(c[k], surf, dark)
        t["on" + k[0].upper() + k[1:]] = on_fill(c[k], t["text"], c["bg"])
    t["lights"] = [c["warm"], c["gold"], c["bad"], c["accent"], c["violet"], c["good"]]
    t["shadow"] = "#000000" if dark else mix(c["text"], "#000000", 0.5)
    return t


def report(t):
    """Contrast rows: (token, colour, worst ratio, needed, pass)."""
    surf = [t[k] for k in SURFACES]
    rows = []
    need = {"text": (TEXT_TARGET, 1.0), "muted": (MUTED_TARGET, 1.0), "dim": (INK_TARGET, 1.0)}
    for k in TEXT_ROLES:
        tgt, op = need[k]
        r = worst(t[k], surf, op)
        rows.append((k, t[k], round(r, 2), f"{tgt}" + (f" at {op} opacity" if op < 1 else ""), r >= tgt))
    r = worst(t["text"], surf, STEP_BACK)
    rows.append(("text@0.8", t["text"], round(r, 2), f"{INK_TARGET} at {STEP_BACK} opacity", r >= INK_TARGET))
    for k in HUES:
        ink = t[k + "Ink"]
        rows.append((k + "Ink", ink, round(worst(ink, surf), 2), str(INK_TARGET), worst(ink, surf) >= INK_TARGET))
        on = "on" + k[0].upper() + k[1:]
        r = contrast(t[on], t[k])
        rows.append((on, t[on], round(r, 2), f"{INK_TARGET} on {t[k]}", r >= INK_TARGET))
    return rows


def shipped_failures(theme_id):
    """How many shipped text colours (text, muted, the seven hues) miss 4.5:1 on the shipped background."""
    _, v = find(theme_id)
    c = v["colors"]
    return [k for k in ["text", "muted"] + HUES if contrast(c[k], c["bg"]) < 4.5]


# ----------------------------------------------------------------------------- emit
def fingerprint(t):
    return hashlib.sha256(json.dumps(t, sort_keys=True).encode()).hexdigest()[:12]


def render(t, fmt):
    head = f"theme-id: {t['id']}  sha: {fingerprint(t)}  (generated by theme.py; edit themes.json, not this file)"
    body = json.dumps(t, indent=2, ensure_ascii=False)
    if fmt == "json":
        return json.dumps({"_generated": head, **t}, indent=2, ensure_ascii=False) + "\n"
    if fmt == "js":
        return f"// {head}\nexport const THEME = {body};\nexport default THEME;\n"
    if fmt == "ts":
        return f"// {head}\nexport const THEME = {body} as const;\nexport default THEME;\n"
    if fmt == "global":
        return f"/* {head} */\nwindow.THEME = {body};\n"
    if fmt == "css":
        lines = [f"/* {head} */", ":root {"]
        for k, v in t.items():
            if isinstance(v, str) and v.startswith("#"):
                lines.append(f"  --t-{k}: {v};")
        lines += [f"  --t-light-{i}: {v};" for i, v in enumerate(t["lights"])] + ["}"]
        return "\n".join(lines) + "\n"
    if fmt == "py":
        return f"# {head}\nTHEME = {json.dumps(t, indent=4, ensure_ascii=False)}\n"
    raise SystemExit(f"unknown format {fmt}")


# ----------------------------------------------------------------------------- commands
def cmd_list(_a):
    for fam, v in variants():
        t = resolve(v["id"])
        print(f"{v['id']:22} {v['slot']:5} {t['tone']:5} {v['name']}")


def cmd_show(a):
    t = resolve(a.theme)
    for k, v in t.items():
        if isinstance(v, str) and v.startswith("#"):
            print(f"  {k:12} {v}")
    print("  lights      ", " ".join(t["lights"]))
    print(f"\n  shipped text colours under 4.5:1 on bg: {', '.join(shipped_failures(a.theme)) or 'none'}")
    for name, col, r, need, ok in report(t):
        print(f"  {'ok  ' if ok else 'FAIL'} {name:12} {col}  {r:5.2f}  (need {need})")


def cmd_emit(a):
    t = resolve(a.theme)
    out = render(t, a.format)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"wrote {a.out} ({t['id']}, {t['tone']}, sha {fingerprint(t)})")
    else:
        sys.stdout.write(out)


def cmd_check(_a):
    bad = 0
    n = 0
    shipped = 0
    for _, v in variants():
        t = resolve(v["id"])
        shipped += len(shipped_failures(v["id"]))
        for name, col, r, need, ok in report(t):
            n += 1
            if not ok:
                bad += 1
                print(f"FAIL {v['id']} {name} {col} {r} (need {need})")
    print(f"{n} text tokens in {sum(1 for _ in variants())} themes: {bad} below the bar after solving "
          f"({shipped} shipped text colours were under 4.5:1 before solving)")
    sys.exit(1 if bad else 0)


def cmd_selftest(_a):
    assert round(contrast("#000000", "#FFFFFF"), 2) == 21.0
    assert round(contrast("#777777", "#FFFFFF"), 2) == 4.48          # the classic just-under-AA grey
    assert mix("#000000", "#FFFFFF", 0.5) == "#808080"
    # a failing ink is pushed the right way and keeps its hue
    ink = solve("#FF9E64", ["#E1E2E7"], dark=False)
    assert contrast(ink, "#E1E2E7") >= INK_TARGET and lum(ink) < lum("#FF9E64"), ink
    h0 = colorsys.rgb_to_hls(*rgb("#FF9E64"))[0]
    h1 = colorsys.rgb_to_hls(*rgb(ink))[0]
    assert abs(h0 - h1) < 0.02, (h0, h1)
    # a passing ink is returned untouched
    assert solve("#1E66F5", ["#FFFFFF"], dark=False) == "#1E66F5"
    # registry: 10 families x (light, mid, dark), unique ids, every role present and a valid hex
    reg = registry()
    assert len(reg["families"]) == 10, len(reg["families"])
    ids = [v["id"] for _, v in variants()]
    assert len(ids) == len(set(ids)) == 30
    for fam in reg["families"]:
        assert [v["slot"] for v in fam["variants"]] == ["light", "mid", "dark"], fam["id"]
        for v in fam["variants"]:
            assert set(v["colors"]) == set(reg["roles"]), v["id"]
            for h in v["colors"].values():
                assert len(h) == 7 and h[0] == "#" and int(h[1:], 16) >= 0, (v["id"], h)
    # light slots are light, dark slots are dark
    for fam, v in variants():
        tone = resolve(v["id"])["tone"]
        if v["slot"] == "light":
            assert tone == "light", v["id"]
        if v["slot"] == "dark":
            assert tone == "dark", v["id"]
    # every theme passes after solving, and every format carries the id line kits and vstate look for
    for i in ids:
        t = resolve(i)
        assert all(ok for *_, ok in report(t)), i
        sf = [t[k] for k in SURFACES]
        assert worst(t["text"], sf) > worst(t["muted"], sf) > worst(t["dim"], sf), (i, "text > muted > dim")
        for fmt in ("json", "js", "ts", "global", "css", "py"):
            out = render(t, fmt)
            assert f"theme-id: {i}" in out, (i, fmt)
    print(f"theme selftest: ok ({len(ids)} themes, every text token >= {INK_TARGET}:1)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    s = sub.add_parser("show")
    s.add_argument("theme")
    e = sub.add_parser("emit")
    e.add_argument("theme")
    e.add_argument("--format", default="json", choices=["json", "js", "ts", "global", "css", "py"])
    e.add_argument("--out")
    sub.add_parser("check")
    sub.add_parser("selftest")
    a = ap.parse_args()
    dict(list=cmd_list, show=cmd_show, emit=cmd_emit, check=cmd_check, selftest=cmd_selftest)[a.cmd](a)


if __name__ == "__main__":
    main()
