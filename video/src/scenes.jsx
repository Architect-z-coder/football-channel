import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { C, HEAD, BODY, parseNum, fmt } from "./theme";
import { PressCut } from "./Newspaper";

// ---------- helpers ----------
const useSpring = (delay = 0, config = { damping: 14, mass: 0.6 }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: f - delay, fps, config });
};

const CountUp = ({ value, delay = 0, frames = 28, style }) => {
  const f = useCurrentFrame();
  const p = parseNum(value);
  if (!p) return <span style={style}>{value ?? "–"}</span>;
  const t = interpolate(f - delay, [0, frames], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic),
  });
  return <span style={style}>{fmt(p, p.n * t)}</span>;
};

const Center = ({ children, style }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", ...style }}>
    {children}
  </AbsoluteFill>
);

const facts = (props) => props.facts || {};

// ---------- scene types ----------
const TitleCard = ({ visual }) => {
  const words = (visual.title || "").split(" ");
  const sub = useSpring(12 + words.length * 3);
  return (
    <Center style={{ padding: "0 160px", textAlign: "center" }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0 26px", justifyContent: "center" }}>
        {words.map((w, i) => <Word key={i} w={w} delay={i * 3} />)}
      </div>
      <div style={{ marginTop: 30, fontFamily: BODY, fontWeight: 700, fontSize: 40,
                    color: C.accent, opacity: sub, transform: `translateY(${(1 - sub) * 30}px)` }}>
        {visual.subtitle}
      </div>
    </Center>
  );
};

const Word = ({ w, delay }) => {
  const s = useSpring(delay);
  return (
    <span style={{ fontFamily: HEAD, fontSize: 120, color: C.text, lineHeight: 1.05,
                   display: "inline-block", opacity: s, transform: `translateY(${(1 - s) * 60}px)` }}>
      {w}
    </span>
  );
};

const KeyNumber = ({ visual }) => {
  const s = useSpring(0, { damping: 10, mass: 0.5 });
  const ring = useSpring(6, { damping: 30 });
  const lbl = useSpring(18);
  return (
    <Center>
      <div style={{ position: "relative", display: "flex", alignItems: "center",
                    justifyContent: "center" }}>
        <div style={{ position: "absolute", width: 620, height: 620, borderRadius: 310,
                      border: `6px solid ${C.accent}`, opacity: 0.25 * ring,
                      transform: `scale(${0.6 + 0.4 * ring})` }} />
        <CountUp value={visual.value} frames={30} style={{
          fontFamily: HEAD, fontSize: 290, color: C.accent, lineHeight: 1,
          transform: `scale(${0.7 + 0.3 * s})`, display: "inline-block",
          textShadow: "0 10px 60px rgba(242,193,78,0.35)",
        }} />
      </div>
      <div style={{ marginTop: 20, fontFamily: BODY, fontWeight: 700, fontSize: 46, color: C.text,
                    opacity: lbl, transform: `translateY(${(1 - lbl) * 24}px)`, maxWidth: 1300,
                    textAlign: "center" }}>
        {visual.label}
      </div>
    </Center>
  );
};

const TeamName = ({ name, color, from, delay }) => {
  const s = useSpring(delay);
  return (
    <div style={{ width: 560, textAlign: "center", fontFamily: HEAD, fontSize: 92, color,
                  lineHeight: 1.05, opacity: s, transform: `translateX(${(1 - s) * from}px)` }}>
      {name}
    </div>
  );
};

const Scoreline = ({ props }) => {
  const F = facts(props);
  const score = useSpring(12, { damping: 9, mass: 0.6 });
  const meta = useSpring(22);
  return (
    <Center>
      <div style={{ fontFamily: BODY, fontWeight: 800, fontSize: 30, color: C.muted,
                    letterSpacing: 4, marginBottom: 30 }}>{props.competition.toUpperCase()}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
        <TeamName name={props.home} color={C.home} from={-400} delay={0} />
        <div style={{ fontFamily: HEAD, fontSize: 230, color: C.text, minWidth: 420,
                      textAlign: "center", transform: `scale(${2 - score})`, opacity: score }}>
          {F.score_home} – {F.score_away}
        </div>
        <TeamName name={props.away} color={C.away} from={400} delay={4} />
      </div>
      <div style={{ marginTop: 30, fontFamily: BODY, fontWeight: 600, fontSize: 30,
                    color: C.muted, opacity: meta }}>
        {[F.round || (F.matchday ? `Matchday ${F.matchday}` : null), F.date].filter(Boolean).join("  ·  ")}
      </div>
    </Center>
  );
};

const HalfFull = ({ props, scene }) => {
  const F = facts(props);
  const ht = useSpring(4);
  const ftDelay = Math.round(scene.durationInFrames * 0.35);
  const ft = useSpring(ftDelay, { damping: 9, mass: 0.6 });
  const Row = ({ label, h, a, s, gold }) => (
    <div style={{ display: "flex", alignItems: "center", gap: 50, opacity: s,
                  transform: `translateY(${(1 - s) * 40}px) scale(${gold ? 0.8 + 0.2 * s : 1})` }}>
      <span style={{ width: 300, textAlign: "right", fontFamily: BODY, fontWeight: 800,
                     fontSize: 34, letterSpacing: 4, color: C.muted }}>{label}</span>
      <span style={{ fontFamily: HEAD, fontSize: 170, color: gold ? C.accent : C.text }}>
        {h} – {a}
      </span>
      <span style={{ width: 300 }} />
    </div>
  );
  return (
    <Center>
      <div style={{ display: "flex", gap: 360, fontFamily: HEAD, fontSize: 60, marginBottom: 10 }}>
        <span style={{ color: C.home }}>{props.home}</span>
        <span style={{ color: C.away }}>{props.away}</span>
      </div>
      <Row label="HALF TIME" h={F.ht_home} a={F.ht_away} s={ht} />
      <Row label="FULL TIME" h={F.score_home} a={F.score_away} s={ft} gold />
    </Center>
  );
};

const labelOf = (key) =>
  key.replace(/_/g, " ").replace("pct", "%").replace(/\b\w/g, (c) => c.toUpperCase());

const StatRow = ({ label, hv, av, delay }) => {
  const s = useSpring(delay, { damping: 20 });
  const hp = parseNum(hv)?.n ?? 0;
  const ap = parseNum(av)?.n ?? 0;
  const total = hp + ap || 1;
  const W = 1100;
  return (
    <div style={{ marginBottom: 22, opacity: Math.min(1, s * 1.5) }}>
      <div style={{ textAlign: "center", fontFamily: BODY, fontWeight: 700, fontSize: 30,
                    color: C.muted, marginBottom: 10 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
        <CountUp value={hv} delay={delay} style={{ width: 170, textAlign: "right", fontFamily: HEAD,
                 fontSize: 64, color: C.home }} />
        <div style={{ width: W, height: 34, display: "flex", background: C.line, borderRadius: 17,
                      overflow: "hidden" }}>
          <div style={{ width: (W * hp / total) * s, background: C.home }} />
          <div style={{ flex: 1 }} />
          <div style={{ width: (W * ap / total) * s, background: C.away }} />
        </div>
        <CountUp value={av} delay={delay} style={{ width: 170, fontFamily: HEAD, fontSize: 64,
                 color: C.away }} />
      </div>
    </div>
  );
};

const StatBars = ({ visual, props }) => {
  const F = facts(props);
  const keys = (visual.stats || []).filter((k) => `home_${k}` in F && `away_${k}` in F).slice(0, 3);
  return (
    <Center>
      <div style={{ display: "flex", justifyContent: "space-between", width: 1500, fontFamily: HEAD,
                    fontSize: 54, marginBottom: 16 }}>
        <span style={{ color: C.home }}>{props.home}</span>
        <span style={{ color: C.away }}>{props.away}</span>
      </div>
      {keys.map((k, i) => (
        <StatRow key={k} label={labelOf(k)} hv={F[`home_${k}`]} av={F[`away_${k}`]} delay={6 + i * 10} />
      ))}
    </Center>
  );
};

const Grid = ({ title, cols, rows }) => {
  const head = useSpring(0);
  return (
    <Center>
      <div style={{ fontFamily: HEAD, fontSize: 70, color: C.text, marginBottom: 30, opacity: head }}>
        {title}
      </div>
      <div style={{ display: "flex", marginLeft: 440, gap: 0, marginBottom: 12 }}>
        {cols.map((c) => (
          <div key={c} style={{ width: 150, textAlign: "center", fontFamily: BODY, fontWeight: 800,
                                fontSize: 28, color: C.muted, letterSpacing: 2 }}>{c}</div>
        ))}
      </div>
      {rows.map((r, ri) => <GridRow key={ri} row={r} delay={8 + ri * 10} />)}
    </Center>
  );
};

const GridRow = ({ row, delay }) => {
  const s = useSpring(delay);
  return (
    <div style={{ display: "flex", alignItems: "center", background: C.panel, borderRadius: 18,
                  padding: "22px 30px", marginBottom: 18, opacity: s,
                  transform: `translateX(${(1 - s) * -120}px)` }}>
      <div style={{ width: 410, fontFamily: HEAD, fontSize: 58, color: row.color }}>{row.name}</div>
      {row.values.map((v, i) => (
        <CountUp key={i} value={v} delay={delay + 4 + i * 2} style={{
          width: 150, textAlign: "center", fontFamily: HEAD, fontSize: 64,
          color: row.highlight === i ? C.accent : C.text }} />
      ))}
    </div>
  );
};

const TableSnapshot = ({ props }) => {
  const F = facts(props);
  const keys = [["Pos", "position"], ["Pts", "points"], ["P", "played_games"], ["W", "won"],
                ["D", "draw"], ["L", "lost"], ["GF", "goals_for"], ["GA", "goals_against"]];
  const rows = [["home", C.home], ["away", C.away]].map(([s, color]) => ({
    name: props[s], color, highlight: 1, values: keys.map(([, k]) => F[`${s}_${k}`] ?? "–"),
  }));
  return <Grid title="The league table" cols={keys.map(([c]) => c)} rows={rows} />;
};

const FormChips = ({ w, d, l, delay }) => {
  const f = useCurrentFrame();
  const chips = [...Array(w || 0).fill("W"), ...Array(d || 0).fill("D"), ...Array(l || 0).fill("L")];
  const color = { W: C.win, D: C.draw, L: C.loss };
  return (
    <div style={{ display: "flex", gap: 14 }}>
      {chips.map((c, i) => {
        const s = spring({ frame: f - delay - i * 4, fps: 30, config: { damping: 10, mass: 0.4 } });
        return (
          <div key={i} style={{ width: 84, height: 84, borderRadius: 42, background: color[c],
                                display: "flex", alignItems: "center", justifyContent: "center",
                                fontFamily: HEAD, fontSize: 46, color: "#fff",
                                transform: `scale(${s})` }}>{c}</div>
        );
      })}
    </div>
  );
};

const FormCompare = ({ props }) => {
  const F = facts(props);
  const head = useSpring(0);
  return (
    <Center>
      <div style={{ fontFamily: HEAD, fontSize: 66, color: C.text, marginBottom: 40, opacity: head }}>
        Form: the 5 matches before this one
      </div>
      {[["home", C.home], ["away", C.away]].map(([s, color], i) => (
        <div key={s} style={{ display: "flex", alignItems: "center", gap: 40, marginBottom: 34,
                              background: C.panel, padding: "24px 40px", borderRadius: 20 }}>
          <div style={{ width: 400, fontFamily: HEAD, fontSize: 58, color }}>{props[s]}</div>
          <FormChips w={F[`${s}_last5_wins`]} d={F[`${s}_last5_draws`]} l={F[`${s}_last5_losses`]}
                     delay={10 + i * 14} />
          <div style={{ width: 260, fontFamily: BODY, fontWeight: 700, fontSize: 32, color: C.muted,
                        textAlign: "right" }}>
            <CountUp value={F[`${s}_last5_goals_for`]} delay={20 + i * 14}
                     style={{ fontFamily: HEAD, fontSize: 52, color: C.text }} /> scored{" "}
            <br />
            <CountUp value={F[`${s}_last5_goals_against`]} delay={20 + i * 14}
                     style={{ fontFamily: HEAD, fontSize: 52, color: C.text }} /> conceded
          </div>
        </div>
      ))}
    </Center>
  );
};

const EventsTimeline = ({ props, scene }) => {
  const f = useCurrentFrame();
  const events = (props.events || []).filter((e) => e.kind === "goal" || e.kind === "red");
  const end = Math.max(90, ...events.map((e) => e.minute || 0));
  const draw = interpolate(f, [0, scene.durationInFrames * 0.6], [0, 1], {
    extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const X0 = 160, X1 = 1760, Y = 360;
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", top: 40, width: "100%", textAlign: "center",
                    fontFamily: HEAD, fontSize: 66, color: C.text }}>How the match unfolded</div>
      <svg width="1920" height="720" style={{ position: "absolute" }}>
        <line x1={X0} y1={Y} x2={X0 + (X1 - X0) * draw} y2={Y} stroke={C.muted} strokeWidth="6"
              strokeLinecap="round" />
        {[0, 45, 90].map((m) => (
          <text key={m} x={X0 + (X1 - X0) * m / end} y={Y + 60} fill={C.muted} fontSize="30"
                fontFamily={BODY} textAnchor="middle">{m}'</text>
        ))}
      </svg>
      {events.map((e, i) => {
        const pos = (e.minute || 0) / end;
        const s = spring({ frame: f - pos * scene.durationInFrames * 0.6, fps: 30,
                           config: { damping: 10, mass: 0.5 } });
        const up = e.side === "home" ? -1 : 1;
        const color = e.kind === "red" ? C.loss : e.side === "home" ? C.home : C.away;
        return (
          <div key={i} style={{ position: "absolute", left: X0 + (X1 - X0) * pos - 150, top: Y - 30,
                                width: 300, display: "flex", flexDirection: "column",
                                alignItems: "center", transform: `scale(${s})` }}>
            <div style={{ width: 60, height: 60, borderRadius: e.kind === "red" ? 8 : 30,
                          background: color, border: `6px solid ${C.bg}` }} />
            <div style={{ position: "absolute", top: up < 0 ? -110 : 90, textAlign: "center",
                          fontFamily: BODY, fontWeight: 800, fontSize: 30, color }}>
              {e.minute}'{e.extra ? `+${e.extra}` : ""}<br />{e.player || ""}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const formationPoints = (formation, right) => {
  const rows = (formation || "4-4-2").split("-").map(Number).filter(Boolean);
  const pts = [[4, 50]];
  rows.forEach((n, r) => {
    const x = rows.length > 1 ? 12 + r * (30 / (rows.length - 1)) : 28;
    for (let j = 0; j < n; j++) pts.push([x, (100 * (j + 1)) / (n + 1)]);
  });
  return right ? pts : pts.map(([x, y]) => [100 - x, y]);
};

const Formations = ({ props }) => {
  const F = facts(props);
  const f = useCurrentFrame();
  const PW = 1100, PH = 520;
  return (
    <Center>
      <div style={{ display: "flex", justifyContent: "space-between", width: PW, fontFamily: HEAD,
                    fontSize: 48, marginBottom: 16 }}>
        <span style={{ color: C.home }}>{props.home} {F.home_formation}</span>
        <span style={{ color: C.away }}>{F.away_formation} {props.away}</span>
      </div>
      <div style={{ position: "relative", width: PW, height: PH, background: "#123222",
                    border: `4px solid ${C.line}`, borderRadius: 12 }}>
        <div style={{ position: "absolute", left: PW / 2 - 2, top: 0, bottom: 0, width: 4,
                      background: C.line }} />
        <div style={{ position: "absolute", left: PW / 2 - 90, top: PH / 2 - 90, width: 180,
                      height: 180, borderRadius: 90, border: `4px solid ${C.line}` }} />
        {[["home", C.home, true], ["away", C.away, false]].map(([s, color, right]) =>
          formationPoints(F[`${s}_formation`], right).map(([x, y], i) => {
            const p = spring({ frame: f - i * 2 - (right ? 0 : 6), fps: 30, config: { damping: 14 } });
            const cx = PW / 2 + ((x / 100) * PW - PW / 2) * p;
            const cy = PH / 2 + ((y / 100) * PH - PH / 2) * p;
            return <div key={s + i} style={{ position: "absolute", left: cx - 22, top: cy - 22,
                       width: 44, height: 44, borderRadius: 22, background: color,
                       border: `4px solid ${C.bg}` }} />;
          })
        )}
      </div>
    </Center>
  );
};

const TextCard = ({ visual }) => {
  const head = useSpring(0);
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: "0 160px" }}>
      <div style={{ fontFamily: HEAD, fontSize: 110, color: C.accent, opacity: head,
                    transform: `translateX(${(1 - head) * -80}px)`, marginBottom: 40 }}>
        {visual.heading}
      </div>
      {(visual.lines || []).slice(0, 3).map((l, i) => <Line key={i} text={l} delay={10 + i * 9} />)}
    </AbsoluteFill>
  );
};

const Line = ({ text, delay, index }) => {
  const s = useSpring(delay);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 26, marginBottom: 26, opacity: s,
                  transform: `translateX(${(1 - s) * 100}px)` }}>
      {index !== undefined ? (
        <div style={{ width: 76, height: 76, borderRadius: 38, background: C.accent, color: C.bg,
                      fontFamily: HEAD, fontSize: 46, display: "flex", alignItems: "center",
                      justifyContent: "center" }}>{index}</div>
      ) : (
        <div style={{ width: 18, height: 18, borderRadius: 9, background: C.accent }} />
      )}
      <span style={{ fontFamily: BODY, fontWeight: 700, fontSize: 56, color: C.text }}>{text}</span>
    </div>
  );
};

const LessonList = ({ visual, scene }) => {
  const head = useSpring(0);
  const items = (visual.items || []).slice(0, 3);
  const gap = Math.max(12, Math.floor((scene.durationInFrames * 0.6) / Math.max(1, items.length)));
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: "0 160px" }}>
      <div style={{ fontFamily: HEAD, fontSize: 110, color: C.accent, opacity: head, marginBottom: 40 }}>
        The lesson
      </div>
      {items.map((t, i) => <Line key={i} text={t} delay={8 + i * gap} index={i + 1} />)}
    </AbsoluteFill>
  );
};

