import { interpolate, spring, useCurrentFrame } from "remotion";
import { C, HEAD, BODY } from "./theme";

const sp = (f, d = 0) => spring({ frame: f - d, fps: 30, config: { damping: 16, mass: 0.7 } });
const Wrap = ({ children }) => (
  <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center",
                justifyContent: "center", paddingTop: 80 }}>{children}</div>
);

// ---------- how xG is built: one pitch, the things the model looks at (no numbers) ----------
export const XgExplainer = () => {
  const f = useCurrentFrame();
  const W = 900, H = 560;              // half pitch, goal at top
  const items = [
    { t: "Distance to goal", d: 10 }, { t: "Angle to goal", d: 22 }, { t: "Foot or header", d: 34 },
    { t: "Type of pass before it", d: 46 }, { t: "Open play or set piece", d: 58 },
  ];
  const glow = interpolate(f, [0, 40], [0, 1], { extrapolateRight: "clamp" });
  return (
    <Wrap>
      <div style={{ fontFamily: HEAD, fontSize: 72, color: C.text, marginBottom: 26, opacity: sp(f) }}>
        What is xG?
      </div>
      <div style={{ display: "flex", gap: 70, alignItems: "center" }}>
        <svg width={W} height={H} style={{ background: "#0f3d24", borderRadius: 16 }}>
          <defs>
            <radialGradient id="xgz" cx="50%" cy="0%" r="70%">
              <stop offset="0%" stopColor={C.accent} stopOpacity={0.85 * glow} />
              <stop offset="35%" stopColor={C.accent} stopOpacity={0.35 * glow} />
              <stop offset="100%" stopColor={C.accent} stopOpacity={0} />
            </radialGradient>
          </defs>
          <rect x="0" y="0" width={W} height={H} fill="url(#xgz)" />
          <g stroke="rgba(255,255,255,0.75)" strokeWidth="3" fill="none">
            <rect x={W / 2 - 260} y="0" width="520" height="210" />
            <rect x={W / 2 - 120} y="0" width="240" height="70" />
            <circle cx={W / 2} cy="150" r="4" fill="white" />
            <line x1="0" y1={H - 2} x2={W} y2={H - 2} />
          </g>
          <rect x={W / 2 - 55} y="0" width="110" height="10" fill="white" />
          {[[W / 2, 120, 26], [W / 2 + 230, 190, 14], [W / 2 - 60, 330, 9]].map(([x, y, r], i) => {
            const s = sp(f, 70 + i * 12);
            return <circle key={i} cx={x} cy={y} r={r * s} fill="white" stroke={C.accent} strokeWidth="4" />;
          })}
        </svg>
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          {items.map((it) => {
            const s = sp(f, it.d);
            return (
              <div key={it.t} style={{ fontFamily: BODY, fontWeight: 800, fontSize: 40, color: C.text, opacity: s,
                                       transform: `translateX(${(1 - s) * 40}px)`, display: "flex", alignItems: "center", gap: 16 }}>
                <span style={{ width: 16, height: 16, borderRadius: 8, background: C.accent, display: "inline-block" }} />
                {it.t}
              </div>
            );
          })}
          <div style={{ fontFamily: BODY, fontSize: 28, color: C.muted, marginTop: 10, maxWidth: 560, opacity: sp(f, 80) }}>
            Learned from hundreds of thousands of past shots: how often a chance like this one is scored.
          </div>
        </div>
      </div>
    </Wrap>
  );
};

