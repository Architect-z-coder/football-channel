import "@fontsource/anton/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/700.css";
import "@fontsource/inter/800.css";

export const C = {
  bg: "#07110C",
  bg2: "#0F2419",
  panel: "rgba(255,255,255,0.06)",
  line: "rgba(255,255,255,0.10)",
  text: "#F4F6F5",
  muted: "#93A79B",
  accent: "#F2C14E",
  home: "#E8EDF2",
  away: "#4FB3BF",
  win: "#3FB66B",
  draw: "#8A9A90",
  loss: "#D64545",
};

export const HEAD = "Anton, Impact, sans-serif";
export const BODY = "Inter, Arial, sans-serif";

export const FPS = 30;

// "62%" -> {n: 62, suffix: "%", decimals: 0}; "1.42" -> {n: 1.42, decimals: 2}
export function parseNum(v) {
  if (v === null || v === undefined) return null;
  const m = String(v).match(/-?\d+(?:\.(\d+))?/);
  if (!m) return null;
  return {
    n: parseFloat(m[0]),
    decimals: m[1] ? m[1].length : 0,
    prefix: String(v).slice(0, m.index),
    suffix: String(v).slice(m.index + m[0].length),
  };
}

export function fmt(p, value) {
  if (!p) return "";
  return `${p.prefix}${value.toFixed(p.decimals)}${p.suffix}`;
}
