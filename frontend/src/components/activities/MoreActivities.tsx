import { useMemo, useState } from 'react';
import { soundFx } from '../../lib/soundFx';

const card = 'rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4 space-y-3';
const inputClass = 'rounded-lg border border-[var(--border-strong)] bg-[var(--bg-card)] px-3 py-2 text-sm';
const primary = 'rounded-lg bg-[var(--lg-indigo)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50';
const secondary = 'rounded-lg border border-[var(--border-strong)] px-3 py-2 text-sm font-medium text-[var(--text-primary)] disabled:opacity-50';
const heading = 'font-semibold text-[var(--text-primary)]';
const body = 'text-sm text-[var(--text-secondary)]';
const sliderLabel = 'block text-sm text-[var(--text-primary)]';

function Feedback({ ok, text }: { ok: boolean; text: string }) {
  return <p role="status" className={`text-sm font-medium ${ok ? 'text-[var(--lg-mastery-text)]' : 'text-[var(--lg-repair-text)]'}`}>{text}</p>;
}

function announce(ok: boolean) {
  if (ok) soundFx.playStepVerified();
  else soundFx.playMistakeLogged();
}

export function FreeBodyVectorLab() {
  const [applied, setApplied] = useState(20);
  const [friction, setFriction] = useState(5);
  const [mass, setMass] = useState(5);
  const net = applied - friction;
  const acceleration = net / mass;
  const centre = 150;
  const arrow = (length: number, colour: string, label: string, y: number) => (
    <g>
      <line x1={centre} y1={y} x2={centre + length * 3} y2={y} stroke={colour} strokeWidth={3} />
      <text x={centre + length * 3} y={y - 5} fontSize={11} fill="#0F172A" textAnchor="middle">{label}</text>
    </g>
  );
  return (
    <section className={card} aria-label="Free-body vector lab">
      <h3 className={heading}>Free-body vector lab</h3>
      <svg viewBox="0 0 300 120" className="w-full rounded-lg border border-[var(--border)] bg-white" role="img"
        aria-label={`Applied force ${applied} newtons right, friction ${friction} newtons left, net ${net} newtons`}>
        <rect x={centre - 18} y={42} width={36} height={36} fill="#E2E8F0" stroke="#0F172A" />
        {arrow(applied, '#1E3A8A', `${applied} N`, 52)}
        {arrow(-friction, '#D97706', `${friction} N`, 68)}
      </svg>
      <label className={sliderLabel}>Applied force: {applied} N<input type="range" className="w-full" min={0} max={40} value={applied} onChange={(e) => setApplied(Number(e.target.value))} /></label>
      <label className={sliderLabel}>Friction: {friction} N<input type="range" className="w-full" min={0} max={40} value={friction} onChange={(e) => setFriction(Number(e.target.value))} /></label>
      <label className={sliderLabel}>Mass: {mass} kg<input type="range" className="w-full" min={1} max={20} value={mass} onChange={(e) => setMass(Number(e.target.value))} /></label>
      <p role="status" className="font-mono font-semibold text-[var(--lg-indigo)]">Net force = {net} N; a = F/m = {acceleration.toFixed(2)} m/s²</p>
    </section>
  );
}

