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

// PR1 4367933993/4367933995: portable export regressions.
test('native caption source contains the actual VTT before any script runs', async()=>{
 const {videoLesson}=await import('./bundle_templates.mjs');
 const vtt='WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nπ < 2 & 3\n';
 const data={title:'Caption',sources:[],video:{captions:vtt,scenes:[]}};
 const html=videoLesson(data),track=html.match(/<track\b[^>]+>/)[0];
 assert.match(track,/\bdefault\b/);
 const uri=track.match(/\bsrc="([^"]+)"/)[1];
 assert.equal(decodeURIComponent(uri.split(',').slice(1).join(',')),vtt);
 assert.match(uri,/^data:text\/vtt;charset=utf-8,/);
 assert.match(html,/track.src=URL.createObjectURL/);
 assert.match(html,/connect-src 'none'/);
});
test('static export retains every live code language and the JavaScript alias as text', async()=>{
 const {staticLesson}=await import('./bundle_templates.mjs');
 const code=Object.fromEntries(['cpp','python','js','javascript','java','go','rust'].map(k=>[k,k+' <b>example</b>']));
 const html=staticLesson({title:'Code',sources:[],steps:[],misconceptions:[],deeper:[],code});
 for(const lang of Object.keys(code))assert.ok(html.includes(`${lang} &lt;b&gt;example&lt;/b&gt;`));
 assert.doesNotMatch(html,/<b>example<\/b>/);
});

test('poster source preparation shares the HTTP/HTTPS allowlist', async()=>{
 const {createPoster}=await import('./bundle_poster.mjs');
 const sources=['javascript:localMarker()','data:text/html,marker','file:///marker','https://example.invalid/a?x=1&y=2','http://example.invalid/a'].map(url=>({title:'Reference',url}));
 const refs=await createPoster({evaluate:async(_fn,args)=>args.refs},{sources},{sources:[]});
 assert.deepEqual(refs.map(r=>r.posterHref),[null,null,null,sources[3].url,sources[4].url]);
 assert.equal(refs[0].url,sources[0].url,'provenance text is retained');
});
