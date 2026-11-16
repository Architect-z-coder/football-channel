import { Composition } from "remotion";
import { Match } from "./Match";
import { FPS } from "./theme";
import sample from "./sample-props.json";

export const Root = () => (
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
);
