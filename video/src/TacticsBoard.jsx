import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, HEAD, BODY } from "./theme";

// Tactical analysis board in 3D, built from the REAL starting line-ups (FotMob positions).
// A moving camera (iso / top / low, optional focus on the lit players), big two-line text on the left,
// glowing zones, pulsing rings, a line joining a unit, and dashed arrows to REAL shot spots.
// visual: {type:"tactics_board", team:"home"|"away"|"both", kicker, title,
//          steps:[{from, side, shirts:[..], kicker, label, camera:"iso"|"top"|"low", focus:bool,
//                  zone:bool, link:bool, tone:"gold"|"warn", arrows:[{shirt, to:"shot:<minute>"}]}]}
const GOLD = C.accent, GREY = "#9ca3af", WARN = "#FF7A00";
const VIEWS = { iso: { rx: 48, s: 0.86 }, top: { rx: 6, s: 0.9 }, low: { rx: 60, s: 1.02 } };

const Puck = ({ x, y, n, col, lit, dim, size, ring, f }) => (
  <>
    {lit ? [0, 20].map((o) => {
      const t = ((f + o) % 40) / 40;
      return <div key={o} style={{ position: "absolute", left: x - size, top: y - size, width: size * 2, height: size * 2,
                                   borderRadius: "50%", border: `3px solid ${ring}`, opacity: 0.8 * (1 - t),
                                   transform: `scale(${0.6 + t * 0.9})` }} />;
    }) : null}
    <div style={{ position: "absolute", left: x - size / 2, top: y - size / 2, width: size, height: size,
                  borderRadius: "50%", background: col, opacity: dim ? 0.3 : 1,
                  boxShadow: lit ? `0 0 ${size * 0.7}px ${ring}, 0 0 0 ${size * 0.08}px #fff` : "0 4px 8px rgba(0,0,0,0.5)",
                  transform: `scale(${lit ? 1.15 : 1})`, display: "flex", alignItems: "center", justifyContent: "center",
                  fontFamily: BODY, fontWeight: 900, fontSize: size * 0.42, color: "#0b1410" }}>{n}</div>
  </>
);

