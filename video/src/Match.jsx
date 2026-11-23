import {
  AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame,
  useVideoConfig, Easing,
} from "remotion";
import { C, HEAD, BODY } from "./theme";
import { NameTags } from "./NameTag";
import { Crowd, CrowdSinging } from "./Crowd";
import { Headline } from "./Newspaper";
import { SceneVisual, FullPhoto, findPhoto } from "./scenes";

// 3D boards and replays use the whole frame
const FULL = new Set(["tactics_board", "goal_replay"]);
// Where the numbers or the report come from: shown, never spoken
const SourceTag = ({ text }) => (
  <div style={{ position: "absolute", left: 60, bottom: 236, fontFamily: BODY, fontSize: 22, fontWeight: 700,
                color: "rgba(255,255,255,0.75)", background: "rgba(0,0,0,0.45)", padding: "6px 14px", borderRadius: 8,
                letterSpacing: 1 }}>Source: {text}</div>
);

const TAIL = 12; // frames of silence at the end of each scene (matches Python PAD)

// ---------- background: slow-moving light and faint pitch markings ----------
const Background = () => {
  const f = useCurrentFrame();
  const x = 50 + 18 * Math.sin(f / 240);
  const y = 40 + 12 * Math.cos(f / 300);
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at ${x}% ${y}%, ${C.bg2} 0%, ${C.bg} 60%)`,
        }}
      />
      <svg width="1920" height="1080" style={{ position: "absolute", opacity: 0.07 }}>
        <g transform={`rotate(${f / 40} 960 540)`} stroke="#fff" strokeWidth="3" fill="none">
          <circle cx="960" cy="540" r="260" />
          <line x1="960" y1="-400" x2="960" y2="1480" />
          <circle cx="960" cy="540" r="8" fill="#fff" />
        </g>
      </svg>
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.35) 0%, rgba(0,0,0,0) 20%, rgba(0,0,0,0) 70%, rgba(0,0,0,0.55) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};

// ---------- top bar + progress bar ----------
const TopBar = ({ channel, competition, home, away, total }) => {
  const f = useCurrentFrame();
  const progress = Math.min(1, f / total);
  return (
    <>
      <div style={{
        position: "absolute", top: 34, left: 60, right: 60, display: "flex",
        justifyContent: "space-between", alignItems: "center", fontFamily: BODY,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 14, height: 14, borderRadius: 7, background: C.accent }} />
          <span style={{ color: C.text, fontWeight: 800, fontSize: 24, letterSpacing: 3 }}>
            {channel.toUpperCase()}
          </span>
        </div>
        <span style={{ color: C.muted, fontWeight: 700, fontSize: 22, letterSpacing: 2 }}>
          {competition.toUpperCase()} · {home.toUpperCase()} v {away.toUpperCase()}
        </span>
      </div>
      <div style={{ position: "absolute", top: 82, left: 60, right: 60, height: 4,
                    background: C.line, borderRadius: 2 }}>
        <div style={{ width: `${progress * 100}%`, height: "100%", background: C.accent,
                      borderRadius: 2 }} />
      </div>
    </>
  );
};

// ---------- kinetic captions: words appear and the spoken word lights up ----------
export const Captions = ({ text, speakFrames, wordStarts, per = 7, size = 50, bottom = 70, maxWidth = 1500 }) => {
  const f = useCurrentFrame();
  const words = text.split(/\s+/).filter(Boolean);
  if (!words.length) return null;
  // exact timings from the voice when we have them (seconds -> frames)
  const exact = Array.isArray(wordStarts) && wordStarts.length === words.length;
  // otherwise weight each word by length so long words take longer
  const weights = words.map((w) => 1 + w.replace(/[^\w]/g, "").length * 0.18);
  const totalW = weights.reduce((a, b) => a + b, 0);
  let acc = 0;
  const starts = exact ? wordStarts.map((t) => t * 30) : weights.map((w) => {
    const s = (acc / totalW) * speakFrames;
    acc += w;
    return s;
  });
  let current = starts.findIndex((s, i) => f >= s && (i === words.length - 1 || f < starts[i + 1]));
  if (current < 0) current = f < starts[0] ? 0 : words.length - 1;

  const PER = per; // words per caption line
  const lineStart = Math.floor(current / PER) * PER;
  const line = words.slice(lineStart, lineStart + PER);
  return (
    <div style={{
      position: "absolute", bottom, left: 0, right: 0, display: "flex",
      justifyContent: "center", fontFamily: BODY,
    }}>
      <div style={{
        background: "rgba(0,0,0,0.55)", padding: "16px 30px", borderRadius: 16,
        display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center", maxWidth,
      }}>
        {line.map((w, i) => {
          const idx = lineStart + i;
          const active = idx === current;
          const shown = f >= starts[idx] - 2;
          const pop = spring({ frame: f - starts[idx], fps: 30, config: { damping: 12, mass: 0.4 } });
          return (
            <span key={idx} style={{
              fontSize: size, fontWeight: 800, color: active ? C.accent : C.text,
              opacity: shown ? 1 : 0.25,
              transform: `scale(${active ? 1 + 0.08 * pop : 1})`,
              display: "inline-block", textShadow: "0 4px 18px rgba(0,0,0,0.6)",
            }}>{w}</span>
          );
        })}
      </div>
    </div>
  );
};

// ---------- shots: crossfade between pictures; graphics sit on a dark stadium backdrop ----------
const ShotFade = ({ len, last, exit, children }) => {
  const f = useCurrentFrame();
  const a = interpolate(f, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  const b = last ? exit : interpolate(f, [len - 8, len], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity: Math.min(a, b) }}>{children}</AbsoluteFill>;
};

const Backdrop = ({ props, sceneId = 0 }) => {
  const f = useCurrentFrame();
  const all = props.photos || [];
  const inside = all.filter((p) => p.role === "Stadium inside");
  const st = inside.length ? inside[sceneId % inside.length] : all.find((p) => p.role === "Stadium");
  if (!st) return null;
  return (
    <AbsoluteFill>
      <Img src={staticFile(`run/${st.file}`)} onError={() => {}} style={{ width: "100%", height: "100%", objectFit: "cover",
           filter: "blur(10px) brightness(0.28) saturate(0.7)", transform: `scale(${1.1 + f / 3000})` }} />
    </AbsoluteFill>
  );
};

// ---------- one scene: slide in, hold, fade out ----------
const SceneShell = ({ scene, props }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dur = scene.durationInFrames;
  const enter = spring({ frame: f, fps, config: { damping: 18, mass: 0.7 } });
  const exit = interpolate(f, [dur - 8, dur], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.in(Easing.cubic),
  });
  const kicker = scene.on_screen;
  const shots = scene.shots || [];
  return (
    <AbsoluteFill>
      {shots.map((sh, i) => {
        const next = i + 1 < shots.length ? shots[i + 1].from : dur;
        const len = next - sh.from + (i + 1 < shots.length ? 8 : 0);   // small overlap for a crossfade
        const isPhoto = sh.visual.type === "photo" && findPhoto(props, sh.visual);
        return (
          <Sequence key={i} from={sh.from} durationInFrames={Math.max(len, 10)}>
            <ShotFade len={Math.max(len, 10)} last={i + 1 === shots.length} exit={exit}>
              {isPhoto ? <FullPhoto visual={sh.visual} props={props} dur={len} /> : (
                <AbsoluteFill>
                  <Backdrop props={props} sceneId={scene.id} />
                  <div style={FULL.has(sh.visual.type) ? { position: "absolute", top: 110, bottom: 0, left: 0, right: 0 }
                                                       : { position: "absolute", top: 160, bottom: 230, left: 0, right: 0 }}>
                    <SceneVisual scene={{ ...scene, visual: sh.visual, durationInFrames: len }} props={props} />
                  </div>
                  {sh.visual.source ? <SourceTag text={sh.visual.source} /> : null}
                </AbsoluteFill>
              )}
            </ShotFade>
          </Sequence>
        );
      })}
      <AbsoluteFill style={{
        opacity: enter * exit,
        transform: `translateX(${(1 - enter) * 160}px) scale(${0.96 + 0.04 * exit})`,
      }}>
        {kicker ? (
          <Headline text={kicker} channel={props.channel} sceneNo={scene.id}
                    kicker={`${props.competition} · ${props.home} v ${props.away}`} />
        ) : null}
        {scene.shots && scene.shots.length ? null : (
          <div style={{ position: "absolute", top: 160, bottom: 230, left: 0, right: 0 }}>
            <SceneVisual scene={scene} props={props} />
          </div>
        )}
      </AbsoluteFill>
      <NameTags tags={scene.tags} channel={props.channel} />
      <Captions text={scene.narration} speakFrames={Math.max(15, dur - TAIL)} wordStarts={scene.wordStarts} />
    </AbsoluteFill>
  );
};

export const Match = (props) => {
  let from = 0;
  const total = props.scenes.reduce((s, x) => s + x.durationInFrames, 0);
  return (
    <AbsoluteFill style={{ fontFamily: BODY }}>
      <Background />
      {props.scenes.map((scene) => {
        const seq = (
          <Sequence key={scene.id} from={from} durationInFrames={scene.durationInFrames}>
            <SceneShell scene={scene} props={props} />
            {scene.audio ? <Audio src={staticFile(scene.audio)} /> : null}
            <Crowd cues={scene.crowd} volume={props.crowdVolume} />
            <Audio src={staticFile("sfx/whoosh.wav")} volume={0.35} />
            {["key_number", "scoreline", "halftime_fulltime"].includes(scene.visual?.type) ? (
              <Sequence from={14}><Audio src={staticFile("sfx/hit.wav")} volume={0.45} /></Sequence>
            ) : null}
          </Sequence>
        );
        from += scene.durationInFrames;
        return seq;
      })}
      <CrowdSinging total={total} volume={props.crowdVolume} />
      <TopBar channel={props.channel} competition={props.competition} home={props.home}
              away={props.away} total={total} />
      <div style={{ position: "absolute", bottom: 26, right: 60, color: C.muted,
                    fontFamily: BODY, fontSize: 18, fontWeight: 500 }}>
        Data: {props.source}
      </div>
    </AbsoluteFill>
  );
};
