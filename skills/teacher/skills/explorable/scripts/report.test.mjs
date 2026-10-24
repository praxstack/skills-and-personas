import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Exercise the actual teacher-facing formatter without loading the DOM engine.
const source = readFileSync(new URL('../assets/engine/explorable.js', import.meta.url), 'utf8');
const formatter = source.match(/function report\(choice, text\) \{[\s\S]*?\n\}/)[0];
function report(attempts, tried = {}) {
  return vm.runInNewContext(`${formatter}\nreport('finished', '')`, {
    L:{title:'Synthetic',steps:[{title:'Question'}]}, PRACTICE:false, notesBox:null,
    S:{done:new Set([0]),attempts,tried,explained:{},curious:[]},
  });
}

test('unattempted absent and empty answers never claim correctness', () => {
  for(const attempts of [{},{0:[]}]) {
    const text=report(attempts,{0:[]});
    assert.doesNotMatch(text,/right first time|^- Question:/m);
    assert.match(text,/viewing is not proof of learning/);
  }
});
test('unattempted question can still report an actual alternate explanation', () => {
  const text=report({0:[]},{0:['Torch']});
  assert.match(text,/- Question: tried other explanations: Torch/);
  assert.doesNotMatch(text,/right first time/);
});
test('actually correct first attempt is reported as right first time', () => {
  assert.match(report({0:[{given:'correct',right:true}]}),/- Question: right first time/);
});
test('a correct answer after a miss retains its miss history', () => {
  const text=report({0:[{given:'wrong',right:false},{given:'correct',right:true}]});
  assert.match(text,/- Question: 1 miss/);
  assert.doesNotMatch(text,/right first time/);
});
test('asking to be shown is not reported as a correct answer', () => {
  const text=report({0:[{given:null,right:false,asked:true}]});
  assert.match(text,/1 miss, asked to be shown/);
  assert.doesNotMatch(text,/right first time/);
});
