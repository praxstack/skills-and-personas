// Headless render harness (do not edit for a new film).
//
// Loads the Motion Canvas project with the same Renderer class the editor's Render button uses, and draws
// any frame on demand. It implements the capture.mjs page contract, so the shared capturer handles
// segments, resume, the time budget, stills and the benchmark:
//
//   window.READY             resolves when fonts, scenes and the timeline are ready
//   window.TOTAL             film length in seconds (= TIMING.total)
//   window.renderFrame(t)    draw frame round(t * fps) into the canvas
//   window.CAPTURE_SELECTOR  '#mc' (the stage's final buffer)
//
// Frames are produced exactly like the editor's renderer (checked pixel-identical against its image-sequence
// export): reset, seek(first frame), then progress() one frame at a time. Seeking backwards replays the
// scene from frame 0 without drawing (fast).
// URL options: ?scale=0.5 renders at half resolution (drafts).
import {PlaybackState, Renderer, Vector2} from '@motion-canvas/core';
import project from './project?project';
import {TIMING} from './timing';

declare global {
  interface Window {
    READY: Promise<void>;
    TOTAL: number;
    renderFrame: (t: number) => Promise<void>;
    CAPTURE_SELECTOR: string;
    MC: {fps: number; frames: number; sceneFrames: number; frame: () => number};
  }
}

const params = new URLSearchParams(location.search);
const scale = Number(params.get('scale') ?? 1);
const fps = TIMING.fps;

// Errors from scene code go to the project's logger; surface them where capture.mjs prints them.
project.logger.onLogged.subscribe(entry => {
  const msg = typeof entry.message === 'string' ? entry.message : JSON.stringify(entry.message);
  if (entry.level === 'error') console.error(`[motion-canvas] ${msg}${entry.stack ? '\n' + entry.stack : ''}`);
  else if (entry.level === 'warn') console.error(`[motion-canvas warn] ${msg}`);
});

// The Renderer builds the scenes exactly as the editor's export does; we drive its playback ourselves.
const renderer = new Renderer(project) as any;
const playback = renderer.playback;
const stage = renderer.stage;

async function setup() {
  await document.fonts.ready;
  const settings = {
    ...project.meta.getFullRenderingSettings(),
    fps,
    size: new Vector2(TIMING.width, TIMING.height),
    resolutionScale: scale,
    colorSpace: 'srgb',
  };
  stage.configure(settings);
  playback.fps = fps;
  playback.state = PlaybackState.Rendering;
  await renderer.reloadScenes(settings);
  await playback.recalculate();
  await playback.reset();
  await playback.seek(0);
  const canvas: HTMLCanvasElement = stage.finalBuffer;
  canvas.id = 'mc';
  canvas.style.width = '100vw';
  document.body.appendChild(canvas);
  const sceneFrames = playback.duration;
  const frames = Math.round(TIMING.total * fps);
  if (Math.abs(sceneFrames - frames) > 2) {
    console.error(
      `[timing] the scene lasts ${(sceneFrames / fps).toFixed(2)} s but TIMING.total is ${TIMING.total.toFixed(2)} s. ` +
        'The film must end with `yield* waitUntilTime(TIMING.total)` and no animation may run past it.',
    );
  }
  window.MC = {fps, frames, sceneFrames, frame: () => playback.frame};
}

let queue: Promise<void> = Promise.resolve();
async function draw(t: number) {
  const f = Math.max(0, Math.round(t * fps));
  if (f === playback.frame + 1) await playback.progress();
  else if (f !== playback.frame) await playback.seek(f);
  await stage.render(playback.currentScene, playback.previousScene);
}

window.TOTAL = TIMING.total;
window.CAPTURE_SELECTOR = '#mc';
window.READY = setup();
window.renderFrame = (t: number) => (queue = queue.then(() => draw(t)));
