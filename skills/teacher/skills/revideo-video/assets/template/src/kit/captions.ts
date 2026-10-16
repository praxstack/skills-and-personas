// Caption band: the bottom 180 px. Shows the current line's `cap` (wraps to two lines), fed by the timing.
// The scrim keeps captions readable over anything; the subject never goes below STAGE_BOTTOM.
import {Img, Node, Rect, Txt} from '@revideo/2d';
import {scrimTex} from './textures';
import {all, easeOutCubic, ThreadGenerator} from '@revideo/core';
import {C, F, H, S, W} from './theme';
import {at, LINES} from './time';

export class Captions {
  readonly root = new Node({});
  /** Between the scrim and the caption text: lower thirds go here, so the scrim never darkens them. */
  readonly lower = new Node({});
  readonly box: Rect;
  readonly txt: Txt;
  private shown = false;
  constructor(parent: Node) {
    parent.add(this.root);
    this.root.add(new Img({src: scrimTex(W, 300), y: H / 2 - 150, width: W, height: 300}));
    this.root.add(this.lower);
    this.box = new Rect({layout: true, y: H / 2 - 90, opacity: 0, alignItems: 'center', justifyContent: 'center'});
    this.txt = new Txt({
      text: '', fontFamily: F.text, fontWeight: 500, fontSize: S.caption, lineHeight: 54, fill: C.ink,
      textWrap: true, maxWidth: 1560, textAlign: 'center',
      shadowColor: C.captionShadow, shadowBlur: 12, shadowOffset: [0, 3],
    });
    this.box.add(this.txt);
    this.root.add(this.box);
  }
  *show(text: string): ThreadGenerator {
    if (this.shown) yield* this.box.opacity(0, 0.12);
    this.txt.text(text);
    this.box.y(H / 2 - 82);
    yield* all(this.box.opacity(1, 0.22, easeOutCubic), this.box.y(H / 2 - 90, 0.28, easeOutCubic));
    this.shown = true;
  }
  *hide(d = 0.25): ThreadGenerator {
    if (!this.shown) return;
    yield* this.box.opacity(0, d);
    this.shown = false;
  }
}

/** Background track: every line's caption appears just before its voice, and clears at chapter ends. */
export function* captionTrack(c: Captions): ThreadGenerator {
  for (let i = 0; i < LINES.length; i++) {
    const l = LINES[i], next = LINES[i + 1];
    yield* at(Math.max(0, l.voiceAt - 0.15));
    yield* c.show(l.cap);
    if (!next || next.chapter !== l.chapter) {
      yield* at(l.end - 0.3);
      yield* c.hide();
    }
  }
}
