import test from "node:test";
import assert from "node:assert/strict";

import { page, readableCaptionCues, sceneIndexAtTime, safeSourceUrl, sources } from "./bundle_templates.mjs";

const opening={startTime:1,endTime:2,text:'Opening'},closing={startTime:4,endTime:5,text:'Closing'};
test('readable captions preserve native cue intervals and earlier gaps',()=>{
 assert.deepEqual(readableCaptionCues([opening,closing],0.5),[]);
 assert.deepEqual(readableCaptionCues([opening,closing],1),[opening]);
 assert.deepEqual(readableCaptionCues([opening,closing],2.5),[]);
 assert.deepEqual(readableCaptionCues([opening,closing],4.5),[closing]);
});
test('terminal still retains actual final cue and seeking back clears it',()=>{
 assert.deepEqual(readableCaptionCues([opening,closing],5),[closing]);
 assert.deepEqual(readableCaptionCues([opening,closing],8),[closing]);
 assert.deepEqual(readableCaptionCues([opening,closing],0),[]);
 assert.deepEqual(readableCaptionCues([opening,closing],3),[]);
});
test('final means latest ending cue, including overlapping tracks',()=>{
 const long={startTime:1,endTime:7,text:'Long'},short={startTime:4,endTime:5,text:'Short'};
 assert.deepEqual(readableCaptionCues([long,short],4.5),[long,short]);
 assert.deepEqual(readableCaptionCues([long,short],6),[long]);
 assert.deepEqual(readableCaptionCues([long,short],8),[long]);
});
test('unloaded or empty tracks never invent readable words',()=>{
 assert.deepEqual(readableCaptionCues(null,8),[]);
 assert.deepEqual(readableCaptionCues([],8),[]);
});

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


test('chapter selection shares whole-microsecond media boundaries',()=>{
 const scenes=[{start:0},{start:1.23456789},{start:4.3456789123}];
 assert.equal(sceneIndexAtTime(scenes,1.234566),0);
 assert.equal(sceneIndexAtTime(scenes,1.234567),1);
 assert.equal(sceneIndexAtTime(scenes,1.23456789),1);
 assert.equal(sceneIndexAtTime(scenes,4.345677),1);
 assert.equal(sceneIndexAtTime(scenes,4.345678),2);
 assert.equal(sceneIndexAtTime(scenes,0.5),0);
 assert.deepEqual(scenes,[{start:0},{start:1.23456789},{start:4.3456789123}]);
});
test('exact microsecond boundaries do not move into the preceding microsecond',()=>{
 const scenes=[{start:0},{start:1.000001}];
 assert.equal(sceneIndexAtTime(scenes,1),0);
 assert.equal(sceneIndexAtTime(scenes,1.000001),1);
});
