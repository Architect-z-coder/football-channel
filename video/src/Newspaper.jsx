import "@fontsource/playfair-display/700.css";
import "@fontsource/playfair-display/900.css";
import "@fontsource/playfair-display/400-italic.css";
import "@fontsource/unifrakturmaguntia/400.css";
import { Img, interpolate, spring, staticFile, useCurrentFrame } from "remotion";

// "The Other Touchline" newspaper look: newsprint paper, blackletter masthead, serif headlines.
export const PAPER = "#F1E9D8";
export const INK = "#1B1A17";
export const INK2 = "#5A554B";
export const RED = "#9E1B1B";
export const MAST = "UnifrakturMaguntia, 'Old English Text MT', serif";
export const SERIF = "'Playfair Display', Georgia, serif";

// a slightly torn paper edge
const TORN = "polygon(0% 1.5%, 6% 0%, 13% 1.2%, 21% 0.2%, 30% 1.4%, 38% 0%, 47% 1%, 55% 0.1%, 64% 1.3%, 72% 0.2%, 81% 1.1%, 90% 0%, 100% 1.2%, 99.2% 50%, 100% 98.5%, 92% 100%, 83% 98.8%, 74% 100%, 65% 98.7%, 56% 99.9%, 47% 98.6%, 38% 100%, 29% 98.9%, 20% 99.8%, 11% 98.6%, 4% 100%, 0% 98.7%, 0.8% 50%)";

const paperBg = {
  background: `radial-gradient(ellipse at 30% 20%, #F7F1E3 0%, ${PAPER} 55%, #E3D8C1 100%)`,
};

export const Masthead = ({ name = "The Other Touchline", size = 34, line, s = 1 }) => (
  <div style={{ textAlign: "center", color: INK }}>
    <div style={{ fontFamily: MAST, fontSize: size * s, lineHeight: 1.05 }}>{name}</div>
    <div style={{ borderTop: `${2 * s}px solid ${INK}`, borderBottom: `${1 * s}px solid ${INK}`, height: 3 * s,
                  margin: `${4 * s}px 0 ${3 * s}px` }} />
    {line ? (
      <div style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 13 * s, color: INK2, letterSpacing: 0.5 }}>{line}</div>
    ) : null}
  </div>
);

// ---------- the player/coach photo, as a newspaper clipping ----------
export const Clipping = ({ t, s = 1, channel, frames = 90 }) => {
  const f = useCurrentFrame();
  const inn = spring({ frame: f, fps: 30, config: { damping: 13, mass: 0.7 } });
  const out = interpolate(f, [frames - 10, frames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const rot = -2.5 + (1 - inn) * -8;
  const W = 330 * s;
  const role = t.role === "Head coach" ? "Head coach" : t.role === "Missing" ? "Missing tonight" : null;
  return (
    <div style={{ width: W, opacity: out, transform: `translateY(${(1 - inn) * 60}px) rotate(${rot}deg)`,
                  transformOrigin: "50% 100%", filter: "drop-shadow(0 14px 22px rgba(0,0,0,0.55))" }}>
      <div style={{ ...paperBg, clipPath: TORN, padding: `${16 * s}px ${16 * s}px ${14 * s}px` }}>
        <Masthead name={channel} size={24} s={s} line={null} />
        {t.file ? (
          <div style={{ marginTop: 8 * s, border: `${1.5 * s}px solid ${INK}`, height: W * 0.78, overflow: "hidden",
                        background: "#cfc6b3" }}>
            <Img src={staticFile(`run/${t.file}`)} onError={() => {}}
                 style={{ width: "100%", height: "100%", objectFit: "cover",
                          objectPosition: t.face ? `${(t.face[0] * 100).toFixed(1)}% ${(t.face[1] * 100).toFixed(1)}%` : "50% 20%",
                          transform: t.face ? "scale(1.35)" : "none",
                          transformOrigin: t.face ? `${(t.face[0] * 100).toFixed(1)}% ${(t.face[1] * 100).toFixed(1)}%` : "50% 50%",
                          filter: "grayscale(1) contrast(1.25) brightness(1.02) sepia(0.18)" }} />
          </div>
        ) : null}
        <div style={{ fontFamily: SERIF, fontWeight: 900, fontSize: (t.name.length > 18 ? 26 : 31) * s, color: INK,
                      lineHeight: 1.05, marginTop: 10 * s, textTransform: "uppercase", letterSpacing: 0.3 }}>
          {t.name}
        </div>
        <div style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 17 * s, color: INK2, marginTop: 3 * s }}>
          {[role, t.team].filter(Boolean).join(", ")}
        </div>
        {t.credit ? (
          <div style={{ fontFamily: SERIF, fontSize: 10.5 * s, color: INK2, marginTop: 6 * s,
                        borderTop: `${1 * s}px solid rgba(27,26,23,0.35)`, paddingTop: 3 * s }}>
            Photo: {t.credit}
          </div>
        ) : null}
      </div>
    </div>
  );
};