// ---------- Understat: shot map ----------
const ShotMap = ({ props, scene }) => {
  const f = useCurrentFrame();
  const shots = props.shots || [];
  const F = facts(props);
  const W = 920, H = 596;
  const span = scene.durationInFrames * 0.65;
  const maxMin = Math.max(90, ...shots.map((s) => s.minute));
  return (
    <Center>
      <div style={{ display: "flex", justifyContent: "space-between", width: W, fontFamily: HEAD,
                    fontSize: 44, marginBottom: 10 }}>
        <span style={{ color: C.home }}>{props.home} <CountUp value={F.home_xg} frames={span}
              style={{ color: C.text }} /> xG</span>
        <span style={{ color: C.away }}>xG <CountUp value={F.away_xg} frames={span}
              style={{ color: C.text }} /> {props.away}</span>
      </div>
      <svg width={W} height={H} style={{ background: "#123222", borderRadius: 12 }}>
        <g stroke="rgba(255,255,255,0.22)" strokeWidth="3" fill="none">
          <rect x="2" y="2" width={W - 4} height={H - 4} rx="10" />
          <line x1={W / 2} y1="0" x2={W / 2} y2={H} />
          <circle cx={W / 2} cy={H / 2} r="90" />
          <rect x="0" y={H * 0.2} width={W * 0.16} height={H * 0.6} />
          <rect x={W * 0.84} y={H * 0.2} width={W * 0.16} height={H * 0.6} />
          <rect x="0" y={H * 0.37} width={W * 0.055} height={H * 0.26} />
          <rect x={W * 0.945} y={H * 0.37} width={W * 0.055} height={H * 0.26} />
        </g>
        {shots.map((s, i) => {
          const home = s.side === "home";
          const cx = (home ? s.x : 1 - s.x) * W;
          const cy = (home ? 1 - s.y : s.y) * H;
          const appear = (s.minute / maxMin) * span;
          const p = spring({ frame: f - appear, fps: 30, config: { damping: 10, mass: 0.5 } });
          const r = 8 + 52 * Math.sqrt(s.xg);
          const goal = s.result === "Goal";
          const color = home ? C.home : C.away;
          return (
            <g key={i} transform={`translate(${cx} ${cy}) scale(${p})`}>
              <circle r={r} fill={goal ? C.accent : color} fillOpacity={goal ? 1 : 0.35}
                      stroke={color} strokeWidth={goal ? 7 : 3} />
            </g>
          );
        })}
      </svg>
      <div style={{ marginTop: 10, fontFamily: BODY, fontWeight: 600, fontSize: 24, color: C.muted }}>
        Bigger circle = better chance (xG) · gold = goal · data: Understat
      </div>
    </Center>
  );
};

