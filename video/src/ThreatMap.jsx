import { spring, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { C, HEAD, BODY } from "./theme";

// Where one team's threat came from: its shots in time order on the attacking half, sized by xG,
// coloured by the type of attack, with the share of xG per channel (left / centre / right).
// visual: {type:"threat_map", side:"home"|"away", title?, kicker?}
const COL = { "fast break": "#ef4444", "open play": "#f5b942", "set piece": "#60a5fa" };
const SET = ["SetPiece", "FromCorner", "FreeKick", "ThrowInSetPiece", "Penalty", "DirectFreekick"];
const kind = (s) => (s.situation === "FastBreak" ? "fast break" : SET.includes(s.situation) ? "set piece" : "open play");

export const ThreatMap = ({ visual, props, scene }) => {
  const f = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const vertical = height > width;
  const side = visual.side === "away" ? "away" : "home";
  const team = props[side];
  const shots = (props.shots || []).filter((s) => s.side === side && (!visual.player || s.player === visual.player))
    .sort((a, b) => a.minute - b.minute);
  const sum = (fn) => Math.round(shots.filter(fn).reduce((a, s) => a + s.xg, 0) * 100) / 100;
  const chanOf = (s) => (s.y < 1 / 3 ? "right" : s.y > 2 / 3 ? "left" : "centre");
  const th = visual.player ? {
    by_channel: { left: sum((s) => chanOf(s) === "left"), centre: sum((s) => chanOf(s) === "centre"), right: sum((s) => chanOf(s) === "right") },
    by_type: Object.fromEntries(["fast break", "open play", "set piece"].map((t) => [t, sum((s) => kind(s) === t)])),
    shots_by_type: Object.fromEntries(["fast break", "open play", "set piece"].map((t) => [t, shots.filter((s) => kind(s) === t).length])),
  } : ((props.diagnosis || {}).threat || {})[side];
  const W = vertical ? 900 : 1100, H = vertical ? 820 : 640;       // attacking half, goal at the top
  // shot x: 0.5..1 towards goal; shot y: high = attacker's left (FotMob)
  const px = (s) => (1 - s.y) * W, py = (s) => Math.max(0, (1 - s.x) / 0.5) * H;
  const dur = (scene?.durationInFrames || 240) - 40;
  const step = Math.max(6, Math.min(24, dur / Math.max(1, shots.length)));
  const inn = spring({ frame: f, fps: 30, config: { damping: 16 } });
  const total = shots.reduce((a, s) => a + s.xg, 0) || 1;
  const lanes = ["left", "centre", "right"];
  const done = Math.max(0, Math.floor((f - 20) / step));
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: vertical ? "column" : "row",
                  alignItems: "center", justifyContent: "center", gap: vertical ? 30 : 70, paddingTop: vertical ? 120 : 70 }}>
      <div style={{ position: "relative", width: W, height: H, opacity: inn }}>
        <div style={{ position: "absolute", inset: 0, borderRadius: 16,
                      background: "radial-gradient(ellipse at 50% 0%, #1c3a28 0%, #0f2418 70%)",
                      border: "3px solid rgba(255,255,255,0.25)" }} />
        {lanes.map((l, i) => {
          const v = th ? th.by_channel[l] : 0;
          const a = interpolate(f, [20 + shots.length * step, 40 + shots.length * step], [0, 1],
                                { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={l} style={{ position: "absolute", left: (i * W) / 3, top: 0, width: W / 3, height: H,
                                  background: `rgba(245,185,66,${0.32 * a * (v / total)})`,
                                  borderLeft: i ? "2px dashed rgba(255,255,255,0.15)" : "none" }}>
              <div style={{ position: "absolute", bottom: 14, width: "100%", textAlign: "center", opacity: a,
                            fontFamily: HEAD, fontSize: vertical ? 54 : 46, color: "#fff" }}>
                {Math.round((100 * v) / total)}%
              </div>
              <div style={{ position: "absolute", bottom: vertical ? 92 : 82, width: "100%", textAlign: "center", opacity: a,
                            fontFamily: BODY, fontWeight: 800, fontSize: 22, letterSpacing: 3, color: "#cbd5e1" }}>
                {l.toUpperCase()}
              </div>
            </div>
          );
        })}
        <svg width={W} height={H} style={{ position: "absolute", inset: 0 }} stroke="rgba(255,255,255,0.35)" fill="none" strokeWidth="3">
          <rect x={W * 0.2} y="0" width={W * 0.6} height={H * 0.31} />
          <rect x={W * 0.37} y="0" width={W * 0.26} height={H * 0.1} />
          <rect x={W * 0.44} y="-8" width={W * 0.12} height="10" fill="#fff" />
        </svg>
        {shots.map((s, i) => {
          const p = spring({ frame: f - 20 - i * step, fps: 30, config: { damping: 12 } });
          if (p <= 0.01) return null;
          const r = 10 + Math.sqrt(s.xg) * 46, k = kind(s), goal = s.result === "Goal";
          return (
            <div key={i} style={{ position: "absolute", left: px(s) - r, top: py(s) - r, width: 2 * r, height: 2 * r,
                                  borderRadius: "50%", background: COL[k], opacity: 0.85 * p,
                                  transform: `scale(${p})`, boxShadow: goal ? "0 0 0 5px #fff, 0 0 30px #fff" : "none" }}>
              {k === "fast break" ? (
                <div style={{ position: "absolute", left: r - 3, top: 2 * r, width: 6, height: 90 * p,
                              background: `linear-gradient(${COL[k]}, transparent)` }} />
              ) : null}
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, opacity: inn, width: vertical ? W : 640 }}>
        <div style={{ fontFamily: BODY, fontWeight: 800, letterSpacing: 4, fontSize: 26, color: "#f5b942" }}>
          {visual.kicker || "WHERE THE THREAT CAME FROM"}
        </div>
        <div style={{ fontFamily: HEAD, fontSize: vertical ? 70 : 64, color: "#fff", lineHeight: 1 }}>{visual.title || visual.player || team}</div>
        {th ? ["fast break", "open play", "set piece"].map((t, i) => {
          const g = spring({ frame: f - 30 - i * 8, fps: 30, config: { damping: 16 } });
          return (
            <div key={t} style={{ display: "flex", alignItems: "center", gap: 16, opacity: g }}>
              <span style={{ width: 22, height: 22, borderRadius: 11, background: COL[t] }} />
              <span style={{ fontFamily: BODY, fontWeight: 700, fontSize: 30, color: "#fff", width: 200, whiteSpace: "nowrap" }}>{t}</span>
              <span style={{ height: 22, width: (300 * th.by_type[t] / total) * g + 4, background: COL[t], borderRadius: 6 }} />
              <span style={{ fontFamily: BODY, fontWeight: 800, fontSize: 28, color: "#cbd5e1", whiteSpace: "nowrap" }}>
                {th.by_type[t]} xG · {th.shots_by_type[t]} shot{th.shots_by_type[t] === 1 ? "" : "s"}
              </span>
            </div>
          );
        }) : null}
      </div>
    </div>
  );
};
