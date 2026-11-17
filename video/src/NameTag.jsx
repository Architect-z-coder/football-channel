import { Img, Sequence, interpolate, spring, staticFile, useCurrentFrame } from "remotion";
import { C, HEAD, BODY } from "./theme";

// A small round photo with the person's name and team, shown when the narration first names him.
const TAG = 90; // 3 s

const Tag = ({ t, scale }) => {
  const f = useCurrentFrame();
  const inn = spring({ frame: f, fps: 30, config: { damping: 15, mass: 0.6 } });
  const out = interpolate(f, [TAG - 10, TAG], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const size = 132 * scale;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 20 * scale, opacity: out,
                  transform: `translateX(${(1 - inn) * -80}px)`,
                  background: "rgba(7,17,12,0.88)", borderLeft: `${6 * scale}px solid ${C.accent}`,
                  borderRadius: 14 * scale, padding: `${12 * scale}px ${28 * scale}px ${12 * scale}px ${14 * scale}px`,
                  boxShadow: "0 10px 30px rgba(0,0,0,0.5)" }}>
      {t.file ? (
        <div style={{ width: size, height: size, borderRadius: "50%", overflow: "hidden",
                      border: `${4 * scale}px solid ${C.accent}`, flexShrink: 0, background: C.line }}>
          <Img src={staticFile(`run/${t.file}`)} onError={() => {}}
               style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 18%" }} />
        </div>
      ) : null}
      <div style={{ display: "flex", flexDirection: "column" }}>
        <div style={{ fontFamily: HEAD, fontSize: 52 * scale, color: C.text, lineHeight: 1.05 }}>{t.name}</div>
        <div style={{ fontFamily: BODY, fontWeight: 700, fontSize: 26 * scale, color: C.accent,
                      textTransform: "uppercase", letterSpacing: 1.5 }}>
          {[t.role === "Head coach" ? "Coach" : null, t.team].filter(Boolean).join(" · ")}
        </div>
        {t.credit ? (
          <div style={{ fontFamily: BODY, fontSize: 15 * scale, color: C.muted, marginTop: 4 }}>Photo: {t.credit}</div>
        ) : null}
      </div>
    </div>
  );
};

export const NameTags = ({ tags, left = 60, bottom = 210, scale = 1 }) => (
  <>
    {(tags || []).map((t, i) => (
      <Sequence key={i} from={t.from} durationInFrames={TAG} layout="none">
        <div style={{ position: "absolute", left, bottom }}>
          <Tag t={t} scale={scale} />
        </div>
      </Sequence>
    ))}
  </>
);
