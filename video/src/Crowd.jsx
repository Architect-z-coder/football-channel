import { Audio, Sequence, interpolate, staticFile } from "remotion";

// Stadium reactions: an "ooh" on a save or miss, a roar on a goal. Fades out after ~3.5 s.
const LEN = 110;

export const Crowd = ({ cues, volume = 0.32 }) => (
  <>
    {(cues || []).map((c, i) => (
      <Sequence key={i} from={Math.max(0, c.from - 6)} durationInFrames={LEN} layout="none">
        <Audio src={staticFile(`sfx/crowd_${c.kind}.mp3`)}
               volume={(f) => interpolate(f, [0, 8, LEN - 35, LEN], [0, volume * (c.kind === "roar" ? 1.1 : 1), volume, 0],
                                          { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      </Sequence>
    ))}
  </>
);

// Fans singing (voices only, original wordless chant): under the opening and the ending, ~10 s each.
const SING = 300;
const singVol = (v) => (f) => interpolate(f, [0, 45, SING - 75, SING], [0, v, v, 0],
                                          { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

export const CrowdSinging = ({ total, volume = 0.3 }) => (
  <>
    <Sequence from={0} durationInFrames={SING} layout="none">
      <Audio src={staticFile("sfx/crowd_sing.mp3")} volume={singVol(volume)} />
    </Sequence>
    {total > SING * 3 ? (
      <Sequence from={total - SING} durationInFrames={SING} layout="none">
        <Audio src={staticFile("sfx/crowd_sing.mp3")} volume={singVol(volume)} />
      </Sequence>
    ) : null}
  </>
);
