import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { C, HEAD, BODY, parseNum, fmt } from "./theme";

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

const MAP = {
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
