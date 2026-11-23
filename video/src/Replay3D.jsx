import { interpolate, spring, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { C, HEAD, BODY } from "./theme";

// Moving 3D replay of one goal (or big chance), built from FotMob data:
//   REAL: both starting line-ups, the shot spot, where the ball entered the goal, the type of play
//         (corner, fast break, open play, penalty, free kick), body part, xG, scorer and assist names.
//   ILLUSTRATED: the build-up path (ball from the corner flag, the scorer's run, the assist pass) and a
//         reported area such as "ball lost in own half"; a line on screen says so.
// visual: {type:"goal_replay", minute, lost?: "own_half"|"midfield"|"final_third", lost_label?, source?}
const GOLD = C.accent, GREY = "#9ca3af", WARN = "#FF7A00";
const KIND = { FromCorner: "Corner", SetPiece: "Set piece", FreeKick: "Free kick", FastBreak: "Fast break",
               RegularPlay: "Open play", Penalty: "Penalty", ThrowInSetPiece: "Throw-in", IndividualPlay: "Solo run" };
const last = (n) => (n || "").split(" ").slice(-1)[0].toLowerCase();

export const Replay3D = ({ visual, props }) => {
  const f = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const vertical = height > width;
  const shots = props.shots || [];
  const goals = shots.filter((s) => s.result === "Goal").sort((a, b) => a.minute - b.minute);
  // the shot named by minute (and player, if given): exact minute first, then goals, then the biggest chance
  const g = visual.minute != null
    ? (shots.filter((s) => Math.abs(s.minute - visual.minute) <= 1 && (!visual.player || last(s.player) === last(visual.player)))
        .sort((a, b) => (Math.abs(a.minute - visual.minute) - Math.abs(b.minute - visual.minute))
                        || ((b.result === "Goal") - (a.result === "Goal")) || ((b.xg || 0) - (a.xg || 0)))[0])
    : goals[visual.goal_index || 0];
  if (!g) return null;
  const info = (props.goals || []).find((x) => Math.abs(x.minute - g.minute) <= 1 && last(x.player) === last(g.player)) || {};
  const own = /own/i.test(info.type || "");
  const att = g.side, def = att === "home" ? "away" : "home";
  const lu = props.lineups || {};
  const W = vertical ? 880 : 1300, H = vertical ? 1300 : 780;
  // depth d: 0 = attacking team's own goal, 1 = the goal it attacks; a = across (line-up frame)
  const P = (d, a) => (vertical ? { x: a * W, y: (1 - d) * H } : { x: d * W, y: a * H });
  const posOf = (side, p) => (side === att ? P(p.x, p.y) : P(1 - p.x, 1 - p.y));
  const all = (side) => [...(lu[side]?.starters || []), ...(lu[side]?.bench || [])];
  const find = (side, name) => all(side).find((p) => last(p.player || p.name) === last(name));
  const scorer = find(att, g.player);
  const assist = info.assist ? find(att, info.assist) : null;
  const spot = P(g.x, 1 - g.y);                                  // FotMob shot y is mirrored vs line-ups
  const goal = P(1, 1 - (g.goal_y ?? 0.5));
  const kind = g.situation;
  const corner = P(1, spot[vertical ? "x" : "y"] / (vertical ? W : H) < 0.5 ? 0 : 1);
  const start = kind === "FromCorner" ? corner
    : kind === "Penalty" ? spot
    : assist ? posOf(att, assist)
    : kind === "FastBreak" ? P(0.45, scorer ? scorer.y : 0.5) : P(Math.max(0.5, g.x - 0.25), 1 - g.y);
  const setPiece = ["FromCorner", "SetPiece", "FreeKick", "ThrowInSetPiece"].includes(kind);
  const runFrom = setPiece ? P(0.8, 0.5 + (0.5 - g.y) * 0.4)            // set pieces: from the edge of the box
    : scorer ? posOf(att, scorer) : P(Math.max(0.5, g.x - 0.25), 1 - g.y);

  // timeline (frames): 0-25 board in, 25-75 build-up, 75-100 shot, 100+ hold with a slow orbit
  const intro = spring({ frame: f, fps: 30, config: { damping: 20 } });
  const build = interpolate(f, [25, 75], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const shot = interpolate(f, [78, 96], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.in(Easing.quad) });
  const net = spring({ frame: f - 96, fps: 30, config: { damping: 9 } });
  const cam = spring({ frame: f - 10, fps: 30, config: { damping: 30, mass: 2 } });
  const rx = interpolate(cam, [0, 1], [46, 58]);
  const sc = interpolate(cam, [0, 1], [0.86, 1.18]);
  const rz = interpolate(f, [0, 300], vertical ? [0, 0] : [-4, 4]);
  const focus = P(0.78, 0.5);
  const tx = interpolate(cam, [0, 1], [0, (vertical ? W / 2 - focus.x : W / 2 - focus.x) * 0.55]);
  const ty = interpolate(cam, [0, 1], [0, (H / 2 - focus.y) * 0.55]);

  // ball position: build-up (start -> spot, curved for corners) then shot (spot -> goal)
  const lerp = (A, B, t) => ({ x: A.x + (B.x - A.x) * t, y: A.y + (B.y - A.y) * t });
  const curve = (A, B, t, lift) => {
    const m = lerp(A, B, 0.5), nx = -(B.y - A.y), ny = B.x - A.x, L = Math.hypot(nx, ny) || 1;
    const c = { x: m.x + (nx / L) * lift, y: m.y + (ny / L) * lift };
    return { x: (1 - t) ** 2 * A.x + 2 * (1 - t) * t * c.x + t * t * B.x, y: (1 - t) ** 2 * A.y + 2 * (1 - t) * t * c.y + t * t * B.y };
  };
  const lift = kind === "FromCorner" || kind === "FreeKick" ? 140 : 0;
  const ball = f < 78 ? curve(start, spot, build, lift) : lerp(spot, goal, shot);
  const runner = lerp(runFrom, spot, build);
  const trail = [...Array(14)].map((_, i) => {
    const t = Math.max(0, build - i * 0.03);
    return f < 78 ? curve(start, spot, t, lift) : lerp(spot, goal, Math.max(0, shot - i * 0.05));
  });
  const lostZone = visual.lost ? ({ own_half: [0.08, 0.5], midfield: [0.35, 0.65], final_third: [0.66, 0.95] }[visual.lost] || [0.08, 0.5]) : null;
  const size = vertical ? 58 : 52;
  const txt = spring({ frame: f - 30, fps: 30, config: { damping: 14 } });
  const label = own ? "Own goal" : KIND[kind] || "Open play";
  const isGoal = g.result === "Goal";

  return (
    <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 60% 50%, #10231a 0%, #06100b 75%)", opacity: intro }}>
      <div style={vertical ? { position: "absolute", top: 120, left: 60, right: 60, zIndex: 3 }
                           : { position: "absolute", left: 80, top: 0, bottom: 0, width: 520, display: "flex", flexDirection: "column", justifyContent: "center", zIndex: 3 }}>
        <div style={{ fontFamily: BODY, fontWeight: 800, letterSpacing: 5, fontSize: 30, color: "#fff", opacity: intro }}>
          MINUTE {g.minute}</div>
        <div style={{ fontFamily: HEAD, fontSize: vertical ? 104 : 100, lineHeight: 0.98, color: GOLD, marginTop: 6,
                      opacity: txt, transform: `translateY(${(1 - txt) * 30}px)` }}>{label.toUpperCase()}</div>
        <div style={{ fontFamily: BODY, fontWeight: 700, fontSize: 34, color: "#fff", marginTop: 18, opacity: txt }}>
          {g.player}{info.assist ? <span style={{ color: GREY }}> · from {info.assist}</span> : null}</div>
        <div style={{ fontFamily: BODY, fontWeight: 700, fontSize: 30, color: GREY, marginTop: 8, opacity: net }}>
          {(g.body_part || "").replace(/([a-z])([A-Z])/g, "$1 $2")} · xG {Number(g.xg).toFixed(2)}{isGoal ? "" : " · no goal"}</div>
      </div>
      <div style={{ position: "absolute", top: 0, bottom: 0, right: vertical ? 0 : 30, left: vertical ? 0 : 520, overflow: "hidden",
                    display: "flex", alignItems: vertical ? "flex-end" : "center", justifyContent: "center", paddingBottom: vertical ? 170 : 0, perspective: 1800 }}>
        <div style={{ position: "relative", width: W, height: H, transformStyle: "preserve-3d",
                      transform: `rotateX(${rx}deg) rotateZ(${rz}deg) scale(${sc}) translate(${tx}px, ${ty}px)`,
                      borderRadius: 14, background: "rgba(16,40,28,0.6)", border: "2px solid rgba(242,193,78,0.35)",
                      boxShadow: "0 50px 90px rgba(0,0,0,0.65)" }}>
          <svg width={W} height={H} style={{ position: "absolute", inset: 0, overflow: "visible" }} fill="none">
            <g stroke="rgba(242,193,78,0.38)" strokeWidth="2.5" style={{ filter: "drop-shadow(0 0 4px rgba(242,193,78,0.5))" }}>
              {vertical ? (<>
                <line x1="0" y1={H / 2} x2={W} y2={H / 2} /><circle cx={W / 2} cy={H / 2} r={W * 0.12} />
                <rect x={W * 0.2} y="0" width={W * 0.6} height={H * 0.16} /><rect x={W * 0.2} y={H * 0.84} width={W * 0.6} height={H * 0.16} />
              </>) : (<>
                <line x1={W / 2} y1="0" x2={W / 2} y2={H} /><circle cx={W / 2} cy={H / 2} r={H * 0.15} />
                <rect x="0" y={H * 0.2} width={W * 0.16} height={H * 0.6} /><rect x={W * 0.84} y={H * 0.2} width={W * 0.16} height={H * 0.6} />
                <rect x={W * 0.945} y={H * 0.36} width={W * 0.055} height={H * 0.28} />
              </>)}
            </g>
            {/* the goal it attacks */}
            {(() => { const a = P(1, 0.44), b = P(1, 0.56);
              return <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#fff" strokeWidth={10 + 8 * net} strokeLinecap="round"
                           style={{ filter: isGoal && net > 0.1 ? `drop-shadow(0 0 ${20 * net}px ${GOLD})` : "none" }} />; })()}
            {lostZone ? (() => { const a = P(lostZone[0], 0.05), b = P(lostZone[1], 0.95);
              return <rect x={Math.min(a.x, b.x)} y={Math.min(a.y, b.y)} width={Math.abs(b.x - a.x)} height={Math.abs(b.y - a.y)} rx="20"
                           fill="rgba(255,122,0,0.14)" stroke={WARN} strokeWidth="3" strokeDasharray="12 8"
                           opacity={interpolate(f, [12, 26], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />; })() : null}
            {/* scorer's run */}
            <line x1={runFrom.x} y1={runFrom.y} x2={runner.x} y2={runner.y} stroke={GOLD} strokeWidth="4" strokeDasharray="10 9" opacity={0.8} />
            {/* ball trail */}
            {trail.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r={9 - i * 0.5} fill="#fff" opacity={(f > 25 ? 0.5 : 0) * (1 - i / 14)} />)}
            {/* shot line to the goal */}
            {f >= 78 ? <line x1={spot.x} y1={spot.y} x2={ball.x} y2={ball.y} stroke={GOLD} strokeWidth="6" /> : null}
            <circle cx={spot.x} cy={spot.y} r={18} stroke="#fff" strokeWidth="3" opacity={build} />
          </svg>
          {[def, att].map((s) => (lu[s]?.starters || []).map((p, i) => {
            const isScorer = s === att && scorer && last(p.player || p.name) === last(g.player);
            const isAssist = s === att && assist && last(p.player || p.name) === last(info.assist);
            const pt = isScorer ? runner : posOf(s, p);
            const pop = spring({ frame: f - 3 - i, fps: 30, config: { damping: 14 } });
            const lit = isScorer || isAssist;
            return (
              <div key={`${s}${p.shirt}`} style={{ position: "absolute", left: pt.x - size / 2, top: pt.y - size / 2, width: size, height: size,
                    borderRadius: "50%", opacity: pop * (lit ? 1 : s === att ? 0.55 : 0.4),
                    background: s === "home" ? GOLD : GREY, display: "flex", alignItems: "center", justifyContent: "center",
                    fontFamily: BODY, fontWeight: 900, fontSize: size * 0.42, color: "#0b1410",
                    boxShadow: lit ? `0 0 ${size}px ${GOLD}, 0 0 0 4px #fff` : "0 4px 8px rgba(0,0,0,0.5)",
                    transform: `scale(${lit ? 1.2 : 1})` }}>{p.shirt}</div>
            );
          }))}
          {/* the ball */}
          <div style={{ position: "absolute", left: ball.x - 13, top: ball.y - 13, width: 26, height: 26, borderRadius: "50%",
                        background: "#fff", boxShadow: "0 0 18px rgba(255,255,255,0.9)", opacity: f > 20 ? 1 : 0 }} />
        </div>
      </div>
      <div style={{ position: "absolute", right: 50, top: vertical ? 60 : 30, fontFamily: BODY, fontSize: 18, color: "rgba(255,255,255,0.6)", textAlign: "right" }}>
        Shot spot, goal and line-ups: FotMob · build-up path illustrated{visual.lost ? ` · ${visual.lost_label || "area as reported"}` : ""}
      </div>
    </div>
  );
};
