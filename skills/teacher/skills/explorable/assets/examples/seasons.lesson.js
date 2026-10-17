// Why seasons happen. A non-code explorable: one model (sun height, light per
// square metre and day length from latitude, date and axial tilt) drives the
// figure, the readouts, the checks and the film.
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_START = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
function dateOf(day) {
  const d = Math.round(day);
  let m = 11;
  while (MONTH_START[m] >= d) m -= 1;
  return `${d - MONTH_START[m]} ${MONTHS[m]}`;
}
const rad = (deg) => (deg * Math.PI) / 180;
const deg = (r) => (r * 180) / Math.PI;

function seasonsModel({ lat, day, tilt }) {
  // Solar declination: where the noon sun is overhead. Zero at the March equinox (day ~80).
  const decl = tilt * Math.sin((2 * Math.PI * (day - 80)) / 365);
  const elev = 90 - Math.abs(lat - decl); // noon sun height above the horizon
  const light = Math.max(0, Math.sin(rad(elev))); // share of overhead sunlight per square metre
  const x = -Math.tan(rad(lat)) * Math.tan(rad(decl));
  const hours = x <= -1 ? 24 : x >= 1 ? 0 : (2 * deg(Math.acos(x))) / 15;
  return { decl, elev, light, hours, spread: light > 0 ? 1 / light : Infinity };
}

