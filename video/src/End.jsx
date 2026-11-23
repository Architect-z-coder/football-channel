import { interpolate, spring, useCurrentFrame } from "remotion";
import { C, HEAD, BODY } from "./theme";

// THE VERDICT: the one main reason the game went the way it did, with its key number.
// visual: {type:"verdict", cause:"Relentless pressure", number:"3.29 xG v 0.17", detail:"10 corners to none"}
export const Verdict = ({ visual }) => {
  const f = useCurrentFrame();
  const stamp = spring({ frame: f - 4, fps: 30, config: { damping: 11, mass: 0.8 } });
  const line = interpolate(f, [10, 34], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const cause = spring({ frame: f - 16, fps: 30, config: { damping: 14 } });
  const num = spring({ frame: f - 30, fps: 30, config: { damping: 12 } });
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center",
                  justifyContent: "center", textAlign: "center" }}>
      <div style={{ fontFamily: BODY, fontWeight: 900, letterSpacing: 12, fontSize: 40, color: "#fff",
                    transform: `scale(${1.6 - 0.6 * stamp})`, opacity: stamp }}>THE VERDICT</div>
      <div style={{ width: 520 * line, height: 5, background: C.accent, margin: "22px 0 30px" }} />
      <div style={{ fontFamily: HEAD, fontSize: 120, lineHeight: 1, color: C.accent, maxWidth: 1500,
                    opacity: cause, transform: `translateY(${(1 - cause) * 40}px)` }}>
        {String(visual.cause || "").toUpperCase()}</div>
      {visual.number ? (
        <div style={{ marginTop: 34, fontFamily: BODY, fontWeight: 900, fontSize: 64, color: "#fff",
                      background: "rgba(242,193,78,0.14)", border: `3px solid ${C.accent}`, borderRadius: 16,
                      padding: "10px 34px", opacity: num, transform: `scale(${0.8 + 0.2 * num})` }}>{visual.number}</div>
      ) : null}
      {visual.detail ? (
        <div style={{ marginTop: 22, fontFamily: BODY, fontWeight: 700, fontSize: 38, color: "rgba(255,255,255,0.8)",
                      opacity: num }}>{visual.detail}</div>
      ) : null}
    </div>
  );
};

// Ad-style end card: what comes next, subscribe and bell.
// visual: {type:"outro", next?: "Next: Barcelona v Atlético"}
export const Outro = ({ visual, props }) => {
  const f = useCurrentFrame();
  const a = spring({ frame: f - 2, fps: 30, config: { damping: 13 } });
  const b = spring({ frame: f - 14, fps: 30, config: { damping: 12 } });
  const c = spring({ frame: f - 26, fps: 30, config: { damping: 10 } });
  const pulse = 1 + 0.05 * Math.sin(f / 5);
  const ring = Math.sin(Math.max(0, f - 40) / 2.2) * Math.max(0, 1 - Math.max(0, f - 40) / 40) * 22;
  const sweep = interpolate(f % 60, [0, 60], [-30, 130]);
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
      <div style={{ fontFamily: BODY, fontWeight: 800, letterSpacing: 8, fontSize: 34, color: "rgba(255,255,255,0.85)",
                    opacity: a, transform: `translateY(${(1 - a) * -30}px)` }}>STAY TUNED</div>
      <div style={{ position: "relative", overflow: "hidden", fontFamily: HEAD, fontSize: 132, lineHeight: 1, color: C.accent,
                    marginTop: 12, textAlign: "center", opacity: a, transform: `scale(${0.85 + 0.15 * a})` }}>
        NEXT DATA BREAKDOWN
        <div style={{ position: "absolute", top: 0, bottom: 0, left: `${sweep}%`, width: "18%",
                      background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.45), transparent)" }} />
      </div>
      <div style={{ marginTop: 14, fontFamily: BODY, fontWeight: 700, fontSize: 42, color: "#fff", opacity: b }}>
        {visual.next || "Coming soon on " + (props.channel || "The Other Touchline")}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 36, marginTop: 56, opacity: c, transform: `translateY(${(1 - c) * 40}px)` }}>
        <div style={{ fontFamily: BODY, fontWeight: 900, fontSize: 46, color: "#fff", background: "#cc0000", borderRadius: 14,
                      padding: "18px 46px", transform: `scale(${pulse})`, boxShadow: "0 10px 30px rgba(204,0,0,0.45)" }}>SUBSCRIBE</div>
        <svg width="90" height="90" viewBox="0 0 24 24" style={{ transform: `rotate(${ring}deg)`, transformOrigin: "50% 10%" }}>
          <path fill={C.accent} d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22zm7-6V11a7 7 0 0 0-5.5-6.84V3.5a1.5 1.5 0 0 0-3 0v.66A7 7 0 0 0 5 11v5l-2 2v1h18v-1z" />
        </svg>
      </div>
    </div>
  );
};