// ---------- Understat: xG race ----------
const XgTimeline = ({ props, scene }) => {
  const f = useCurrentFrame();
  const shots = props.shots || [];
  const W = 1500, H = 520, PAD = 60, RIGHT = 330;
  const maxMin = Math.max(90, ...shots.map((s) => s.minute + 2));
  const cum = (side) => {
    let total = 0;
    const pts = [[0, 0]];
    shots.filter((s) => s.side === side).forEach((s) => {
      pts.push([s.minute, total]);
      total += s.xg;
      pts.push([s.minute, total]);
    });
    pts.push([maxMin, total]);
    return { pts, total };
  };
  const home = cum("home"), away = cum("away");
  const maxY = Math.max(1, home.total, away.total) * 1.15;
  const X = (m) => PAD + (m / maxMin) * (W - PAD - RIGHT);
  const Y = (v) => H - PAD - (v / maxY) * (H - 2 * PAD);
  const path = (pts) => pts.map(([m, v], i) => `${i ? "L" : "M"}${X(m)},${Y(v)}`).join(" ");
  const reveal = interpolate(f, [0, scene.durationInFrames * 0.7], [0, 1], {
    extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const clipW = PAD + reveal * (W - PAD - RIGHT) + 4;
  let yh = Y(home.total), ya = Y(away.total);
  if (Math.abs(yh - ya) < 56) { const mid = (yh + ya) / 2; const up = home.total >= away.total; yh = mid + (up ? -28 : 28); ya = mid + (up ? 28 : -28); }
  return (
    <Center>
      <div style={{ fontFamily: HEAD, fontSize: 62, color: C.text, marginBottom: 6 }}>
        The xG race
      </div>
      <svg width={W} height={H}>
        <defs><clipPath id="rev"><rect x="0" y="0" width={clipW} height={H} /></clipPath></defs>
        {[0, 45, 90].map((m) => (
          <g key={m}>
            <line x1={X(m)} y1={PAD} x2={X(m)} y2={H - PAD} stroke={C.line} strokeWidth="2" />
            <text x={X(m)} y={H - 18} fill={C.muted} fontSize="26" fontFamily={BODY}
                  textAnchor="middle">{m}'</text>
          </g>
        ))}
        <g clipPath="url(#rev)" fill="none" strokeWidth="8" strokeLinejoin="round">
          <path d={path(home.pts)} stroke={C.home} />
          <path d={path(away.pts)} stroke={C.away} />
          {shots.filter((s) => s.result === "Goal").map((s, i) => {
            const before = shots.filter((t) => t.side === s.side && t.minute <= s.minute)
              .reduce((a, t) => a + t.xg, 0);
            return <circle key={i} cx={X(s.minute)} cy={Y(before)} r="16" fill={C.accent}
                           stroke={C.bg} strokeWidth="5" />;
          })}
        </g>
        <text x={W - RIGHT + 24} y={yh + 14} fill={C.home} fontSize="40" fontFamily={HEAD}
              opacity={reveal > 0.95 ? 1 : 0}>{home.total.toFixed(2)} {props.home}</text>
        <text x={W - RIGHT + 24} y={ya + 14} fill={C.away} fontSize="40" fontFamily={HEAD}
              opacity={reveal > 0.95 ? 1 : 0}>{away.total.toFixed(2)} {props.away}</text>
      </svg>
      <div style={{ fontFamily: BODY, fontWeight: 600, fontSize: 24, color: C.muted }}>
        Running total of expected goals · gold = goal · data: Understat
      </div>
    </Center>
  );
};


// ---------- StatsBomb open data: history lens ----------
const LENS_LABELS = {
  record: "Record", goals_for_pm: "Goals per match", goals_against_pm: "Conceded per match",
  xg_for_pm: "xG per match", xg_against_pm: "xG against per match",
  shots_for_pm: "Shots per match", shots_against_pm: "Shots faced per match",
  possession_pct: "Possession (share of passes)", pass_completion_pct: "Pass completion",
  ppda: "PPDA (lower = more pressing)",
};
const lensValue = (facts, key) => {
  if (key === "record") return facts.wins === undefined ? null : `${facts.wins}W ${facts.draws}D ${facts.losses}L`;
  const v = facts[key];
  if (v === undefined || v === null) return null;
  return key.endsWith("_pct") ? `${v}%` : String(v);
};

const LensTile = ({ label, value, delay }) => {
  const p = useSpring(delay);
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.line}`, borderRadius: 14, padding: "18px 24px",
                  opacity: p, transform: `translateY(${(1 - p) * 30}px)` }}>
      <div style={{ fontFamily: HEAD, fontSize: 76, color: C.accent, lineHeight: 1.05 }}>
        {/\d+W/.test(value) ? value : <CountUp value={value} delay={delay} />}
      </div>
      <div style={{ fontFamily: BODY, fontWeight: 600, fontSize: 26, color: C.text }}>{label}</div>
    </div>
  );
};

const HistoryLens = ({ visual, props, scene }) => {
  const f = useCurrentFrame();
  const lens = (props.history || {})[visual.lens];
  if (!lens) return <TextCard visual={{ heading: visual.heading || scene.on_screen || "History lens", lines: [] }} />;
  const metrics = (visual.metrics || ["goals_for_pm", "xg_for_pm", "possession_pct", "ppda"])
    .filter((k) => lensValue(lens.facts, k) !== null).slice(0, 4);
  // half pitch: StatsBomb x 60..120 (attacking up), y 0..80 across
  const PW = 420, PH = 525, sx = (y) => (y / 80) * PW, sy = (x) => ((120 - x) / 60) * PH;
  const head = useSpring(0);
  const goals = lens.goal_shots || [];
  return (
    <AbsoluteFill style={{ padding: "0 90px", justifyContent: "center", gap: 22 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 22, opacity: head,
                    transform: `translateX(${(1 - head) * -40}px)` }}>
        <span style={{ fontFamily: BODY, fontWeight: 800, fontSize: 24, letterSpacing: 3, color: C.bg,
                       background: C.accent, borderRadius: 8, padding: "6px 14px" }}>HISTORY LENS</span>
        <span style={{ fontFamily: HEAD, fontSize: 64, color: C.text }}>{lens.label}</span>
        <span style={{ fontFamily: BODY, fontWeight: 500, fontSize: 24, color: C.muted }}>{lens.coverage}</span>
      </div>
      <div style={{ display: "flex", gap: 48, alignItems: "center" }}>
        <div>
          <svg width={PW} height={PH} style={{ background: "#123222", borderRadius: 12 }}>
            <g stroke="rgba(255,255,255,0.22)" strokeWidth="3" fill="none">
              <rect x="2" y="2" width={PW - 4} height={PH - 4} rx="10" />
              <rect x={sx(18)} y={sy(120)} width={sx(62) - sx(18)} height={sy(102) - sy(120)} />
              <rect x={sx(30)} y={sy(120)} width={sx(50) - sx(30)} height={sy(114) - sy(120)} />
              <path d={`M ${sx(30)} ${PH} A ${sx(10)} ${sx(10)} 0 0 1 ${sx(50)} ${PH}`} />
            </g>
            {goals.map((g, i) => {
              const appear = 10 + (i / Math.max(goals.length, 1)) * scene.durationInFrames * 0.5;
              const p = spring({ frame: f - appear, fps: 30, config: { damping: 10, mass: 0.5 } });
              return <circle key={i} cx={sx(g.y)} cy={sy(g.x)} r={(4 + 18 * Math.sqrt(g.xg)) * p}
                             fill={C.accent} fillOpacity={0.8} stroke={C.bg} strokeWidth={2} />;
            })}
          </svg>
          <div style={{ marginTop: 8, fontFamily: BODY, fontWeight: 600, fontSize: 21, color: C.muted, width: PW }}>
            Every goal ({goals.length}), sized by xG · StatsBomb open data
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, flex: 1 }}>
          {metrics.map((k, i) => (
            <LensTile key={k} label={LENS_LABELS[k] || k} value={lensValue(lens.facts, k)} delay={14 + i * 8} />
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};


// ---------- FotMob momentum: who was on top, minute by minute ----------
const Momentum = ({ props, scene }) => {
  const f = useCurrentFrame();
  const pts = props.momentum || [];
  if (!pts.length) return <TextCard visual={{ heading: scene.on_screen || "Momentum", lines: [] }} />;
  const W = 1560, H = 520, MID = H / 2, maxMin = Math.max(90, ...pts.map((p) => p.minute));
  const maxV = Math.max(1, ...pts.map((p) => Math.abs(p.value)));
  const x = (m) => (m / maxMin) * W;
  const bw = Math.max(4, W / pts.length - 3);
  const reveal = interpolate(f, [8, scene.durationInFrames * 0.6], [0, maxMin], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fromShots = (props.shots || []).filter((s) => s.result === "Goal").map((s) => ({ minute: s.minute, team: s.side }));
  const goals = fromShots.length ? fromShots
    : (props.events || []).filter((e) => e.kind === "goal").map((e) => ({ minute: e.minute, team: e.side }));
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", width: W, fontFamily: HEAD, fontSize: 40 }}>
        <span style={{ color: C.home }}>▲ {props.home.toUpperCase()} ON TOP</span>
        <span style={{ color: C.away }}>{props.away.toUpperCase()} ON TOP ▼</span>
      </div>
      <svg width={W} height={H + 40} style={{ overflow: "visible" }}>
        <line x1={0} y1={MID} x2={W} y2={MID} stroke={C.line} strokeWidth={3} />
        <line x1={x(45)} y1={0} x2={x(45)} y2={H} stroke={C.line} strokeDasharray="8 8" strokeWidth={2} />
        {pts.filter((p) => p.minute <= reveal).map((p, i) => {
          const h = (Math.abs(p.value) / maxV) * (MID - 10);
          const home = p.value > 0;
          return <rect key={i} x={x(p.minute) - bw / 2} y={home ? MID - h : MID} width={bw} height={h}
                       fill={home ? C.home : C.away} opacity={0.85} rx={2} />;
        })}
        {goals.filter((g) => g.minute <= reveal).map((g, i) => (
          <g key={`g${i}`} transform={`translate(${x(g.minute)}, ${g.team === "home" ? 14 : H - 14})`}>
            <circle r={16} fill={C.accent} />
            <text y={7} textAnchor="middle" fontFamily={BODY} fontWeight={800} fontSize={18} fill={C.bg}>⚽</text>
          </g>
        ))}
        {[0, 45, 90].map((m) => (
          <text key={m} x={x(m)} y={H + 34} textAnchor="middle" fontFamily={BODY} fontWeight={600}
                fontSize={24} fill={C.muted}>{m}'</text>
        ))}
      </svg>
      <div style={{ fontFamily: BODY, fontWeight: 600, fontSize: 22, color: C.muted }}>
        Momentum and goals · data: FotMob
      </div>
    </AbsoluteFill>
  );
};


// ---------- FotMob player ratings: best vs lowest-rated starters ----------
const ratingColor = (r) => (r >= 8 ? C.win : r >= 7 ? C.accent : r >= 6 ? C.draw : C.loss);
const RatingRow = ({ r, delay }) => {
  const f = useCurrentFrame();
  const p = spring({ frame: f - delay, fps: 30, config: { damping: 14 } });
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 22, opacity: p, transform: `translateX(${(1 - p) * 40}px)` }}>
      <div style={{ width: 120, height: 84, borderRadius: 14, background: ratingColor(r.rating), display: "flex",
                    alignItems: "center", justifyContent: "center", fontFamily: HEAD, fontSize: 56, color: C.bg }}>
        {r.rating.toFixed(1)}
      </div>
      <div>
        <div style={{ fontFamily: HEAD, fontSize: 50, color: C.text, lineHeight: 1 }}>{r.player}</div>
        <div style={{ fontFamily: BODY, fontWeight: 600, fontSize: 26, color: r.side === "home" ? C.home : C.away }}>
          {r.team}{r.subbed_off ? " · subbed off" : ""}
        </div>
      </div>
    </div>
  );
};
const PlayerRatings = ({ props }) => {
  const st = (props.ratings || []).filter((r) => r.started);
  if (!st.length) return null;
  const best = [...st].sort((a, b) => b.rating - a.rating).slice(0, 3);
  const worst = [...st].sort((a, b) => a.rating - b.rating).slice(0, 3);
  const col = (title, rows, d0) => (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 26 }}>
      <div style={{ fontFamily: BODY, fontWeight: 800, letterSpacing: 3, fontSize: 28, color: C.muted }}>{title}</div>
      {rows.map((r, i) => <RatingRow key={r.player} r={r} delay={d0 + i * 8} />)}
    </div>
  );
  return (
    <AbsoluteFill style={{ padding: "0 120px", justifyContent: "center" }}>
      <div style={{ display: "flex", gap: 80 }}>
        {col("BEST RATED", best, 6)}
        {col("LOWEST RATED STARTERS", worst, 30)}
      </div>
      <div style={{ marginTop: 34, fontFamily: BODY, fontWeight: 600, fontSize: 22, color: C.muted }}>
        Player ratings: FotMob (0-10)
      </div>
    </AbsoluteFill>
  );
};

// ---------- What the coach / player said ----------
const QuoteCard = ({ visual, props }) => {
  const f = useCurrentFrame();
  const old = visual.press_index !== undefined ? (props.press || [])[visual.press_index] : null;
  const q = old ? { quote: old.quote, speaker: old.speaker, role: old.role, outlet: (old.source || "") }
                : { quote: visual.quote, speaker: visual.speaker, role: visual.role, outlet: visual.outlet };
  if (!q.quote) return null;
  const p = spring({ frame: f - 4, fps: 30, config: { damping: 16 } });
  const words = q.quote.split(" ");
  const shown = Math.min(words.length, Math.floor(interpolate(f, [10, 10 + words.length * 4], [0, words.length],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" })));
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      {/* press-room backdrop: soft panel wall + desk + microphone (our own drawing) */}
      <div style={{ position: "absolute", inset: "40px 120px 60px", borderRadius: 24, opacity: 0.9 * p,
                    background: `repeating-linear-gradient(90deg, ${C.panel} 0 160px, #0b1912 160px 320px)` }} />
      <div style={{ position: "absolute", left: 120, right: 120, bottom: 60, height: 70, background: "#050c08",
                    borderTop: `4px solid ${C.accent}`, opacity: p }} />
      <svg width="90" height="230" style={{ position: "absolute", bottom: 128, left: 230, opacity: p }}>
        <rect x="33" y="0" width="24" height="60" rx="12" fill="#cfd6d2" />
        <rect x="42" y="58" width="6" height="140" fill="#8a948f" />
        <rect x="15" y="196" width="60" height="10" rx="4" fill="#8a948f" />
      </svg>
      <div style={{ position: "relative", maxWidth: 1250, marginLeft: 220, marginBottom: 120, opacity: p }}>
        <div style={{ fontFamily: BODY, fontWeight: 800, letterSpacing: 4, fontSize: 24, color: C.accent }}>PRESS CONFERENCE</div>
        <div style={{ fontFamily: BODY, fontWeight: 700, fontSize: q.quote.length > 120 ? 52 : 64, color: C.text,
                      lineHeight: 1.25, marginTop: 16 }}>
          “{words.slice(0, shown).join(" ")}<span style={{ opacity: 0 }}>{words.slice(shown).join(" ")}</span>”
        </div>
        <div style={{ marginTop: 34, fontFamily: HEAD, fontSize: 48, color: C.accent }}>{q.speaker}</div>
        <div style={{ fontFamily: BODY, fontWeight: 600, fontSize: 26, color: C.muted }}>
          {q.role}{q.outlet ? ` · via ${q.outlet}` : ""}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------- Goal replay: shot spot -> ball into the net, on a 2D pitch ----------
const GoalReplay = ({ visual, props, scene }) => {
  const f = useCurrentFrame();
  const goals = (props.shots || []).filter((s) => s.result === "Goal").sort((a, b) => a.minute - b.minute);
  const g = visual.minute != null
    ? goals.find((x) => x.minute === visual.minute) || goals.find((x) => Math.abs(x.minute - visual.minute) <= 1)
    : goals[visual.goal_index || 0];
  if (!g) return null;
  const info = (props.goals || []).find((x) => x.minute === g.minute && (x.player || "").includes((g.player || "").split(" ").slice(-1)[0])) || {};
  // half pitch, attacking up: x 0.5..1 (towards goal), y 0..1 across
  const PW = 980, PH = 640, gx = (y) => 60 + y * (PW - 120), gy = (x) => PH - ((x - 0.5) / 0.5) * (PH - 40);
  const sx = gx(g.y), sy = gy(g.x), tx = gx(g.goal_y ?? 0.5), ty = gy(1) + 6;
  const t = interpolate(f, [25, 45], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.quad) });
  const net = spring({ frame: f - 45, fps: 30, config: { damping: 8 } });
  const home = g.side === "home", col = home ? C.home : C.away;
  const appear = spring({ frame: f - 5, fps: 30, config: { damping: 14 } });
  return (
    <AbsoluteFill style={{ padding: "60px 110px 0", flexDirection: "row", alignItems: "center", gap: 70 }}>
      <svg width={PW} height={PH} style={{ background: "#123222", borderRadius: 16, overflow: "visible" }}>
        <g stroke="rgba(255,255,255,0.25)" strokeWidth="3" fill="none">
          <rect x="2" y="2" width={PW - 4} height={PH - 4} rx="14" />
          <rect x={gx(0.2)} y={gy(1)} width={gx(0.8) - gx(0.2)} height={gy(0.84) - gy(1)} />
          <rect x={gx(0.37)} y={gy(1)} width={gx(0.63) - gx(0.37)} height={gy(0.95) - gy(1)} />
          <path d={`M ${gx(0.4)} ${gy(0.84)} A 90 60 0 0 0 ${gx(0.6)} ${gy(0.84)}`} />
        </g>
        <rect x={gx(0.45)} y={gy(1) - 22} width={gx(0.55) - gx(0.45)} height={22} fill="none" stroke="#fff" strokeWidth="4" />
        <rect x={gx(0.45)} y={gy(1) - 22} width={gx(0.55) - gx(0.45)} height={22} fill={C.accent} opacity={0.5 * net} />
        <line x1={sx} y1={sy} x2={sx + (tx - sx) * t} y2={sy + (ty - sy) * t} stroke={C.accent} strokeWidth="5" strokeDasharray="12 10" />
        <circle cx={sx} cy={sy} r={22 * appear} fill={col} stroke={C.bg} strokeWidth="3" />
        <circle cx={sx + (tx - sx) * t} cy={sy + (ty - sy) * t} r={12} fill="#fff" stroke="#222" strokeWidth="2" opacity={t > 0 ? 1 : 0} />
      </svg>
      <div style={{ opacity: appear }}>
        <div style={{ fontFamily: HEAD, fontSize: 120, color: C.accent, lineHeight: 1 }}>{g.minute}'</div>
        <div style={{ fontFamily: HEAD, fontSize: 76, color: C.text, lineHeight: 1.05 }}>{g.player}</div>
        <div style={{ fontFamily: BODY, fontWeight: 700, fontSize: 30, color: col, marginTop: 6 }}>{home ? props.home : props.away}</div>
        <div style={{ marginTop: 26, display: "flex", flexDirection: "column", gap: 10, fontFamily: BODY, fontWeight: 600, fontSize: 30, color: C.muted }}>
          {info.assist ? <span>Assist: <b style={{ color: C.text }}>{info.assist}</b></span> : null}
          <span>{[(g.body_part || "").replace(/([a-z])([A-Z])/g, "$1 $2"), (g.situation || "").replace(/([a-z])([A-Z])/g, "$1 $2")].filter(Boolean).join(" · ")}</span>
          <span>Chance quality: <b style={{ color: C.text }}>{g.xg} xG</b></span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------- Key moments: the match in a few beats ----------
const KeyMoments = ({ visual, scene }) => {
  const f = useCurrentFrame();
  const ms = (visual.moments || []).slice(0, 6).sort((a, b) => a.minute - b.minute);
  if (!ms.length) return null;
  const W = 1600, x = (m) => (Math.min(m, 95) / 95) * W;
  const per = Math.max(12, (scene.durationInFrames * 0.7) / ms.length);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <svg width={W} height={520} style={{ overflow: "visible", marginTop: -60 }}>
        <line x1={0} y1={210} x2={W} y2={210} stroke={C.line} strokeWidth="6" />
        <line x1={0} y1={210} x2={x(interpolate(f, [0, per * ms.length], [0, 95], { extrapolateRight: "clamp" }))} y2={210}
              stroke={C.accent} strokeWidth="6" />
        {[0, 45, 90].map((m) => <text key={m} x={x(m)} y={250} textAnchor="middle" fontFamily={BODY} fontSize={22} fontWeight={600} fill={C.muted}>{m}'</text>)}
        {ms.map((m, i) => {
          const s = spring({ frame: f - i * per, fps: 30, config: { damping: 13 } });
          const cx = x(m.minute), card = (W / ms.length) * (i + 0.5);   // cards evenly spaced, linked to the real minute
          return (
            <g key={i} opacity={s}>
              <circle cx={cx} cy={210} r={14 * s} fill={C.accent} />
              <path d={`M ${cx} 224 L ${cx} 262 L ${card} 300 L ${card} 318`} stroke={C.accent} strokeWidth="3" fill="none" />
              <text x={card} y={366} textAnchor="middle" fontFamily={HEAD} fontSize={48} fill={C.accent}>{m.minute}'</text>
              {String(m.text).split(" ").reduce((rows, w) => {
                const last = rows[rows.length - 1];
                if (last && (last + " " + w).length <= 14) rows[rows.length - 1] = last + " " + w; else rows.push(w);
                return rows;
              }, []).slice(0, 3).map((row, k) => (
                <text key={k} x={card} y={404 + k * 32} textAnchor="middle" fontFamily={BODY} fontWeight={700} fontSize={27} fill={C.text}>{row}</text>
              ))}
            </g>
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};


// ---------- Line-ups: both elevens on one pitch + key absentees ----------
const Lineups = ({ props }) => {
  const f = useCurrentFrame();
  const L = props.lineups || {};
  if (!L.home || !L.away) return null;
  const PW = 1240, PH = 680;
  const dot = (p, side, i) => {
    // FotMob horizontal layout: x 0..1 from own goal, y 0..1 across. Home attacks right, away left.
    const x = side === "home" ? (p.x || 0) * PW / 2 : PW - (p.x || 0) * PW / 2;
    const y = (side === "home" ? (p.y || 0.5) : 1 - (p.y || 0.5)) * PH;
    const s = spring({ frame: f - 6 - i * 2, fps: 30, config: { damping: 12 } });
    const col = side === "home" ? C.home : C.away;
    const last = (p.player || "").split(" ").slice(-1)[0];
    return (
      <g key={side + i} transform={`translate(${x},${y}) scale(${s})`}>
        <circle r={24} fill={col} />
        <text y={8} textAnchor="middle" fontFamily={BODY} fontWeight={800} fontSize={22} fill={C.bg}>{p.shirt}</text>
        <text y={50} textAnchor="middle" fontFamily={BODY} fontWeight={700} fontSize={20} fill={C.text}>{last}</text>
        {p.rating ? <text y={-32} textAnchor="middle" fontFamily={BODY} fontWeight={800} fontSize={19}
                          fill={ratingColor(p.rating)}>{Number(p.rating).toFixed(1)}</text> : null}
      </g>
    );
  };
  const missing = (side) => (L[side].missing || []).slice(0, 3);
  const miss = [...missing("home").map((m) => ({ ...m, side: "home" })), ...missing("away").map((m) => ({ ...m, side: "away" }))];
  return (
    <AbsoluteFill style={{ padding: "70px 70px 0", flexDirection: "row", alignItems: "center", gap: 40 }}>
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", fontFamily: HEAD, fontSize: 36, marginBottom: 8 }}>
          <span style={{ color: C.home }}>{L.home.team.toUpperCase()} {L.home.formation}</span>
          <span style={{ color: C.away }}>{L.away.formation} {L.away.team.toUpperCase()}</span>
        </div>
        <svg width={PW} height={PH} style={{ background: "#123222", borderRadius: 14, overflow: "visible" }}>
          <g stroke="rgba(255,255,255,0.2)" strokeWidth="3" fill="none">
            <rect x="2" y="2" width={PW - 4} height={PH - 4} rx="12" />
            <line x1={PW / 2} y1={0} x2={PW / 2} y2={PH} />
            <circle cx={PW / 2} cy={PH / 2} r={80} />
            <rect x={0} y={PH * 0.2} width={PW * 0.14} height={PH * 0.6} />
            <rect x={PW * 0.86} y={PH * 0.2} width={PW * 0.14} height={PH * 0.6} />
          </g>
          {L.home.starters.map((p, i) => dot(p, "home", i))}
          {L.away.starters.map((p, i) => dot(p, "away", i + 11))}
        </svg>
      </div>
      {miss.length ? (
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ fontFamily: BODY, fontWeight: 800, letterSpacing: 3, fontSize: 24, color: C.muted }}>MISSING</div>
          {miss.map((m, i) => {
            const s = spring({ frame: f - 40 - i * 6, fps: 30, config: { damping: 14 } });
            return (
              <div key={i} style={{ opacity: s, borderLeft: `6px solid ${m.side === "home" ? C.home : C.away}`, paddingLeft: 14 }}>
                <div style={{ fontFamily: HEAD, fontSize: 34, color: C.text }}>{m.player}</div>
                <div style={{ fontFamily: BODY, fontWeight: 600, fontSize: 21, color: C.muted }}>
                  {String(m.reason).replace(/_/g, " ")}{m.value_eur ? ` · €${Math.round(m.value_eur / 1e6)}m` : ""}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};


// ---------- Real photo (free licence, Wikimedia Commons) with credit ----------
export const findPhoto = (props, visual) => {
  const list = props.photos || [];
  if (visual.photo) {
    const want = String(visual.photo).toLowerCase();
    return list.find((p) => p.name.toLowerCase() === want)
      || list.find((p) => want.includes(p.name.toLowerCase().split(" ").slice(-1)[0]));
  }
  return list[visual.photo_index || 0];
};

// Full-screen photo with a slow move, for shots where the words are about a person or a place.
export const FullPhoto = ({ visual, props, dur }) => {
  const f = useCurrentFrame();
  const ph = findPhoto(props, visual);
  if (!ph) return null;
  const zoom = interpolate(f, [0, Math.max(dur, 30)], [1.04, 1.14]);
  const pan = interpolate(f, [0, Math.max(dur, 30)], [-1.5, 1.5]);
  const lab = spring({ frame: f - 6, fps: 30, config: { damping: 16 } });
  return (
    <AbsoluteFill>
      <Img src={staticFile(`run/${ph.file}`)} onError={() => {}} style={{ width: "100%", height: "100%",
           objectFit: "cover", objectPosition: ph.role === "Stadium" ? "50% 50%" : "50% 25%",
           transform: `scale(${zoom}) translateX(${pan}%)` }} />
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(7,17,12,0.55) 0%, rgba(7,17,12,0.05) 35%, rgba(7,17,12,0.15) 60%, rgba(7,17,12,0.9) 100%)" }} />
      <div style={{ position: "absolute", left: 80, bottom: 250, opacity: lab, transform: `translateY(${(1 - lab) * 30}px)` }}>
        {ph.role !== "Stadium" ? <div style={{ fontFamily: BODY, fontWeight: 800, letterSpacing: 3, fontSize: 24, color: C.accent }}>
          {(ph.role || "").toUpperCase()}{ph.team ? ` · ${ph.team.toUpperCase()}` : ""}</div> : null}
        <div style={{ fontFamily: HEAD, fontSize: 84, color: "#fff", lineHeight: 1, textShadow: "0 4px 24px rgba(0,0,0,0.7)" }}>
          {ph.role === "Stadium" ? ph.name.split(",")[0] : ph.name}</div>
        {visual.caption ? <div style={{ fontFamily: BODY, fontWeight: 700, fontSize: 34, color: "#fff", marginTop: 8,
                                         textShadow: "0 2px 12px rgba(0,0,0,0.8)" }}>{visual.caption}</div> : null}
      </div>
      <div style={{ position: "absolute", right: 60, top: 130, fontFamily: BODY, fontSize: 17, color: "rgba(255,255,255,0.8)",
                    background: "rgba(0,0,0,0.45)", padding: "4px 10px", borderRadius: 6 }}>
        Photo: {ph.author} · {ph.licence} · {ph.via || "Wikimedia Commons"}
      </div>
    </AbsoluteFill>
  );
};

const PhotoCard = ({ visual, props, scene }) => {
  const f = useCurrentFrame();
  const ph = findPhoto(props, visual);
  if (!ph) return null;
  const p = spring({ frame: f - 2, fps: 30, config: { damping: 16 } });
  const zoom = interpolate(f, [0, scene.durationInFrames], [1.0, 1.08]);   // slow Ken Burns
  return (
    <AbsoluteFill style={{ padding: "60px 120px 0", flexDirection: "row", alignItems: "center", gap: 70 }}>
      <div style={{ width: 620, height: 700, borderRadius: 18, overflow: "hidden", border: `4px solid ${C.accent}`,
                    opacity: p, transform: `translateX(${(1 - p) * -40}px)`, flexShrink: 0, position: "relative" }}>
        <Img src={staticFile(`run/${ph.file}`)} onError={() => {}} style={{ width: "100%", height: "100%", objectFit: "cover",
                                                         objectPosition: "50% 20%", transform: `scale(${zoom})` }} />
        <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, padding: "8px 12px", background: "rgba(0,0,0,0.6)",
                      fontFamily: BODY, fontSize: 17, color: "#ddd" }}>
          Photo: {ph.author} · {ph.licence} · {ph.via || "Wikimedia Commons"}
        </div>
      </div>
      <div style={{ opacity: p }}>
        <div style={{ fontFamily: BODY, fontWeight: 800, letterSpacing: 3, fontSize: 26, color: C.muted }}>
          {(ph.role || "").toUpperCase()}{ph.team ? ` · ${ph.team.toUpperCase()}` : ""}
        </div>
        <div style={{ fontFamily: HEAD, fontSize: 96, color: C.text, lineHeight: 1 }}>{ph.name}</div>
        {visual.caption ? <div style={{ marginTop: 24, fontFamily: BODY, fontWeight: 600, fontSize: 40, color: C.accent,
                                        maxWidth: 820, lineHeight: 1.25 }}>{visual.caption}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

const MAP = {
  press_cut: PressCut,
  goal_replay: GoalReplay,
  key_moments: KeyMoments,
  photo: PhotoCard,
  lineups: Lineups,
  player_ratings: PlayerRatings,
  quote_card: QuoteCard,
  momentum: Momentum,
  history_lens: HistoryLens,
  shot_map: ShotMap, xg_timeline: XgTimeline,
  title_card: TitleCard, key_number: KeyNumber, scoreline: Scoreline,
  halftime_fulltime: HalfFull, stat_bars: StatBars, table_snapshot: TableSnapshot,
  form_compare: FormCompare, events_timeline: EventsTimeline, formations: Formations,
  text_card: TextCard, lesson_list: LessonList,
};

export const SceneVisual = ({ scene, props }) => {
  const visual = scene.visual || { type: "text_card", heading: scene.on_screen };
  const Comp = MAP[visual.type] || TextCard;
  return <Comp visual={visual} props={props} scene={scene} />;
};