/** Solve x + left = right by removing equal weights from both pans. */
export function EquationBalanceScale() {
  const [left, setLeft] = useState(5);
  const [right, setRight] = useState(12);
  const [note, setNote] = useState('');
  const tilt = Math.max(-12, Math.min(12, (right - (left + 7)) * 2));
  const solved = left === 0;
  const remove = (fromBoth: boolean) => {
    if (!fromBoth) {
      soundFx.playMistakeLogged();
      setRight(right - 1);
      setNote('The scale tipped: removing from one side breaks the balance.');
      return;
    }
    if (left === 0) return;
    const nextLeft = left - 1;
    setLeft(nextLeft);
    setRight(right - 1);
    setNote(nextLeft === 0 ? 'x is alone, and the scale still balances.' : 'Still balanced.');
    if (nextLeft === 0) soundFx.playStepVerified();
  };
  return (
    <section className={card} aria-label="Equation balance scale">
      <h3 className={heading}>Equation balance scale</h3>
      <svg viewBox="0 0 240 90" className="w-full max-w-sm rounded-lg border border-[var(--border)] bg-white" role="img" aria-label={`x plus ${left} on the left, ${right} on the right`}>
        <g transform={`rotate(${tilt} 120 30)`}>
          <line x1={30} y1={30} x2={210} y2={30} stroke="#0F172A" strokeWidth={3} />
          <text x={60} y={22} fontSize={13} textAnchor="middle" fill="#0F172A">x + {left}</text>
          <text x={180} y={22} fontSize={13} textAnchor="middle" fill="#0F172A">{right}</text>
        </g>
        <line x1={120} y1={30} x2={120} y2={80} stroke="#475569" strokeWidth={3} />
      </svg>
      <p className="font-mono text-sm text-[var(--text-primary)]">x + {left} = {right}</p>
      <div className="flex flex-wrap gap-2">
        <button type="button" className={primary} disabled={solved} onClick={() => remove(true)}>Remove 1 from both sides</button>
        <button type="button" className={secondary} disabled={solved} onClick={() => remove(false)}>Remove 1 from the right only</button>
        <button type="button" className={secondary} onClick={() => { setLeft(5); setRight(12); setNote(''); }}>Reset</button>
      </div>
      {note && <Feedback ok={right - left === 7} text={note} />}
    </section>
  );
}

export function FractionNumberLine() {
  const [round, setRound] = useState(0);
  const questions = useMemo(() => [{ n: 3, d: 4 }, { n: 2, d: 5 }, { n: 5, d: 8 }, { n: 1, d: 3 }], []);
  const q = questions[round % questions.length];
  const [position, setPosition] = useState(50);
  const [result, setResult] = useState<boolean | null>(null);
  const target = (q.n / q.d) * 100;
  const check = () => {
    const ok = Math.abs(position - target) <= 4;
    setResult(ok);
    announce(ok);
  };
  return (
    <section className={card} aria-label="Fraction number line">
      <h3 className={heading}>Place {q.n}/{q.d} on the number line</h3>
      <svg viewBox="0 0 300 40" className="w-full" aria-hidden>
        <line x1={10} y1={20} x2={290} y2={20} stroke="#475569" strokeWidth={2} />
        {Array.from({ length: q.d + 1 }, (_, i) => <line key={i} x1={10 + (280 * i) / q.d} y1={13} x2={10 + (280 * i) / q.d} y2={27} stroke="#475569" />)}
        <circle cx={10 + 2.8 * position} cy={20} r={6} fill="#1E3A8A" />
      </svg>
      <label className={sliderLabel}>Position: {(position / 100).toFixed(2)}
        <input type="range" className="w-full" min={0} max={100} value={position} onChange={(e) => { setPosition(Number(e.target.value)); setResult(null); }} /></label>
      <div className="flex gap-2">
        <button type="button" className={primary} onClick={check}>Check</button>
        <button type="button" className={secondary} onClick={() => { setRound(round + 1); setPosition(50); setResult(null); }}>Next fraction</button>
      </div>
      {result !== null && <Feedback ok={result} text={result ? `Yes: ${q.n}/${q.d} = ${(q.n / q.d).toFixed(3)}.` : `Count ${q.d} equal parts between 0 and 1, then take ${q.n} of them.`} />}
    </section>
  );
}

type Species = { label: string; atoms: Record<string, number> };

const REACTIONS: { name: string; reactants: Species[]; products: Species[] }[] = [
  { name: 'Hydrogen + oxygen', reactants: [{ label: 'H₂', atoms: { H: 2 } }, { label: 'O₂', atoms: { O: 2 } }], products: [{ label: 'H₂O', atoms: { H: 2, O: 1 } }] },
  { name: 'Methane combustion', reactants: [{ label: 'CH₄', atoms: { C: 1, H: 4 } }, { label: 'O₂', atoms: { O: 2 } }], products: [{ label: 'CO₂', atoms: { C: 1, O: 2 } }, { label: 'H₂O', atoms: { H: 2, O: 1 } }] },
  { name: 'Iron + oxygen', reactants: [{ label: 'Fe', atoms: { Fe: 1 } }, { label: 'O₂', atoms: { O: 2 } }], products: [{ label: 'Fe₂O₃', atoms: { Fe: 2, O: 3 } }] },
];