// ---------- a scene title as a front-page headline: big for a moment, then a small paper tab ----------
export const Headline = ({ text, channel, kicker, sceneNo, big = 75 }) => {
  const f = useCurrentFrame();
  if (!text) return null;
  const inn = spring({ frame: f, fps: 30, config: { damping: 14, mass: 0.8 } });
  const shrink = spring({ frame: f - big, fps: 30, config: { damping: 18, mass: 0.8 } }); // 0 = big, 1 = tab
  // big: centred front page; tab: top-left
  const scale = interpolate(shrink, [0, 1], [1, 0.34]);
  const x = interpolate(shrink, [0, 1], [960, 60]);
  const y = interpolate(shrink, [0, 1], [150, 105]);
  const anchor = interpolate(shrink, [0, 1], [50, 0]);
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `translateX(-${anchor}%) scale(${scale * (0.9 + 0.1 * inn)}) rotate(${(1 - inn) * -4}deg)`,
                  transformOrigin: shrink > 0.5 ? "0% 0%" : "50% 0%", opacity: inn,
                  filter: "drop-shadow(0 18px 30px rgba(0,0,0,0.6))", zIndex: 6 }}>
      <div style={{ ...paperBg, clipPath: TORN, width: 1100, padding: "26px 44px 30px" }}>
        <Masthead name={channel} size={62} line={kicker} s={1} />
        <div style={{ display: "flex", justifyContent: "space-between", fontFamily: SERIF, fontSize: 18, color: INK2,
                      textTransform: "uppercase", letterSpacing: 2, marginTop: 4 }}>
          <span>Match report</span><span>Part {sceneNo}</span>
        </div>
        <div style={{ borderTop: `1px solid ${INK}`, margin: "8px 0 14px" }} />
        <div style={{ fontFamily: SERIF, fontWeight: 900, fontSize: text.length > 34 ? 70 : 86, color: INK,
                      lineHeight: 1.02, textAlign: "center" }}>
          {text}
        </div>
      </div>
    </div>
  );
};

// ---------- the Short's hook as the front page (stays at the top) ----------
export const ShortFront = ({ hook, channel, line }) => {
  const f = useCurrentFrame();
  const inn = spring({ frame: f, fps: 30, config: { damping: 14, mass: 0.7 } });
  return (
    <div style={{ position: "absolute", top: 105, left: 50, right: 50, zIndex: 5, opacity: inn,
                  transform: `translateY(${(1 - inn) * -40}px) rotate(-1deg)`,
                  filter: "drop-shadow(0 16px 26px rgba(0,0,0,0.6))" }}>
      <div style={{ ...paperBg, clipPath: TORN, padding: "24px 36px 30px" }}>
        <Masthead name={channel} size={64} line={line} s={1.15} />
        <div style={{ fontFamily: SERIF, fontWeight: 900, fontSize: hook.length > 24 ? 84 : 100, color: INK,
                      lineHeight: 1.0, textAlign: "center", marginTop: 14 }}>
          {hook}
        </div>
      </div>
    </div>
  );
};

// ---------- a cut from a real article: screenshot (free pages) or our rebuilt clipping ----------
const MARK = "rgba(255, 214, 10, 0.62)";