export const TacticsBoard = ({ visual, props }) => {
  const f = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const vertical = height > width;
  const lu = props.lineups || {};
  const W = vertical ? 900 : 1180, H = vertical ? 1250 : 720;
  const sides = visual.team === "both" ? ["home", "away"] : [visual.team || "home"];
  const all = visual.steps || [];
  const done = all.filter((s) => f >= (s.from || 0));
  const cur = done[done.length - 1];
  const prev = done[done.length - 2];
  const side0 = cur?.side || sides[0];
  const litSet = new Set((cur?.shirts || []).map((n) => `${side0}:${n}`));
  const warn = cur?.tone === "warn";
  const ring = warn ? WARN : GOLD;

  const place = (side, p) => {
    const d = sides.length === 1 ? p.x : side === "home" ? p.x * 0.5 : 1 - p.x * 0.5;
    const across = side === "home" ? p.y : 1 - p.y;
    return vertical ? { x: across * W, y: (1 - d) * H } : { x: d * W, y: across * H };
  };
  // a real shot spot (FotMob shot y is mirrored against the line-ups), for the attacking side
  const shotSpot = (side, minute) => {
    const s = (props.shots || []).find((q) => q.side === side && Math.abs((q.min ?? q.minute ?? -99) - minute) <= 1);
    if (!s) return null;
    return place(side, { x: s.x, y: 1 - s.y });
  };
  const byShirt = (side, n) => (lu[side]?.starters || []).find((p) => String(p.shirt) === String(n));
  const litPts = (cur?.shirts || []).map((n) => byShirt(side0, n)).filter(Boolean).map((p) => place(side0, p));

  // camera: spring from the previous step's view to this one
  const k = cur ? spring({ frame: f - cur.from, fps: 30, config: { damping: 18 } }) : 1;
  const vA = VIEWS[prev?.camera] || VIEWS.iso, vB = VIEWS[cur?.camera] || VIEWS.iso;
  const centre = (st, pts) => (st?.focus && pts.length
    ? { x: pts.reduce((a, b) => a + b.x, 0) / pts.length, y: pts.reduce((a, b) => a + b.y, 0) / pts.length }
    : { x: W / 2, y: H / 2 });
  const prevPts = (prev?.shirts || []).map((n) => byShirt(prev.side || sides[0], n)).filter(Boolean)
    .map((p) => place(prev.side || sides[0], p));
  const cA = centre(prev, prevPts), cB = centre(cur, litPts);
  const zoomA = vA.s * (prev?.focus ? 1.12 : 1), zoomB = vB.s * (cur?.focus ? 1.12 : 1);
  const rx = interpolate(k, [0, 1], [vA.rx, vB.rx]);
  const sc = interpolate(k, [0, 1], [zoomA, zoomB]);
  const tx = interpolate(k, [0, 1], [W / 2 - cA.x, W / 2 - cB.x]);
  const ty = interpolate(k, [0, 1], [H / 2 - cA.y, H / 2 - cB.y]);
  const intro = spring({ frame: f, fps: 30, config: { damping: 20 } });

  const size = vertical ? 60 : 50;
  const pad = size;
  const box = (pts) => ({
    x: Math.min(...pts.map((p) => p.x)) - pad, y: Math.min(...pts.map((p) => p.y)) - pad,
    w: Math.max(...pts.map((p) => p.x)) - Math.min(...pts.map((p) => p.x)) + 2 * pad,
    h: Math.max(...pts.map((p) => p.y)) - Math.min(...pts.map((p) => p.y)) + 2 * pad });
  const gaps = litPts.slice(1).map((p, i) => Math.hypot(p.x - litPts[i].x, p.y - litPts[i].y));
  const compact = gaps.every((g) => g < (vertical ? W : H) * 0.38);
  const zones = cur?.zone && litPts.length ? (compact ? [box(litPts)] : litPts.map((p) => box([p]))) : [];
  const arrows = (cur?.arrows || []).map((a) => {
    const pl = byShirt(a.side || side0, a.shirt);
    const end = typeof a.to === "string" && a.to.startsWith("shot:") ? shotSpot(a.side || side0, Number(a.to.slice(5))) : null;
    return pl && end ? { s: place(a.side || side0, pl), e: end } : null;
  }).filter(Boolean);
  const draw = cur ? interpolate(f - cur.from, [6, 30], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  const txt = cur ? spring({ frame: f - cur.from, fps: 30, config: { damping: 14 } }) : intro;
  const kicker = cur?.kicker || visual.kicker || (sides.length === 2 ? "THE LINE-UPS" : (lu[sides[0]]?.team || "").toUpperCase());
  const label = cur?.label || visual.title || sides.map((s) => lu[s]?.formation).join("  v  ");

  const Text = (
    <div style={vertical
      ? { position: "absolute", top: 150, left: 60, right: 60, zIndex: 3 }
      : { position: "absolute", left: 90, top: 0, bottom: 0, width: 560, display: "flex", flexDirection: "column",
          justifyContent: "center", zIndex: 3 }}>
      <div key={`k${cur?.from}`} style={{ fontFamily: BODY, fontWeight: 800, letterSpacing: 5, fontSize: vertical ? 34 : 30,
                    color: "#fff", opacity: txt, transform: `translateY(${(1 - txt) * 20}px)` }}>{String(kicker).toUpperCase()}</div>
      <div key={`l${cur?.from}`} style={{ fontFamily: HEAD, fontSize: vertical ? 110 : 104, lineHeight: 0.98, marginTop: 6,
                    color: warn ? WARN : GOLD, opacity: txt, transform: `translateY(${(1 - txt) * 40}px)`,
                    textShadow: `0 0 30px ${warn ? "rgba(255,122,0,0.35)" : "rgba(242,193,78,0.3)"}` }}>
        {String(label).toUpperCase()}</div>
    </div>
  );

  return (
    <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 65% 50%, #10231a 0%, #07110c 75%)",
                  opacity: intro }}>
      {Text}
      <div style={{ position: "absolute", top: 0, bottom: 0, right: vertical ? 0 : 40, left: vertical ? 0 : 560,
                    display: "flex", alignItems: vertical ? "flex-end" : "center", justifyContent: "center",
                    paddingBottom: vertical ? 160 : 0, perspective: 1800, overflow: "hidden" }}>
        <div style={{ position: "relative", width: W, height: H, transformStyle: "preserve-3d",
                      transform: `rotateX(${rx}deg) scale(${sc}) translate(${tx * (sc - 0.9)}px, ${ty * (sc - 0.9)}px)`,
                      borderRadius: 14, background: "rgba(16,40,28,0.55)",
                      border: `2px solid rgba(242,193,78,0.35)`, boxShadow: "0 50px 90px rgba(0,0,0,0.65)" }}>
          <svg width={W} height={H} style={{ position: "absolute", inset: 0, overflow: "visible" }} fill="none">
            <g stroke="rgba(242,193,78,0.38)" strokeWidth="2.5" style={{ filter: "drop-shadow(0 0 4px rgba(242,193,78,0.5))" }}>
              {vertical ? (<>
                <line x1="0" y1={H / 2} x2={W} y2={H / 2} /><circle cx={W / 2} cy={H / 2} r={W * 0.12} />
                <rect x={W * 0.2} y="0" width={W * 0.6} height={H * 0.16} /><rect x={W * 0.2} y={H * 0.84} width={W * 0.6} height={H * 0.16} />
              </>) : (<>
                <line x1={W / 2} y1="0" x2={W / 2} y2={H} /><circle cx={W / 2} cy={H / 2} r={H * 0.15} />
                <rect x="0" y={H * 0.2} width={W * 0.16} height={H * 0.6} /><rect x={W * 0.84} y={H * 0.2} width={W * 0.16} height={H * 0.6} />
                <rect x="0" y={H * 0.36} width={W * 0.055} height={H * 0.28} /><rect x={W * 0.945} y={H * 0.36} width={W * 0.055} height={H * 0.28} />
              </>)}
            </g>
            {zones.map((z, i) => <rect key={i} x={z.x} y={z.y} width={z.w} height={z.h} rx="18"
                          fill={warn ? "rgba(255,122,0,0.16)" : "rgba(242,193,78,0.15)"} stroke={ring} strokeWidth="3"
                          opacity={txt} />)}
            {cur?.link && litPts.length > 1 ? (
              <polyline points={litPts.map((p) => `${p.x},${p.y}`).join(" ")} stroke={ring} strokeWidth="5"
                        strokeLinejoin="round" pathLength="1" strokeDasharray="1" strokeDashoffset={1 - draw} />
            ) : null}
            {arrows.map((a, i) => {
              const dx = a.e.x - a.s.x, dy = a.e.y - a.s.y, L = Math.hypot(dx, dy) || 1;
              const ex = a.s.x + dx * draw, ey = a.s.y + dy * draw, ux = dx / L, uy = dy / L;
              return (
                <g key={i}>
                  <line x1={a.s.x} y1={a.s.y} x2={ex} y2={ey} stroke={ring} strokeWidth="5" strokeDasharray="14 10" />
                  {draw > 0.95 ? <>
                    <polygon points={`${a.e.x},${a.e.y} ${a.e.x - 22 * ux + 12 * uy},${a.e.y - 22 * uy - 12 * ux} ${a.e.x - 22 * ux - 12 * uy},${a.e.y - 22 * uy + 12 * ux}`} fill={ring} />
                    <circle cx={a.e.x} cy={a.e.y} r="16" stroke="#fff" strokeWidth="3" />
                  </> : null}
                </g>
              );
            })}
          </svg>
          {sides.map((s) => (lu[s]?.starters || []).map((p, i) => {
            const pt = place(s, p);
            const pop = spring({ frame: f - 4 - i * 2, fps: 30, config: { damping: 14 } });
            const key = `${s}:${p.shirt}`;
            return (
              <div key={key} style={{ opacity: pop }}>
                <Puck x={pt.x} y={pt.y} n={p.shirt} col={s === "home" ? GOLD : GREY} size={size} f={f} ring={ring}
                      lit={litSet.has(key)} dim={litSet.size > 0 && !litSet.has(key)} />
              </div>
            );
          }))}
        </div>
      </div>
      <div style={{ position: "absolute", right: 60, bottom: vertical ? 60 : 36, fontFamily: BODY, fontSize: 18,
                    color: "rgba(255,255,255,0.55)" }}>
        Positions: starting line-up (FotMob){arrows.length ? " · arrows end at the real shot spot" : ""}
      </div>
    </div>
  );
};