export function ChemicalEquationBalancer() {
  const [index, setIndex] = useState(0);
  const reaction = REACTIONS[index];
  const all = [...reaction.reactants, ...reaction.products];
  const [coefficients, setCoefficients] = useState<number[]>(all.map(() => 1));
  const count = (species: Species[], offset: number) => {
    const totals: Record<string, number> = {};
    species.forEach((s, i) => Object.entries(s.atoms).forEach(([atom, n]) => { totals[atom] = (totals[atom] ?? 0) + n * coefficients[offset + i]; }));
    return totals;
  };
  const left = count(reaction.reactants, 0);
  const right = count(reaction.products, reaction.reactants.length);
  const balanced = Object.keys(left).every((a) => left[a] === right[a]);
  const coefficient = (i: number, s: Species) => (
    <label key={s.label} className="inline-flex items-center gap-1 text-sm text-[var(--text-primary)]">
      <input type="number" min={1} max={9} aria-label={`Coefficient of ${s.label}`} className={`${inputClass} w-14`} value={coefficients[i]}
        onChange={(e) => { const next = [...coefficients]; next[i] = Math.max(1, Number(e.target.value) || 1); setCoefficients(next); }} />
      {s.label}
    </label>
  );
  return (
    <section className={card} aria-label="Chemical equation balancer">
      <h3 className={heading}>Balance: {reaction.name}</h3>
      <div className="flex flex-wrap items-center gap-2">
        {reaction.reactants.map((s, i) => coefficient(i, s))}
        <span aria-label="gives" className="font-semibold">→</span>
        {reaction.products.map((s, i) => coefficient(reaction.reactants.length + i, s))}
      </div>
      <table className="text-sm text-[var(--text-primary)]">
        <thead><tr><th scope="col" className="pr-4 text-left">Atom</th><th scope="col" className="pr-4">Left</th><th scope="col">Right</th></tr></thead>
        <tbody>{Object.keys(left).map((a) => <tr key={a}><th scope="row" className="pr-4 text-left">{a}</th><td className="pr-4 text-center">{left[a]}</td><td className="text-center">{right[a]}</td></tr>)}</tbody>
      </table>
      <div className="flex gap-2">
        <button type="button" className={primary} onClick={() => announce(balanced)}>Check</button>
        <button type="button" className={secondary} onClick={() => { const next = (index + 1) % REACTIONS.length; setIndex(next); setCoefficients([...REACTIONS[next].reactants, ...REACTIONS[next].products].map(() => 1)); }}>Next reaction</button>
      </div>
      <Feedback ok={balanced} text={balanced ? 'Balanced: every atom count matches.' : 'Not balanced yet. Change only the coefficients.'} />
    </section>
  );
}

const SORT_ITEMS: [string, string][] = [
  ['Speed', 'Scalar'], ['Distance', 'Scalar'], ['Time', 'Scalar'],
  ['Velocity', 'Vector'], ['Displacement', 'Vector'], ['Force', 'Vector'],
];

export function SortingClassificationBuckets({ items = SORT_ITEMS }: { items?: [string, string][] }) {
  const buckets = useMemo(() => [...new Set(items.map((i) => i[1]))], [items]);
  const [placed, setPlaced] = useState<Record<string, string>>({});
  const [note, setNote] = useState('');
  const remaining = items.filter(([name]) => !placed[name]);
  const current = remaining[0];
  const place = (bucket: string) => {
    if (!current) return;
    const ok = current[1] === bucket;
    announce(ok);
    if (ok) {
      setPlaced({ ...placed, [current[0]]: bucket });
      setNote(`${current[0]} is a ${bucket.toLowerCase()} quantity.`);
    } else {
      setNote(`Think again about ${current[0]}: does it need a direction?`);
    }
  };
  return (
    <section className={card} aria-label="Sort into buckets">
      <h3 className={heading}>Sort the quantities</h3>
      <p className="text-sm font-medium text-[var(--text-primary)]">{current ? `Where does "${current[0]}" belong?` : 'All sorted.'}</p>
      <div className="grid grid-cols-2 gap-3">
        {buckets.map((bucket) => (
          <div key={bucket} className="rounded-lg border border-[var(--border)] p-2">
            <button type="button" className={`${secondary} w-full`} disabled={!current} onClick={() => place(bucket)}>{bucket}</button>
            <ul className="mt-2 text-sm text-[var(--lg-mastery-text)]">{items.filter(([n]) => placed[n] === bucket).map(([n]) => <li key={n}>{n}</li>)}</ul>
          </div>
        ))}
      </div>
      {note && <p role="status" className={body}>{note}</p>}
    </section>
  );
}

