#!/usr/bin/env bash
# Explicit setup for the ARM64 Actions job; never changes the global context.
set -euo pipefail
test "$(uname -m)" = aarch64
test "$(id -u)" -ne 0
docker --context default info --format '{{.OSType}} {{.Architecture}} cgroup={{.CgroupVersion}}'
python3 --version
node --version
# Cgroup-v2 files are asserted by existing actual controls; do not rewrite them.
python3 -m venv "$RUNNER_TEMP/teacher-regression"
CI_PY="$RUNNER_TEMP/teacher-regression/bin/python"
WHEELS="$RUNNER_TEMP/enrichment-image/wheels"
mkdir -p "$WHEELS" "$RUNNER_TEMP/enrichment-base"
"$CI_PY" -m pip download --only-binary=:all: --no-deps \
  --platform manylinux2014_aarch64 --platform manylinux_2_24_aarch64 \
  --platform manylinux_2_28_aarch64 --python-version 3.11 --implementation cp --abi cp311 \
  --dest "$WHEELS" requests==2.34.2 urllib3==2.6.3 certifi==2026.2.25 \
  charset-normalizer==3.4.4 idna==3.11 playwright==1.58.0 pyee==13.0.1 \
  greenlet==3.3.2 typing-extensions==4.15.0
"$CI_PY" - "$WHEELS" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1])
expected=json.loads(pathlib.Path('skills/transcript-pipeline/scripts/enrichment-wheels-arm64.json').read_text())
assert {p.name for p in root.iterdir()} == set(expected)
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in expected.items())
PY
# Same hash-verified CPython3.11/aarch64 wheels work in the host test venv.
"$CI_PY" -m pip install --no-index --no-deps "$WHEELS"/*.whl
"$CI_PY" -m pip install PyYAML==6.0.3
"$CI_PY" -c 'import requests,yaml;from playwright.sync_api import sync_playwright;import importlib.metadata as m;print({n:m.version(n) for n in ["requests","playwright","greenlet"]})'
export PLAYWRIGHT_BROWSERS_PATH="$RUNNER_TEMP/teacher-pw"
"$CI_PY" -m playwright install --with-deps chromium
npm install --prefix "$RUNNER_TEMP/teacher-node" --no-audit --no-fund --save-exact playwright@1.58.0
export PLAYWRIGHT_MODULE="$RUNNER_TEMP/teacher-node/node_modules/playwright"
# Save CI_PY and PLAYWRIGHT_BROWSERS_PATH in GITHUB_ENV across actual YAML steps.

# Match the locally exercised classic builder for local sha256 FROM references.
# Docker28 supports this; this backend is deprecated, not a long-term pin.
export DOCKER_BUILDKIT=0
docker --context default build --platform linux/arm64 --pull=false \
  -t teacher-code-sandbox:ci skills/teacher/skills/explorable/assets/sandbox
COURSE_BASE=$(docker --context default image inspect teacher-code-sandbox:ci --format '{{.Id}}')
docker --context default build --platform linux/arm64 --pull=false \
  --build-arg BASE_IMAGE="$COURSE_BASE" \
  -f skills/teacher/skills/course/scripts/Dockerfile.sandbox \
  -t teacher-course-browser:ci skills/teacher/skills/course/scripts
COURSE_IMAGE=$(docker --context default image inspect teacher-course-browser:ci --format '{{.Id}}')

docker --context default build --platform linux/arm64 --pull=false \
  -f skills/transcript-pipeline/scripts/Dockerfile.enrichment-base \
  -t teacher-enrichment-base:ci "$RUNNER_TEMP/enrichment-base"
ENRICHMENT_BASE=$(docker --context default image inspect teacher-enrichment-base:ci --format '{{.Id}}')
cp skills/transcript-pipeline/scripts/enrichment-wheels-arm64.json "$RUNNER_TEMP/enrichment-image/"
docker --context default build --platform linux/arm64 --pull=false --network=none \
  --build-arg BASE_IMAGE="$ENRICHMENT_BASE" \
  -f skills/transcript-pipeline/scripts/Dockerfile.enrichment \
  -t teacher-enrichment:ci "$RUNNER_TEMP/enrichment-image"
ENRICHMENT_IMAGE=$(docker --context default image inspect teacher-enrichment:ci --format '{{.Id}}')
for image in "$COURSE_BASE" "$COURSE_IMAGE" "$ENRICHMENT_IMAGE"; do
  [[ "$image" =~ ^sha256:[0-9a-f]{64}$ ]]
  test "$(docker --context default image inspect "$image" --format '{{.Architecture}}')" = arm64
done
export TEACHER_SANDBOX_IMAGE="$COURSE_BASE" TEACHER_SANDBOX_CONTEXT=default
export COURSE_SANDBOX_IMAGE="$COURSE_IMAGE" COURSE_SANDBOX_CONTEXT=default COURSE_SANDBOX_BROWSER=1
export ENRICHMENT_TEST_IMAGE="$ENRICHMENT_IMAGE" ENRICHMENT_TEST_CONTEXT=default
export TEACHER_BROWSER_TESTS=1

docker --context default build --platform linux/arm64 --pull=false --build-arg BROWSER_IMAGE="$COURSE_IMAGE" -f skills/teacher/skills/course/scripts/Dockerfile.media -t teacher-course-media:ci skills/teacher/skills/course/scripts
MEDIA_IMAGE=$(docker --context default image inspect teacher-course-media:ci --format '{{.Id}}')
[[ "$MEDIA_IMAGE" =~ ^sha256:[0-9a-f]{64}$ ]]
docker --context default image inspect "$COURSE_BASE" "$COURSE_IMAGE" "$ENRICHMENT_IMAGE" "$MEDIA_IMAGE" --format '{{.Id}} {{.Architecture}}'
for name in CI_PY PLAYWRIGHT_BROWSERS_PATH PLAYWRIGHT_MODULE TEACHER_SANDBOX_IMAGE TEACHER_SANDBOX_CONTEXT COURSE_SANDBOX_IMAGE COURSE_SANDBOX_CONTEXT COURSE_SANDBOX_BROWSER ENRICHMENT_TEST_IMAGE ENRICHMENT_TEST_CONTEXT TEACHER_BROWSER_TESTS MEDIA_IMAGE; do
  printf '%s=%s\n' "$name" "${!name}" >> "$GITHUB_ENV"
done
