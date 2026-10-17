// The film: one Motion Canvas scene that runs the chapters in order on one persistent world.
// A new film edits this file's chapter list and the chapter files; the kit stays as it is.
import {makeScene2D} from '@motion-canvas/2d';
import {Chrome, Graph, InputPanel, TOTAL, createWorld, waitUntilTime} from '../kit';
import {EDGES, INPUT, NODES, SHOW} from './data';
import type {Film} from './film-context';
import {intro} from './ch0-intro';
import {problem} from './ch1-problem';
import {brute} from './ch2-brute';
import {intuition} from './ch3-intuition';
import {approaches} from './ch4-approaches';
import {codeAndDryRun} from './ch5-code';

export default makeScene2D(function* (view) {
  const w = createWorld(view);
  const g = new Graph({nodes: NODES, edges: EDGES, radius: 58});
  w.world.add(g.root);
  const input = new InputPanel({position: [0, -297], rows: INPUT, title: 'INPUT  ·  EXAMPLE 1'}); // top edge on FRAME.top
  w.hud.add(input.node);
  const chrome = new Chrome(w, {show: SHOW});
  const f: Film = {w, g, cam: w.camera, input, chrome};

  yield w.run(); // film clock, camera drift, grain
  yield chrome.run(); // captions + chapter cards from timing.ts

  yield* intro(f);
  yield* problem(f);
  yield* brute(f);
  yield* intuition(f);
  yield* approaches(f);
  yield* codeAndDryRun(f);

  yield* waitUntilTime(TOTAL, 'end of film'); // the film lasts exactly TIMING.total
});
