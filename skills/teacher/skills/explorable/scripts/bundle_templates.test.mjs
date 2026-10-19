import test from "node:test";
import assert from "node:assert/strict";

import { page, safeSourceUrl, sources } from "./bundle_templates.mjs";

test("source URLs allow only web schemes", () => {
  assert.equal(safeSourceUrl("javascript:alert(1)"), null);
  assert.equal(safeSourceUrl("data:text/html,<script>alert(1)</script>"), null);
  assert.equal(safeSourceUrl("file:///etc/passwd"), null);
  assert.equal(safeSourceUrl("https://example.com/a"), "https://example.com/a");
});

test("unsafe sources render as inert text", () => {
  const html = sources({ title: "T", subject: "S", sources: [{ title: "bad", url: "javascript:alert(1)" }] });
  assert.match(html, />bad</);
  assert.doesNotMatch(html, /href="javascript:/);
});

test("generated pages include a restrictive CSP", () => {
  const html = page({ title: "T", subtitle: "", subject: "", level: "", lang: "en" }, "Test", "<p>body</p>");
  assert.match(html, /Content-Security-Policy/);
  assert.match(html, /connect-src 'none'/);
  assert.match(html, /object-src 'none'/);
});
