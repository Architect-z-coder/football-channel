import {
  AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { C, HEAD, BODY } from "./theme";
import { SceneVisual, findPhoto } from "./scenes";
import { Captions } from "./Match";
import { NameTags } from "./NameTag";
import { Crowd } from "./Crowd";
import { ShortFront } from "./Newspaper";

// Vertical short (1080x1920): hook on top, the match graphic in the middle, big captions below.
const END = 45; // frames of the closing card
// how much to zoom each 16:9 graphic so it fills the phone width (content widths differ by type)
const ZOOM = { goal_replay: 0.6, key_moments: 0.62, lineups: 0.56, player_ratings: 0.62, quote_card: 0.62, momentum: 0.66, shot_map: 1.1, key_number: 1.0, scoreline: 0.78, halftime_fulltime: 0.78, stat_bars: 0.64,
  xg_timeline: 0.66, table_snapshot: 0.6, form_compare: 0.62, history_lens: 0.62,
  diagnosis: 0.66, result_odds: 0.68, xg_explainer: 0.6 };
const BOX_TOP = 650, BOX_H = 820;

const VBackground = () => {
  const f = useCurrentFrame();
  const y = 45 + 10 * Math.sin(f / 200);
  return (
    <AbsoluteFill style={{ background: `radial-gradient(circle at 50% ${y}%, ${C.bg2} 0%, ${C.bg} 65%)` }} />
  );
};

const VShot = ({ len, children }) => {
  const f = useCurrentFrame();
  const o = Math.min(interpolate(f, [0, 8], [0, 1], { extrapolateRight: "clamp" }),
                     interpolate(f, [len - 8, len], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

// full-height photo for shots about a person: slow push-in, name low, credit small
const VPhoto = ({ ph, visual, len }) => {
  const f = useCurrentFrame();
  const zoom = interpolate(f, [0, len], [1.05, 1.15]);
  return (
    <AbsoluteFill>
      <Img src={staticFile(`run/${ph.file}`)} onError={() => {}} style={{ width: "100%", height: "100%", objectFit: "cover",
           objectPosition: "50% 22%", transform: `scale(${zoom})` }} />
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(7,17,12,0.85) 0%, rgba(7,17,12,0.1) 30%, rgba(7,17,12,0.2) 55%, rgba(7,17,12,0.92) 82%)" }} />
      <div style={{ position: "absolute", left: 60, right: 60, top: 1240 }}>
        <div style={{ fontFamily: HEAD, fontSize: 80, color: "#fff", lineHeight: 1 }}>{ph.role === "Stadium" ? ph.name.split(",")[0] : ph.name}</div>
        {visual.caption ? <div style={{ fontFamily: BODY, fontWeight: 700, fontSize: 38, color: C.accent, marginTop: 8 }}>{visual.caption}</div> : null}
      </div>
      <div style={{ position: "absolute", left: 60, bottom: 110, fontFamily: BODY, fontSize: 20, color: "rgba(255,255,255,0.75)" }}>
        Photo: {ph.author} · {ph.licence} · {ph.via || "Wikimedia Commons"}
      </div>
    </AbsoluteFill>
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
      <div style={{ position: "absolute", zIndex: 5, top: 70, left: 60, right: 60, height: 8, background: C.line, borderRadius: 4 }}>
        <div style={{ width: `${progress * 100}%`, height: "100%", background: C.accent, borderRadius: 4 }} />
      </div>
      <ShortFront hook={short.hook} channel={props.channel}
                  line={`${props.competition} · ${props.home} v ${props.away}`} />
      {(short.shots && short.shots.length ? short.shots : [{ from: 0, visual: short.visual }]).map((sh, i, arr) => {
        const next = i + 1 < arr.length ? arr[i + 1].from : speak;
        const len = Math.max(10, next - sh.from + (i + 1 < arr.length ? 8 : 0));
        const ph = sh.visual.type === "photo" ? findPhoto(props, sh.visual) : null;
        const z = ZOOM[sh.visual?.type] || 0.6;
        return (
          <Sequence key={i} from={sh.from} durationInFrames={len}>
            <VShot len={len}>
              {ph ? <VPhoto ph={ph} visual={sh.visual} len={len} /> : (
                <div style={{ position: "absolute", top: BOX_TOP, left: 0, width: 1080, height: BOX_H, overflow: "hidden",
                              opacity: visIn * (1 - endIn) }}>
                  <div style={{ width: 1920, height: 1080, position: "absolute",
                                left: (1080 - 1920 * z) / 2, top: (BOX_H - 1080 * z) / 2,
                                transform: `scale(${z})`, transformOrigin: "top left" }}>
                    <SceneVisual scene={{ ...scene, visual: sh.visual, durationInFrames: len }} props={props} />
                  </div>
                </div>
              )}
            </VShot>
          </Sequence>
        );
      })}
      <NameTags tags={short.tags} channel={props.channel} left={60} bottom={480} scale={1.3} />
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
      <Crowd cues={short.crowd} volume={props.crowdVolume} />
      <Audio src={staticFile("sfx/whoosh.wav")} volume={0.35} />
      <Sequence from={speak}><Audio src={staticFile("sfx/hit.wav")} volume={0.45} /></Sequence>
    </AbsoluteFill>
  );
};
