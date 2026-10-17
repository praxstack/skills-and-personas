#!/usr/bin/env bash
# Everything: fast checks, then builds driven in Chromium and a real video export.
#   scripts/tests/run_all.sh            (from the teacher folder)
# Browser parts need Playwright (PLAYWRIGHT_MODULE=/path/to/node_modules/playwright works)
# and are skipped, loudly, when it's missing. Video parts need ffmpeg.
set -uo pipefail
T="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
S="$T/skills"
OUT="${TEACHER_TEST_OUT:-$(mktemp -d)}"
fail=0
step() { echo; echo "== $*"; }
check() { if "$@"; then echo "ok: $*" | cut -c1-120; else echo "FAIL: $*" | cut -c1-160; fail=1; fi; }

step "fast checks"
check python3 "$T/scripts/tests/test_teacher.py"

step "builds"
check python3 "$S/explorable/scripts/build.py" "$S/explorable/assets/examples/seasons.lesson.js" -o "$OUT/seasons.html"
check python3 "$S/concept-animation/scripts/build.py" "$S/concept-animation/assets/examples/neuron.anim.js" -o "$OUT/neuron.html"

if node -e "import('$S/visual-qa/scripts/pw.mjs').then(m=>m.loadPlaywright()).then(()=>process.exit(0))" >/dev/null 2>&1; then
  step "explorable, every step in Chromium"
  check node "$S/explorable/scripts/test_lesson.mjs" "$OUT/seasons.html"
  step "visual QA: paper and chalkboard"
  check node "$S/visual-qa/scripts/check_page.mjs" "$OUT/seasons.html" --out "$OUT/shots" --eval "window.__explorable.check()"
  check node "$S/visual-qa/scripts/check_page.mjs" "$OUT/seasons.html" --board chalk
  check node "$S/visual-qa/scripts/check_page.mjs" "$OUT/neuron.html"
  if command -v ffmpeg >/dev/null; then
    step "frame-exact export and video QA"
    check node "$S/concept-animation/scripts/export.mjs" "$OUT/neuron.html" --out "$OUT/neuron.mp4" --fps 24 --gif "$OUT/neuron.gif"
    check python3 "$S/visual-qa/scripts/check_video.py" "$OUT/neuron.mp4" --sheet "$OUT/neuron-sheet.png" --min-height 720
  else
    echo "SKIPPED video export: ffmpeg not found"
  fi
else
  echo "SKIPPED browser checks: Playwright not found (npm i playwright, or set PLAYWRIGHT_MODULE)"
fi

echo
echo "outputs in $OUT"
[ $fail = 0 ] && echo "ALL PASSED" || echo "SOME CHECKS FAILED"
exit $fail
