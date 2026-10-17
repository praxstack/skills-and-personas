// Cards: the question card with a countdown ring, the title card, and a plain panel.
//
//   const q = new QuestionCard({position: [430, -150], width: 820});
//   w.hud.add(q.node);
//   yield* q.ask(1, 'What is simpler to count than stops?');
//   yield* q.countdown(line('q1').think);      // ring runs down for the think pause
//   yield* q.answer('Flights: at most k + 1');  // mint answer line under the question
//   yield* q.hide();
import {Circle, Gradient, Layout, Line, Node, Rect, Txt, type NodeProps, type RectProps} from '@motion-canvas/2d';
import {
  Vector2,
  all,
  createSignal,
  delay,
  easeInCubic,
  easeInOutCubic,
  easeOutBack,
  easeOutCubic,
  linear,
  waitFor,
  type ThreadGenerator,
} from '@motion-canvas/core';
import {C, F, S, alpha, glow, inkOf, shade} from './theme';
import {background} from './clock';

/** A raised panel: gradient fill, soft drop shadow, hairline border. */
export function panel(props: RectProps = {}): Rect {
  const h = typeof props.height === 'number' ? props.height : 400;
  return new Rect({
    radius: 24,
    fill: new Gradient({
      from: [0, -h / 2],
      to: [0, h / 2],
      stops: [
        {offset: 0, color: C.panelHi},
        {offset: 1, color: C.panel},
      ],
    }),
    stroke: C.border,
    lineWidth: 2,
    shadowColor: shade(0.62),
    shadowBlur: 46,
    shadowOffset: [0, 18],
    ...props,
  });
}

export class QuestionCard {
  public readonly node: Rect;
  private readonly kicker: Txt;
  private readonly text: Txt;
  private readonly ans: Txt;
  private readonly ring: Circle;
  private readonly ringBg: Circle;
  private readonly secs: Txt;
  private readonly left = createSignal(0);
  private readonly frac = createSignal(1);

  public constructor(props: NodeProps & {width?: number} = {}) {
    const {width = 820, ...rest} = props;
    this.kicker = new Txt({text: 'QUESTION', fontFamily: F.body, fontWeight: 700, fontSize: S.label, letterSpacing: 5, fill: inkOf(C.accent)});
    this.text = new Txt({text: '', fontFamily: F.display, fontWeight: 700, fontSize: 46, lineHeight: 58, fill: C.ink, textWrap: true, width: width - 220});
    this.ans = new Txt({text: '', fontFamily: F.body, fontWeight: 600, fontSize: 40, lineHeight: 50, fill: inkOf(C.good), textWrap: true, width: width - 80, opacity: 0});
    // layout: false on the ring's parts: inside the header row they would otherwise be laid out side by side
    // (squashed into ovals with the number beside them) instead of stacked on one centre
    this.ringBg = new Circle({layout: false, size: 104, stroke: alpha(C.ink, 0.12), lineWidth: 9});
    this.ring = new Circle({
      layout: false,
      size: 104,
      stroke: C.accent,
      lineWidth: 9,
      lineCap: 'round',
      startAngle: -90,
      endAngle: () => -90 + 360 * this.frac(),
      shadowColor: glow(C.accent),
      shadowBlur: 14,
    });
    this.secs = new Txt({
      layout: false,
      text: () => String(Math.max(0, Math.ceil(this.left() - 1e-6))),
      fontFamily: F.mono,
      fontWeight: 700,
      fontSize: 40,
      fill: C.ink,
      letterSpacing: 0.01,
    });
    const timer = new Node({opacity: 0, children: [this.ringBg, this.ring, this.secs]});
    this.timer = timer;
    const head = new Layout({
      direction: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      width: width - 80,
      children: [
        new Layout({direction: 'column', gap: 14, children: [this.kicker, this.text]}),
        new Layout({width: 120, height: 120, alignItems: 'center', justifyContent: 'center', children: [timer]}),
      ],
    });
    this.node = panel({
      layout: true,
      direction: 'column',
      gap: 22,
      padding: [32, 40],
      width,
      opacity: 0,
      ...rest,
      children: [head, this.ans],
    });
    // accent bar on the left edge
    this.node.add(new Rect({layout: false, width: 8, height: () => this.node.height() - 48, x: () => -this.node.width() / 2 + 4, radius: 4, fill: C.accent}));
  }
  private readonly timer: Node;