// ---------- the "why" funnel: xG -> xGOT -> goals, and the keeper ----------
export const DiagnosisFunnel = ({ visual, props }) => {
  const f = useCurrentFrame();
  const side = visual.side === "away" ? "away" : "home";
  const d = (props.diagnosis || {})[side];
  if (!d) return null;
  const other = side === "home" ? "away" : "home";
  const team = props[side], col = side === "home" ? C.home : C.away;
  const og = ((props.diagnosis || {}).own_goals || [0, 0])[side === "home" ? 0 : 1];
  const steps = [
    { label: "Chances created", sub: "xG", v: d.xg },
    d.xgot != null ? { label: "Shots on target", sub: "xGOT: where they went in the goal", v: d.xgot } : null,
    { label: "Goals from shots", sub: og ? `+ ${og} own goal` : "", v: d.goals },
  ].filter(Boolean);
  const max = Math.max(...steps.map((s) => s.v), 1);
  const prevented = d.xgot != null ? Math.round((d.xgot - d.goals) * 100) / 100 : null;
  return (
    <Wrap>
      <div style={{ fontFamily: HEAD, fontSize: 70, color: col, marginBottom: 34, opacity: sp(f) }}>
        {team}: where did the goals go?
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 30, width: 1400 }}>
        {steps.map((s, i) => {
          const g = sp(f, 12 + i * 18);
          return (
            <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 30, opacity: g }}>
              <div style={{ width: 380, textAlign: "right" }}>
                <div style={{ fontFamily: BODY, fontWeight: 800, fontSize: 38, color: C.text }}>{s.label}</div>
                <div style={{ fontFamily: BODY, fontSize: 24, color: C.muted }}>{s.sub}</div>
              </div>
              <div style={{ height: 76, width: (900 * s.v / max) * g + 6, background: col, borderRadius: 10,
                            opacity: 0.35 + 0.65 * (1 - i / steps.length) }} />
              <div style={{ fontFamily: HEAD, fontSize: 64, color: C.text }}>{s.v}</div>
            </div>
          );
        })}
      </div>
      {prevented != null ? (
        <div style={{ marginTop: 40, fontFamily: BODY, fontWeight: 700, fontSize: 36, color: C.accent, opacity: sp(f, 70) }}>
          {props[other]} goalkeeper: {prevented > 0 ? `${prevented} goals prevented` : `${-prevented} more conceded than expected`}
        </div>
      ) : null}
    </Wrap>
  );
};

// ---------- luck: the chances replayed 20,000 times ----------
export const ResultOdds = ({ props }) => {
  const f = useCurrentFrame();
  const sim = (props.diagnosis || {}).sim;
  if (!sim) return null;
  const parts = [
    { t: `${props.home} win`, v: sim[0], c: C.home },
    { t: "Draw", v: sim[1], c: C.muted },
    { t: `${props.away} win`, v: sim[2], c: C.away },
  ];
  const grow = interpolate(f, [10, 55], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <Wrap>
      <div style={{ fontFamily: HEAD, fontSize: 66, color: C.text, opacity: sp(f), textAlign: "center" }}>
        The same chances, replayed 20,000 times
      </div>
      <div style={{ fontFamily: BODY, fontSize: 28, color: C.muted, marginBottom: 46, opacity: sp(f, 6) }}>
        Each shot scores as often as its xG says. Own goals not counted.
      </div>
      <div style={{ display: "flex", width: 1500, height: 130, borderRadius: 14, overflow: "hidden" }}>
        {parts.map((p) => (
          <div key={p.t} style={{ width: `${p.v * grow}%`, background: p.c, display: "flex", alignItems: "center",
                                  justifyContent: "center", minWidth: p.v > 0 ? 4 : 0 }}>
            {p.v >= 8 ? <span style={{ fontFamily: HEAD, fontSize: 64, color: "#0b1410" }}>{Math.round(p.v * grow)}%</span> : null}
          </div>
        ))}
      </div>
      <div style={{ display: "flex", width: 1500, justifyContent: "space-between", marginTop: 20 }}>
        {parts.map((p) => (
          <div key={p.t} style={{ fontFamily: BODY, fontWeight: 800, fontSize: 36, color: p.c, opacity: sp(f, 40) }}>
            {p.t}: {p.v}%
          </div>
        ))}
      </div>
    </Wrap>
  );
};
