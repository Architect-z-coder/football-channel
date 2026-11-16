import {
  AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { C, HEAD, BODY } from "./theme";
import { SceneVisual } from "./scenes";
import { Captions } from "./Match";

// Vertical short (1080x1920): hook on top, the match graphic in the middle, big captions below.
const END = 45; // frames of the closing card
// how much to zoom each 16:9 graphic so it fills the phone width (content widths differ by type)
const ZOOM = { player_ratings: 0.62, quote_card: 0.62, momentum: 0.66, shot_map: 1.1, key_number: 1.0, scoreline: 0.78, halftime_fulltime: 0.78, stat_bars: 0.64,
  xg_timeline: 0.66, table_snapshot: 0.6, form_compare: 0.62, history_lens: 0.62 };
const BOX_TOP = 650, BOX_H = 820;

const VBackground = () => {
  const f = useCurrentFrame();
  const y = 45 + 10 * Math.sin(f / 200);
  return (
    <AbsoluteFill style={{ background: `radial-gradient(circle at 50% ${y}%, ${C.bg2} 0%, ${C.bg} 65%)` }} />
  );
};

export const Short = (props) => {
  const f = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const short = props.short;
  const speak = durationInFrames - END;
  const hookIn = spring({ frame: f, fps, config: { damping: 14, mass: 0.6 } });
  const visIn = spring({ frame: f - 8, fps, config: { damping: 16, mass: 0.7 } });
  const endIn = spring({ frame: f - speak, fps, config: { damping: 14, mass: 0.6 } });
  const progress = Math.min(1, f / durationInFrames);
  // the 16:9 scene graphics, scaled to the phone width
  const zoom = ZOOM[short.visual?.type] || 0.6;
  const scene = { id: 1, durationInFrames: speak, visual: short.visual, on_screen: "", narration: "" };
  return (
    <AbsoluteFill style={{ fontFamily: BODY }}>
      <VBackground />
      <div style={{ position: "absolute", top: 70, left: 60, right: 60, height: 8, background: C.line, borderRadius: 4 }}>
        <div style={{ width: `${progress * 100}%`, height: "100%", background: C.accent, borderRadius: 4 }} />
      </div>
      <div style={{ position: "absolute", top: 110, left: 60, right: 60, display: "flex", gap: 14,
                    alignItems: "center", color: C.muted, fontWeight: 700, fontSize: 30, letterSpacing: 2 }}>
        <div style={{ width: 16, height: 16, borderRadius: 8, background: C.accent }} />
        {props.channel.toUpperCase()}
      </div>
      <div style={{ position: "absolute", top: 190, left: 60, right: 60, fontFamily: HEAD, fontSize: short.hook.length > 26 ? 90 : 112,
                    lineHeight: 1.02, color: C.text, textTransform: "uppercase",
                    opacity: hookIn, transform: `translateY(${(1 - hookIn) * 40}px)` }}>
        {short.hook}
      </div>
      <div style={{ position: "absolute", top: 580, left: 60, color: C.muted, fontSize: 30, fontWeight: 600 }}>
        {props.home} v {props.away} · {props.competition}
      </div>
      <div style={{ position: "absolute", top: BOX_TOP, left: 0, width: 1080, height: BOX_H, overflow: "hidden",
                    opacity: visIn * (1 - endIn), transform: `scale(${0.94 + 0.06 * visIn})` }}>
        <div style={{ width: 1920, height: 1080, position: "absolute",
                      left: (1080 - 1920 * zoom) / 2, top: (BOX_H - 1080 * zoom) / 2,
                      transform: `scale(${zoom})`, transformOrigin: "top left" }}>
          <SceneVisual scene={scene} props={props} />
        </div>
      </div>
      {f < speak ? (
        <Captions text={short.narration} speakFrames={speak - 10} wordStarts={short.wordStarts}
                  per={4} size={72} bottom={270} maxWidth={980} />
      ) : null}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: endIn,
                             background: `rgba(7,17,12,${0.85 * endIn})` }}>
        <div style={{ fontFamily: HEAD, fontSize: 96, color: C.accent, textAlign: "center", lineHeight: 1.05,
                      transform: `scale(${0.9 + 0.1 * endIn})` }}>
          FULL BREAKDOWN<br />ON THE CHANNEL
        </div>
      </AbsoluteFill>
      <div style={{ position: "absolute", bottom: 60, left: 0, right: 0, textAlign: "center",
                    color: C.muted, fontSize: 26, fontWeight: 500 }}>
        Data: {props.source}
      </div>
      <Audio src={staticFile(short.audio)} />
      <Audio src={staticFile("sfx/whoosh.wav")} volume={0.35} />
      <Sequence from={speak}><Audio src={staticFile("sfx/hit.wav")} volume={0.45} /></Sequence>
    </AbsoluteFill>
  );
};