  /** Show the card with question n (or swap the question if the card is up). */
  public *ask(n: number | string, question: string, d = 0.5): ThreadGenerator {
    this.frac(1);
    if (this.node.opacity() < 0.5) {
      this.kicker.text(`QUESTION ${n}`);
      this.text.text(question);
      this.ans.opacity(0);
      this.ans.text('');
      const y = this.node.y();
      this.node.y(y + 40);
      this.node.scale(0.96);
      yield* all(this.node.opacity(1, d, easeOutCubic), this.node.y(y, d, easeOutCubic), this.node.scale(1, d, easeOutBack));
    } else {
      yield* all(this.text.opacity(0, 0.15), this.kicker.opacity(0, 0.15), this.ans.opacity(0, 0.15), this.timer.opacity(0, 0.15));
      this.kicker.text(`QUESTION ${n}`);
      this.text.text(question);
      this.ans.text('');
      yield* all(this.text.opacity(1, 0.3), this.kicker.opacity(1, 0.3), this.node.stroke(C.accent, 0.15));
      yield* this.node.stroke(C.border, 0.6);
    }
  }
  /** Run the countdown ring for `seconds` (the think pause), then hide the ring. */
  public *countdown(seconds: number): ThreadGenerator {
    this.left(seconds);
    this.frac(1);
    yield* all(this.timer.opacity(1, 0.15), this.frac(0, seconds, linear), this.left(0, seconds, linear));
    background(this.timer.opacity(0, 0.2)); // fades while the answer starts
  }
  /** The answer appears under the question, in the "valid" colour. */
  public *answer(text: string, color: string = C.good, d = 0.45): ThreadGenerator {
    this.ans.fill(inkOf(color));
    this.ans.text(text);
    yield* all(this.ans.opacity(1, d), this.node.stroke(color, 0.2));
    yield* this.node.stroke(C.border, 0.6);
  }
  public *hide(d = 0.35): ThreadGenerator {
    yield* all(this.node.opacity(0, d), this.node.y(this.node.y() - 30, d, easeInCubic));
    this.node.y(this.node.y() + 30);
  }
}

/**
 * Title card for the intro: kicker, two title lines (one word in the accent colour), and a plane that flies
 * a dashed arc under it.
 *   const t = new TitleCard({kicker: 'LEETCODE 787 · GRAPHS', lines: ['Cheapest Flights', 'Within K Stops'], accent: 'K'});
 *   w.hud.add(t.node); yield* t.in(); ... yield* t.out();
 */
export class TitleCard {
  public readonly node = new Node({});
  private readonly parts: Node[] = [];
  private readonly arc: Line;
  private readonly arcP = createSignal(0);
  private readonly plane: Line;

  public constructor(o: {kicker: string; lines: string[]; accent?: string; subtitle?: string; y?: number}) {
    const y0 = o.y ?? -40;
    const kicker = new Txt({text: o.kicker, y: y0 - 190, fontFamily: F.body, fontWeight: 700, fontSize: S.label, letterSpacing: 7, fill: inkOf(C.accent), opacity: 0});
    this.node.add(kicker);
    this.parts.push(kicker);
    o.lines.forEach((ln, i) => {
      const t = new Txt({y: y0 - 70 + i * 132, fontFamily: F.display, fontWeight: 800, fontSize: S.hero, fill: C.ink, letterSpacing: -2, opacity: 0, shadowColor: shade(0.6), shadowBlur: 30, shadowOffset: [0, 10]});
      if (o.accent && ln.includes(o.accent)) {
        const [a, b] = ln.split(o.accent);
        t.add(new Txt({text: a}));
        t.add(new Txt({text: o.accent, fill: inkOf(C.accent)}));
        t.add(new Txt({text: b}));
      } else t.text(ln);
      this.node.add(t);
      this.parts.push(t);
    });
    if (o.subtitle) {
      const s = new Txt({text: o.subtitle, y: y0 - 70 + o.lines.length * 132 + 10, fontFamily: F.body, fontWeight: 400, fontSize: 34, fill: C.muted, opacity: 0});
      this.node.add(s);
      this.parts.push(s);
    }
    const pts = [new Vector2(-860, 330), new Vector2(-300, 170), new Vector2(300, 170), new Vector2(860, 330)];
    this.arc = new Line({points: pts, radius: 600, stroke: alpha(C.ink, 0.35), lineWidth: 3, lineDash: [14, 16], end: () => this.arcP(), opacity: 0});
    const where = () => this.arc.getPointAtPercentage(Math.max(0.001, Math.min(0.999, this.arcP())));
    this.plane = new Line({
      points: [
        [24, 0], [9, -4], [-2, -20], [-9, -20], [-3, -4], [-15, -4], [-20, -11],
        [-25, -11], [-21, 0], [-25, 11], [-20, 11], [-15, 4], [-3, 4], [-9, 20],
        [-2, 20], [9, 4],
      ],
      closed: true,
      fill: C.accent,
      scale: 1.6,
      shadowColor: glow(C.accent),
      shadowBlur: 24,
      position: () => where().position,
      rotation: () => where().tangent.degrees,
      opacity: () => (this.arcP() > 0.002 && this.arcP() < 0.998 ? 1 : 0),
    });
    this.node.add(this.arc);
    this.node.add(this.plane);
  }

  /** Title lines rise in one after another while the plane flies the arc for `arc` seconds. */
  public *in(d = 0.7, arc = 2.4): ThreadGenerator {
    this.arc.opacity(1);
    yield* all(
      ...this.parts.map((p, i) => {
        const y = p.y();
        p.y(y + 40);
        return delay(i * 0.12, all(p.opacity(1, d, easeOutCubic), p.y(y, d + 0.1, easeOutCubic)));
      }),
      delay(0.3, this.arcP(1, arc, easeInOutCubic)),
    );
  }
  public *out(d = 0.6): ThreadGenerator {
    yield* all(
      ...this.parts.map((p, i) => delay(i * 0.05, all(p.opacity(0, d * 0.8), p.y(p.y() - 80, d, easeInCubic)))),
      this.arc.opacity(0, d * 0.6),
    );
    this.node.remove();
  }
  /** wait helper so callers can hold the card */
  public *hold(s: number) {
    yield* waitFor(s);
  }
}