const SEQUENCE = [
  'Read the question and list what is known',
  'Choose the formula that links known and unknown',
  'Substitute the values with their signs',
  'Calculate',
  'Check the unit and whether the answer is sensible',
];

export function TimelineSequenceBuilder({ steps = SEQUENCE }: { steps?: string[] }) {
  const [order, setOrder] = useState(() => [...steps].map((_, i) => (i * 2 + 1) % steps.length).map((i) => steps[i]));
  const [checked, setChecked] = useState<boolean | null>(null);
  const move = (index: number, by: number) => {
    const target = index + by;
    if (target < 0 || target >= order.length) return;
    const next = [...order];
    [next[index], next[target]] = [next[target], next[index]];
    setOrder(next);
    setChecked(null);
  };
  return (
    <section className={card} aria-label="Sequence builder">
      <h3 className={heading}>Put the steps in order</h3>
      <ol className="space-y-2">
        {order.map((step, i) => (
          <li key={step} className="flex items-center gap-2 rounded-lg border border-[var(--border)] p-2 text-sm text-[var(--text-primary)]">
            <span className="flex-1">{i + 1}. {step}</span>
            <button type="button" className={secondary} aria-label={`Move "${step}" up`} disabled={i === 0} onClick={() => move(i, -1)}>↑</button>
            <button type="button" className={secondary} aria-label={`Move "${step}" down`} disabled={i === order.length - 1} onClick={() => move(i, 1)}>↓</button>
          </li>
        ))}
      </ol>
      <button type="button" className={primary} onClick={() => { const ok = order.every((s, i) => s === steps[i]); setChecked(ok); announce(ok); }}>Check order</button>
      {checked !== null && <Feedback ok={checked} text={checked ? 'That is the right order.' : `${order.filter((s, i) => s === steps[i]).length} of ${steps.length} are in place.`} />}
    </section>
  );
}

const WORKED = { problem: 'Solve 3x + 2 = 11', steps: ['3x + 2 = 11', '3x = 9', 'x = 3'], notes: ['Start with the equation.', 'Subtract 2 from both sides.', 'Divide both sides by 3.'] };
const FADE_LABELS = ['Full example', 'Last step blank', 'Middle onward blank', 'Solo'];

export function FadedWorkedExampleStepper({ example = WORKED }: { example?: typeof WORKED }) {
  const [stage, setStage] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [result, setResult] = useState<boolean | null>(null);
  const shown = stage === 0 ? example.steps.length : stage === 1 ? example.steps.length - 1 : stage === 2 ? 1 : 0;
  const normal = (s: string) => s.replace(/\s+/g, '').toLowerCase();
  const check = () => {
    const ok = example.steps.every((step, i) => i < shown || normal(answers[i] ?? '') === normal(step));
    setResult(ok);
    announce(ok);
    if (ok && stage < 3) {
      setStage(stage + 1);
      setAnswers({});
    }
  };
  return (
    <section className={card} aria-label="Faded worked example">
      <h3 className={heading}>{example.problem}</h3>
      <p className={body}>Stage {stage + 1} of 4: {FADE_LABELS[stage]}</p>
      <ol className="space-y-2">
        {example.steps.map((step, i) => (
          <li key={step} className="text-sm text-[var(--text-primary)]">
            {i < shown ? <><span className="font-mono">{step}</span>: {example.notes[i]}</> : (
              <input className={`${inputClass} w-full font-mono`} aria-label={`Step ${i + 1}`} placeholder={`Step ${i + 1}`} value={answers[i] ?? ''} onChange={(e) => setAnswers({ ...answers, [i]: e.target.value })} />
            )}
          </li>
        ))}
      </ol>
      <button type="button" className={primary} onClick={stage === 0 ? () => { setStage(1); setResult(null); } : check}>{stage === 0 ? 'I understand, fade it' : 'Check'}</button>
      {result !== null && <Feedback ok={result} text={result ? 'Verified. The next stage gives you less help.' : 'Compare with the step before it. What operation comes next?'} />}
    </section>
  );
}