const litCount = (f, hl, total, dur) => {
  if (hl && hl.length) {
    const said = hl.filter((x) => f >= x).length;
    return Math.round((said / hl.length) * total);
  }
  return Math.round(interpolate(f, [15, Math.max(30, dur - 25)], [0, total], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
};

const fmtDate = (d) => {
  if (!d) return "";
  const t = new Date(d);
  return isNaN(t) ? d : t.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
};

export const PressCut = ({ visual, props, scene }) => {
  const f = useCurrentFrame();
  const r = (props.reviews || [])[visual.review_index ?? 0];
  if (!r) return null;
  const dur = scene?.durationInFrames || 240;
  const inn = spring({ frame: f, fps: 30, config: { damping: 15, mass: 0.8 } });
  const zoom = interpolate(f, [0, dur], [1, 1.05]);
  const byline = [r.outlet, r.author ? `By ${r.author}` : null, fmtDate(r.date)].filter(Boolean).join("  ·  ");
  const shot = r.kind === "screenshot" && r.files?.para;
  let body;
  if (shot) {
    const D = Math.min(1240, (560 / r.box.h) * r.box.w);
    const k = D / r.box.w;
    const lit = litCount(f, visual.hl, r.rects.length, dur);
    body = (
      <>
        {r.files.head ? (
          <Img src={staticFile(`run/${r.files.head}`)} style={{ display: "block", maxWidth: 1240, maxHeight: 230,
                                                               objectFit: "contain", margin: "0 auto 18px" }} />
        ) : null}
        <div style={{ position: "relative", width: D, margin: "0 auto" }}>
          <Img src={staticFile(`run/${r.files.para}`)} style={{ display: "block", width: D }} />
          {r.rects.slice(0, lit).map((b, i) => (
            <div key={i} style={{ position: "absolute", left: b.x * k - 3, top: b.y * k + b.h * k * 0.12,
                                  width: b.w * k + 6, height: b.h * k * 0.86, background: MARK,
                                  mixBlendMode: "multiply", borderRadius: 3 }} />
          ))}
        </div>
      </>
    );
  } else {
    const words = String(r.quote).split(/\s+/);
    const lit = litCount(f, visual.hl, words.length, dur);
    body = (
      <>
        <div style={{ fontFamily: SERIF, fontWeight: 900, fontSize: (r.headline || "").length > 70 ? 46 : 56,
                      color: INK, lineHeight: 1.08, textAlign: "center", margin: "6px 20px 20px" }}>{r.headline}</div>
        <div style={{ borderTop: `1px solid ${INK}`, margin: "0 0 22px" }} />
        <div style={{ fontFamily: SERIF, fontSize: 44, color: INK, lineHeight: 1.45, padding: "0 30px" }}>
          {words.map((w, i) => (
            <span key={i} style={{ background: i < lit ? MARK : "transparent", boxDecorationBreak: "clone",
                                   padding: "0 4px", borderRadius: 3 }}>{w} </span>
          ))}
        </div>
      </>
    );
  }
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                  paddingTop: 70 }}>
      <div style={{ width: 1400, transform: `scale(${zoom * (0.94 + 0.06 * inn)}) rotate(${-1.2 + (1 - inn) * -5}deg)`,
                    opacity: inn, filter: "drop-shadow(0 24px 40px rgba(0,0,0,0.65))" }}>
        <div style={{ background: shot ? "#FFFFFF" : `radial-gradient(ellipse at 30% 20%, #F7F1E3 0%, ${PAPER} 55%, #E3D8C1 100%)`,
                      clipPath: TORN, padding: "34px 50px 40px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", fontFamily: SERIF,
                        color: INK2, fontSize: 22, letterSpacing: 1.5, textTransform: "uppercase",
                        borderBottom: `2px solid ${INK}`, paddingBottom: 10, marginBottom: 20 }}>
            <span style={{ fontWeight: 900, color: INK, fontSize: 30, letterSpacing: 0.5, textTransform: "none" }}>{r.outlet}</span>
            <span>{[r.author ? `By ${r.author}` : null, fmtDate(r.date)].filter(Boolean).join("  ·  ")}</span>
          </div>
          {body}
          <div style={{ fontFamily: SERIF, fontStyle: "italic", fontSize: 17, color: INK2, marginTop: 22, textAlign: "right" }}>
            {shot ? "Screenshot of the article as published" : "Quoted as published · layout by The Other Touchline"}
          </div>
        </div>
      </div>
    </div>
  );
};
