import { Sequence } from "remotion";
import { Clipping } from "./Newspaper";

// When the narration first names a player or coach, his photo appears as a clipping from the paper.
const TAG = 90; // 3 s

export const NameTags = ({ tags, channel = "The Other Touchline", left = 70, bottom = 200, scale = 1 }) => (
  <>
    {(tags || []).map((t, i) => (
      <Sequence key={i} from={t.from} durationInFrames={TAG} layout="none">
        <div style={{ position: "absolute", left, bottom, zIndex: 7 }}>
          <Clipping t={t} s={scale} channel={channel} frames={TAG} />
        </div>
      </Sequence>
    ))}
  </>
);
