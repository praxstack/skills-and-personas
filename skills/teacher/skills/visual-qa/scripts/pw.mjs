// Find Playwright and a Chromium wherever this host keeps them.
// Order: a normal import, then node_modules under the current directory,
// then PLAYWRIGHT_MODULE (a path to the package). For the browser:
// CHROMIUM_PATH, then /opt/pw-browsers/chromium, then Playwright's own.

import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const pick = (mod) => (mod.chromium ? mod : mod.default);

export async function loadPlaywright() {
  try {
    return pick(await import("playwright"));
  } catch {
    /* not resolvable from this file */
  }
  const tries = [process.env.PLAYWRIGHT_MODULE, join(process.cwd(), "node_modules", "playwright")].filter(Boolean);
  for (const spot of tries) {
    try {
      const require = createRequire(join(spot, "..", "noop.js"));
      return pick(await import(pathToFileURL(require.resolve("playwright")).href));
    } catch {
      /* next */
    }
  }
  console.error("Playwright not found. Run `npm i playwright` here (or set PLAYWRIGHT_MODULE=/path/to/node_modules/playwright).");
  process.exit(2);
}

export async function launch(chromium) {
  for (const executablePath of [process.env.CHROMIUM_PATH, "/opt/pw-browsers/chromium"].filter(Boolean)) {
    try {
      return await chromium.launch({ executablePath });
    } catch {
      /* next */
    }
  }
  return chromium.launch();
}