window.LESSON = {
  id: "seasons-v1",
  title: "Why seasons happen",
  subtitle: "Tilt, not distance: the same sunlight spread over more or less ground.",
  subject: "Earth science",
  level: "first intuition to working model",
  params: {
    lat: { label: "Your latitude", min: -66, max: 66, step: 1, value: 40, fmt: (v) => `${Math.abs(Math.round(v))}°${v >= 0 ? "N" : "S"}` },
    day: { label: "Date", min: 1, max: 365, step: 1, value: 172, fmt: dateOf },
    tilt: { label: "Earth's tilt", min: 0, max: 40, step: 0.5, value: 23.5, unit: "°", decimals: 1 },
  },
  model: seasonsModel,
  readouts: (s, p) => [
    ["noon sun", `${s.elev.toFixed(0)}°`],
    ["light per m²", `${(100 * s.light).toFixed(0)}% of overhead`],
    ["daylight", `${s.hours.toFixed(1)} h`],
    ["sun overhead at", `${Math.abs(s.decl).toFixed(1)}°${s.decl >= 0 ? "N" : "S"}`],
  ],
  figure: {
    // Side by side when there's room; stacked (beam under the globe) on narrow screens.
    viewBox: (narrow) => (narrow ? "0 0 340 690" : "0 0 700 360"),
    label: (s, p) =>
      `On ${dateOf(p.day)} at ${Math.abs(p.lat)}°${p.lat >= 0 ? "N" : "S"} the noon sun is ${s.elev.toFixed(0)}° up, so a beam of sunlight is spread over ${s.light > 0 ? `${s.spread.toFixed(2)} times` : "no"} the ground it would cover overhead, and the day lasts ${s.hours.toFixed(1)} hours.`,
    draw(g, s, p, kit) {
      const { ink, seed } = kit;
      let { el, mark, hand } = kit;
      // Left: Earth from the side, sunlight arriving from the left.
      const cx = 200, cy = 180, r = 105;
      el("text", { x: 20, y: 30, class: "t-print", text: "SUNLIGHT →" });
      for (let y = 70; y <= 290; y += 44) el("line", { x1: 20, y1: y, x2: cx - Math.sqrt(Math.max(0, r * r - (y - cy) ** 2)), y2: y, class: "s-graphite", "stroke-dasharray": "4 5" });
      el("path", { d: `M${cx} ${cy - r} A${r} ${r} 0 0 1 ${cx} ${cy + r} Z`, class: "f-paper-2" }); // night side
      el("circle", { cx, cy, r, class: "s-ink" });
      const t = rad(s.decl);
      const pole = [cx - r * 1.25 * Math.sin(t), cy - r * 1.25 * Math.cos(t)];
      const south = [cx + r * 1.25 * Math.sin(t), cy + r * 1.25 * Math.cos(t)];
      el("line", { x1: south[0], y1: south[1], x2: pole[0], y2: pole[1], class: "s-ink", "stroke-dasharray": "6 4" });
      el("text", { x: pole[0] - 8, y: pole[1] - 6, class: "t-print", text: "N" });
      const eq = [cx - r * Math.cos(t), cy + r * Math.sin(t)];
      el("line", { x1: eq[0], y1: eq[1], x2: 2 * cx - eq[0], y2: 2 * cy - eq[1], class: "s-rule" });
      // The learner's place on the day side, at noon.
      const a = rad(p.lat - s.decl);
      const P = [cx - r * Math.cos(a), cy - r * Math.sin(a)];
      if (s.elev > 0) mark([ink.line([20, P[1]], [P[0] - 4, P[1]], { seed: seed("ray"), bow: 0.004, overshoot: 0 })], { tone: "blue" });
      const tx = Math.sin(a) * 34, ty = -Math.cos(a) * 34; // local horizon (tangent)
      el("line", { x1: P[0] - tx, y1: P[1] - ty, x2: P[0] + tx, y2: P[1] + ty, class: "s-ink" });
      mark([ink.loop(P[0], P[1], 11, 11, { seed: seed("you") })], { tone: "red" });
      hand(P[0] - 14, P[1] + (p.lat - s.decl > 0 ? -18 : 30), "you", { tone: "red", anchor: "end" });
      hand(cx, 336, `noon sun ${s.elev.toFixed(0)}° up`, { anchor: "middle" });

      // Right (or below, when narrow): one beam of the same width landing on the ground.
      ({ el, mark, hand } = kit.group(kit.narrow ? "translate(-372 330)" : null));
      const gy = 290, w = 56;
      el("text", { x: 410, y: 30, class: "t-print", text: "ONE BEAM, SAME WIDTH" });
      el("line", { x1: 400, y1: gy, x2: 690, y2: gy, class: "s-ink" });
      if (s.elev <= 0.5) {
        hand(545, 200, "no noon sun today", { tone: "red", anchor: "middle" });
        return;
      }
      const e = rad(s.elev);
      const L = Math.min(200, w / Math.sin(e));
      const gx = Math.min(545, 680 - L / 2); // a long patch slides right so the beam stays in its panel
      const ux = -Math.cos(e), uy = -Math.sin(e);
      const len = Math.min(230, (gx - L / 2 - 405) / Math.max(-ux, 0.05));
      for (const x0 of [gx - L / 2, gx + L / 2]) {
        el("line", { x1: x0, y1: gy, x2: x0 + ux * len, y2: gy + uy * len, class: "s-blue" });
      }
      el("rect", { x: gx - L / 2, y: gy - 3, width: L, height: 6, class: "f-hl" });
      mark([ink.line([gx - L / 2, gy + 12], [gx + L / 2, gy + 12], { seed: seed("patch"), bow: 0.01, tremor: 0.003 })], { tone: "graphite" });
      const spreadText = s.spread < 1.05 ? "light concentrated" : `spread over ${s.spread.toFixed(1)}× the ground`;
      hand(Math.min(gx, 545), gy + 40, spreadText, { tone: s.spread > 1.6 ? "red" : "blue", anchor: "middle" });
      // The angle at the ground.
      el("path", { d: `M${gx + L / 2 - 40} ${gy} A40 40 0 0 0 ${gx + L / 2 + ux * 40} ${gy + uy * 40}`, class: "s-red" });
      el("text", { x: gx + L / 2 - 58, y: gy - 10, class: "t-print", text: `${s.elev.toFixed(0)}°` });
    },
  },
  steps: [
    {
      title: "Same light, more ground",
      say: "<p>Picture one beam of sunlight, always the same width. When it comes straight down it lights a small patch brightly. Tilt it and the <strong>same light</strong> lands on a longer patch, so each square metre gets less.</p><p>Drag the date and watch the yellow patch where the beam lands.</p>",
      set: { lat: 40, day: 172, tilt: 23.5 },
      controls: ["day"],
      lookFor: "the yellow patch stretches as the noon sun drops",
      ask: { kind: "choice", q: "When the sun is lower in the sky, the same beam covers...", options: ["less ground", "the same ground", "more ground"], answer: 2, hint: "Move the date to December and compare the patch with June.", why: "A lower sun hits the ground at a shallow angle, so the beam's footprint gets longer. The patch length is the beam width divided by the sine of the sun's height." },
      note: "Same beam, lower sun: the light is spread thinner.",
      alts: [
        { label: "A torch on a table", say: "Shine a torch straight down: a small bright circle. Tip it over: a long dim oval. The torch didn't get weaker, its light got spread out." },
        { label: "With numbers", say: "A beam 1 m wide at 30° above the ground lands on 1 / sin 30° = 2 m of ground. Each square metre gets half the light it would get from straight overhead.", set: { day: 355 } },
      ],
    },
    {
      title: "Why the noon sun moves",
      say: "<p>Earth's axis is tilted about 23.5° and keeps pointing the same way in space all year. In June the north end leans toward the Sun, and in December it leans away. Watch the dashed axis on the left as you move the date.</p>",
      set: { lat: 40, day: 172, tilt: 23.5 },
      controls: ["day"],
      lookFor: "the place where the sun is overhead slides north and south",
      ask: { kind: "choice", q: "At 40°N, in which month is the noon sun highest?", options: ["March", "June", "September", "December"], answer: 1, hint: "Try each month with the slider and read the noon sun height.", why: "Around 21 June the north end of the axis leans most toward the Sun, so the overhead point is at 23.5°N and 40°N sees the sun 73.5° up at noon." },
      note: "The tilt moves the overhead sun between 23.5°N and 23.5°S.",
      alts: [{ label: "From the Sun's side", say: "Imagine standing on the Sun looking at Earth. In June you see more of the northern half; in December more of the southern half. The half you see more of is the one getting steeper sunlight." }],
    },
    {
      title: "It isn't distance",
      say: "<p>A common guess is that summer happens when Earth is closer to the Sun. But Earth is closest to the Sun in early January, in the middle of the northern winter.</p><p>Set your latitude to 40°S and look at December.</p>",
      set: { lat: -40, day: 355, tilt: 23.5 },
      controls: ["lat", "day"],
      ask: { kind: "choice", q: "If distance caused the seasons, what would be true?", options: ["Both hemispheres would have summer at the same time", "Summer would be longer in the north", "The tilt would change during the year"], answer: 0, why: "Distance changes affect the whole planet at once. But when it's summer in Sydney it's winter in Madrid. Only something that treats the hemispheres differently, the tilt, explains that." },
      note: "Opposite hemispheres, opposite seasons: distance can't do that.",
    },
    {
      title: "Switch the tilt off",
      say: "<p>Now break the planet. Set the tilt to 0° and run through the year.</p>",
      set: { lat: 40, day: 172, tilt: 0 },
      controls: ["tilt", "day"],
      lookFor: "the noon sun height stops changing",
      ask: { kind: "number", q: "With tilt 0°, by how many degrees does the noon sun height at 40°N change over the year?", answer: 0, tol: 0.5, unit: "°", decimals: 0, hint: "Keep tilt at 0 and read the noon sun height in June, then in December.", why: "With no tilt the overhead sun stays on the equator every day, so 40°N always sees it 50° up. No tilt, no seasons." },
      note: "No tilt, no seasons.",
    },
    {
      title: "Longer days add up",
      say: "<p>There's a second effect. In summer the sun is up for longer, so a steeper sun shines for more hours. Both push the same way.</p>",
      set: { lat: 40, day: 172, tilt: 23.5 },
      controls: ["lat", "day"],
      ask: { kind: "number", q: "About how many hours of daylight does 40°N get on 21 June?", answer: (p, s) => seasonsModel({ lat: 40, day: 172, tilt: 23.5 }).hours, tol: 0.6, unit: "h", decimals: 1, hint: "It's more than 12. Read the daylight readout with the date on 21 Jun.", why: "About 15 hours, against about 9 in late December. Steeper light for longer: that's why summer is warmer." },
      note: "Summer: steeper light and longer days.",
    },
  ],
  misconceptions: ["Seasons come from Earth's distance to the Sun.", "The tilt changes direction during the year.", "The equator has strong seasons."],
  deeper: [
    "Why is the hottest month usually July, not June? (seasonal lag)",
    "What happens at 70°N in December, and why?",
    "How would seasons work on Uranus, tilted 98°?",
  ],
  checks: [
    { name: "overhead sun gives full light", test: (m) => Math.abs(m({ lat: 0, day: 80, tilt: 23.5 }).light - 1) < 1e-9 },
    { name: "no tilt means the same noon sun all year", test: (m) => Math.abs(m({ lat: 40, day: 172, tilt: 0 }).elev - m({ lat: 40, day: 355, tilt: 0 }).elev) < 1e-9 },
    { name: "June days are longer than December days at 40N", test: (m) => m({ lat: 40, day: 172, tilt: 23.5 }).hours > m({ lat: 40, day: 355, tilt: 23.5 }).hours + 5 },
    { name: "hemispheres are mirror images", test: (m) => Math.abs(m({ lat: 40, day: 172, tilt: 23.5 }).hours - m({ lat: -40, day: 355, tilt: 23.5 }).hours) < 0.2 },
  ],
};
