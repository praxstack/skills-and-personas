const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "../..");
const pages = [
  "STATUS.html",
  "SKILL.html",
  "evidence/forward/outputs/lesson-attempt-before-transfer-answer.html",
  "evidence/forward/outputs/practical-executable-learning.html",
  "runtime/prax-visual-lab/dist/index.html",
];
const executablePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const contentTypes = { ".css": "text/css", ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript" };

(async () => {
  const server = http.createServer(async (request, response) => {
    try {
      const pathname = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
      if (pathname === "/favicon.ico") { response.statusCode = 204; response.end(); return; }
      const target = path.resolve(root, `.${pathname}`);
      assert(target.startsWith(`${root}${path.sep}`), "browser inspection path escaped root");
      response.setHeader("Content-Type", contentTypes[path.extname(target)] || "application/octet-stream");
      response.end(await fs.readFile(target));
    } catch (error) {
      response.statusCode = 404;
      response.end(String(error.message));
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}/`;
  const browser = await chromium.launch({ executablePath, headless: true });
  try {
    for (const relative of pages) {
      for (const viewport of [{ width: 1280, height: 900 }, { width: 320, height: 720 }]) {
        const context = await browser.newContext({ viewport });
        const page = await context.newPage();
        const errors = [];
        page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
        page.on("pageerror", (error) => errors.push(error.message));
        await page.goto(new URL(relative, origin).href);
        assert.equal(await page.locator("h1").count(), 1, `${relative}: expected one h1`);
        assert((await page.locator("body").innerText()).trim().length > 100, `${relative}: empty body`);
        assert((await page.locator("body").ariaSnapshot()).includes("heading"), `${relative}: no heading in accessibility tree`);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        assert(overflow <= 1, `${relative}: ${viewport.width}px viewport overflows by ${overflow}px`);
        if (relative === "runtime/prax-visual-lab/dist/index.html") {
          await page.locator("prax-parameter-lab input").fill("0.5");
          const comparison = await page.locator("prax-compare-views table").innerText();
          assert(comparison.includes("0.5"), `${relative}: parameter change did not update comparison`);
          const receipt = JSON.parse(await page.locator("prax-receipt-panel textarea").inputValue());
          assert.equal(receipt.observations.rounding_boundary, 0.5, `${relative}: parameter change missing from receipt`);
        }
        assert.deepEqual(errors, [], `${relative}: browser errors`);
        await context.close();
      }
    }
    process.stdout.write(JSON.stringify({ browser: await browser.version(), pages, status: "passed", viewports: [1280, 320] }));
  } finally {
    await browser.close();
    server.close();
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
