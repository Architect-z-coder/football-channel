import { Composition } from "remotion";
import { Match } from "./Match";
import { Short } from "./Short";
import { FPS } from "./theme";
import sample from "./sample-props.json";

export const Root = () => (
  <>
  <Composition
    id="Match"
    component={Match}
    fps={FPS}
    width={1920}
    height={1080}
    durationInFrames={300}
    defaultProps={sample}
    calculateMetadata={({ props }) => ({
      durationInFrames: Math.max(
        30,
        props.scenes.reduce((sum, s) => sum + s.durationInFrames, 0)
      ),
    })}
  />
  <Composition
    id="Short"
    component={Short}
    fps={FPS}
    width={1080}
    height={1920}
    durationInFrames={600}
    defaultProps={{ ...sample, short: { hook: "Sample hook", narration: "Sample narration.",
      visual: { type: "scoreline" }, audio: "sfx/hit.wav", durationInFrames: 120 } }}
    calculateMetadata={({ props }) => ({ durationInFrames: props.short.durationInFrames })}
  />
  </>
);