export function CircuitBuilderLab() {
  const [mode, setMode] = useState<'series' | 'parallel'>('series');
  const [r1, setR1] = useState(4);
  const [r2, setR2] = useState(6);
  const [closed, setClosed] = useState(true);
  const voltage = 12;
  const total = mode === 'series' ? r1 + r2 : (r1 * r2) / (r1 + r2);
  const current = closed ? voltage / total : 0;
  return (
    <section className={card} aria-label="Circuit builder lab">
      <h3 className={heading}>Circuit builder (12 V battery)</h3>
      <div className="flex flex-wrap gap-2">
        {(['series', 'parallel'] as const).map((m) => <button key={m} type="button" aria-pressed={mode === m} className={mode === m ? primary : secondary} onClick={() => setMode(m)}>{m === 'series' ? 'Series' : 'Parallel'}</button>)}
        <button type="button" aria-pressed={closed} className={secondary} onClick={() => setClosed(!closed)}>Switch: {closed ? 'closed' : 'open'}</button>
      </div>
      <svg viewBox="0 0 260 110" className="w-full max-w-sm rounded-lg border border-[var(--border)] bg-white" role="img" aria-label={`${mode} circuit, ${closed ? 'current flowing' : 'no current'}`}>
        <rect x={20} y={15} width={220} height={80} fill="none" stroke={closed ? '#1E3A8A' : '#475569'} strokeWidth={2} strokeDasharray={closed ? undefined : '6 5'} />
        {mode === 'series' ? (
          <><rect x={70} y={7} width={40} height={16} fill="#fff" stroke="#0F172A" /><rect x={150} y={7} width={40} height={16} fill="#fff" stroke="#0F172A" /></>
        ) : (
          <><line x1={90} y1={15} x2={90} y2={95} stroke="#1E3A8A" /><line x1={170} y1={15} x2={170} y2={95} stroke="#1E3A8A" /><rect x={80} y={45} width={20} height={22} fill="#fff" stroke="#0F172A" /><rect x={160} y={45} width={20} height={22} fill="#fff" stroke="#0F172A" /></>
        )}
      </svg>
      <label className={sliderLabel}>R₁ = {r1} Ω<input type="range" className="w-full" min={1} max={20} value={r1} onChange={(e) => setR1(Number(e.target.value))} /></label>
      <label className={sliderLabel}>R₂ = {r2} Ω<input type="range" className="w-full" min={1} max={20} value={r2} onChange={(e) => setR2(Number(e.target.value))} /></label>
      <p role="status" className="font-mono font-semibold text-[var(--lg-indigo)]">R total = {total.toFixed(2)} Ω; I = {current.toFixed(2)} A</p>
    </section>
  );
}

export function GeometryAngleExplorer() {
  const [angle, setAngle] = useState(60);
  const rad = (angle * Math.PI) / 180;
  const kind = angle === 90 ? 'a right angle' : angle < 90 ? 'an acute angle' : angle === 180 ? 'a straight angle' : 'an obtuse angle';
  const x = 110 + 80 * Math.cos(rad);
  const y = 110 - 80 * Math.sin(rad);
  const large = 0;
  return (
    <section className={card} aria-label="Angle explorer">
      <h3 className={heading}>Angle explorer</h3>
      <svg viewBox="0 0 220 125" className="w-full max-w-xs rounded-lg border border-[var(--border)] bg-white" role="img" aria-label={`Angle of ${angle} degrees`}>
        <line x1={110} y1={110} x2={200} y2={110} stroke="#0F172A" strokeWidth={2} />
        <line x1={110} y1={110} x2={x} y2={y} stroke="#1E3A8A" strokeWidth={2} />
        <path d={`M 140 110 A 30 30 0 ${large} 0 ${110 + 30 * Math.cos(rad)} ${110 - 30 * Math.sin(rad)}`} fill="none" stroke="#D97706" strokeWidth={2} />
      </svg>
      <label className={sliderLabel}>Angle: {angle}°<input type="range" className="w-full" min={1} max={180} value={angle} onChange={(e) => setAngle(Number(e.target.value))} /></label>
      <p role="status" className={body}>{angle}° is {kind}. Its supplement is {180 - angle}°{angle < 90 ? ` and its complement is ${90 - angle}°` : ''}.</p>
    </section>
  );
}
