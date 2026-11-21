import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, HEAD, BODY } from "./theme";

// A tilted (2.5D) tactics board built from the real line-ups (FotMob formation positions).
// visual: {type:"tactics_board", team:"home"|"away"|"both", kicker, title,
//          steps:[{from (frames), shirts:[..], side:"home"|"away", label}]}
const GOLD = "#f5b942", GREY = "#9ca3af", RED = "#ef4444";

const Puck = ({ x, y, n, col, lit, dim, size }) => (
  <div style={{ position: "absolute", left: x - size / 2, top: y - size / 2, width: size, height: size,
                borderRadius: "50%", background: col, opacity: dim ? 0.35 : 1,
                boxShadow: lit ? `0 0 ${size * 0.6}px ${col}, 0 0 0 ${size * 0.08}px #fff` : "0 4px 8px rgba(0,0,0,0.5)",
                transform: `scale(${lit ? 1.18 : 1})`, display: "flex", alignItems: "center", justifyContent: "center",
                fontFamily: BODY, fontWeight: 900, fontSize: size * 0.42, color: "#0b1410" }}>{n}</div>
);

export const TacticsBoard = ({ visual, props }) => {
  const f = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const vertical = height > width;
  const lu = props.lineups || {};
  const W = vertical ? 900 : 1500, H = vertical ? 1250 : 820;
  const sides = visual.team === "both" ? ["home", "away"] : [visual.team || "home"];
  const steps = (visual.steps || []).filter((s) => f >= (s.from || 0));
  const cur = steps[steps.length - 1];
  const litSet = new Set((cur?.shirts || []).map((n) => `${cur.side || sides[0]}:${n}`));
  // pitch coords: FotMob x = 0 (own goal) .. 1, y = 0..1 across. Home attacks up (vertical) / right.
  const place = (side, p) => {
    const depth = side === "home" ? p.x * 0.5 : 1 - p.x * 0.5;       // both halves when two teams
    const d = sides.length === 1 ? p.x : depth;
    const across = side === "home" ? p.y : 1 - p.y;
    return vertical ? { x: across * W, y: (1 - d) * H } : { x: d * W, y: across * H };
  };
  const inn = spring({ frame: f, fps: 30, config: { damping: 16 } });
  const label = cur?.label;
  const lblIn = cur ? spring({ frame: f - cur.from, fps: 30, config: { damping: 14 } }) : 0;
  const lit = sides.flatMap((s) => (lu[s]?.starters || []).filter((p) => litSet.has(`${s}:${p.shirt}`)).map((p) => place(s, p)));
  const lx = lit.length ? lit.reduce((a, b) => a + b.x, 0) / lit.length : W / 2;
  const ly = lit.length ? Math.min(...lit.map((b) => b.y)) - 70 : 0;
  const size = vertical ? 62 : 54;
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center",
                  justifyContent: "center", paddingTop: vertical ? 120 : 60 }}>
      <div style={{ textAlign: "center", marginBottom: vertical ? 10 : 0, opacity: inn, zIndex: 2 }}>
        <div style={{ fontFamily: BODY, fontWeight: 800, letterSpacing: 4, fontSize: vertical ? 30 : 26, color: GOLD }}>
          {visual.kicker || (sides.length === 2 ? "THE LINE-UPS" : (lu[sides[0]]?.team || "").toUpperCase())}
        </div>
        <div style={{ fontFamily: HEAD, fontSize: vertical ? 96 : 84, color: "#fff", lineHeight: 1 }}>
          {visual.title || sides.map((s) => lu[s]?.formation).join("  v  ")}
        </div>
      </div>
      <div style={{ perspective: 1400, perspectiveOrigin: "50% 0%" }}>
        <div style={{ position: "relative", width: W, height: H, transform: `rotateX(${vertical ? 30 : 38}deg)`,
                      transformOrigin: "50% 100%", borderRadius: 18,
                      background: "radial-gradient(ellipse at 50% 40%, #1c3a28 0%, #0f2418 70%, #0b1712 100%)",
                      border: "3px solid rgba(255,255,255,0.25)", boxShadow: "0 40px 80px rgba(0,0,0,0.6)" }}>
          {/* pitch lines */}
          <svg width={W} height={H} style={{ position: "absolute", inset: 0 }} stroke="rgba(255,255,255,0.28)" fill="none" strokeWidth="3">
            {vertical ? (<>
              <line x1="0" y1={H / 2} x2={W} y2={H / 2} /><circle cx={W / 2} cy={H / 2} r={W * 0.12} />
              <rect x={W * 0.2} y="0" width={W * 0.6} height={H * 0.16} /><rect x={W * 0.2} y={H * 0.84} width={W * 0.6} height={H * 0.16} />
            </>) : (<>
              <line x1={W / 2} y1="0" x2={W / 2} y2={H} /><circle cx={W / 2} cy={H / 2} r={H * 0.15} />
              <rect x="0" y={H * 0.2} width={W * 0.16} height={H * 0.6} /><rect x={W * 0.84} y={H * 0.2} width={W * 0.16} height={H * 0.6} />
            </>)}
          </svg>
          {sides.map((s) => (lu[s]?.starters || []).map((p, i) => {
            const pt = place(s, p);
            const pop = spring({ frame: f - 4 - i * 2, fps: 30, config: { damping: 14 } });
            const key = `${s}:${p.shirt}`;
            return (
              <div key={key} style={{ opacity: pop, transform: `translateY(${(1 - pop) * -30}px)` }}>
                <Puck x={pt.x} y={pt.y} n={p.shirt} col={s === "home" ? GOLD : GREY} size={size}
                      lit={litSet.has(key)} dim={litSet.size > 0 && !litSet.has(key)} />
              </div>
            );
          }))}
          {label ? (
            <div style={{ position: "absolute", left: lx, top: ly, transform: `translate(-50%, -50%) scale(${lblIn})`,
                          background: "#0b1410", color: cur.color === "red" ? RED : "#fff", border: `2px solid ${GOLD}`,
                          borderRadius: 30, padding: "8px 22px", fontFamily: BODY, fontWeight: 900,
                          fontSize: vertical ? 34 : 30, letterSpacing: 2, whiteSpace: "nowrap" }}>{label}</div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
