import { useMemo, useRef, useState } from 'react';
import { Mic, MicOff } from 'lucide-react';
import { v1 } from '../../lib/v1Api';
import { soundFx } from '../../lib/soundFx';
import { useVoiceInput, type VoiceLanguage } from '../../hooks/useVoiceInput';

const card = 'rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4 space-y-3';
const input = 'w-full rounded-lg border border-[var(--border-strong)] bg-[var(--bg-card)] px-3 py-2 text-sm';
const primary = 'rounded-lg bg-[var(--lg-indigo)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50';
const secondary = 'rounded-lg border border-[var(--border-strong)] px-3 py-2 text-sm font-medium text-[var(--text-primary)]';
const heading = 'font-semibold text-[var(--text-primary)]';
const body = 'text-sm text-[var(--text-secondary)]';

export function StepAttributionBanner({ succeeded, fix }: { succeeded: string; fix: string }) {
  return (
    <div className="rounded-xl overflow-hidden border border-[var(--border)]" role="status">
      <p className="border-l-4 border-[var(--lg-mastery)] bg-[var(--lg-mastery-wash)] px-4 py-2 text-sm font-medium text-[var(--lg-mastery-text)]">
        {succeeded}
      </p>
      <p className="border-l-4 border-[var(--lg-repair)] bg-[var(--lg-repair-wash)] px-4 py-2 text-sm font-medium text-[var(--lg-repair-text)]">
        {fix}
      </p>
    </div>
  );
}

export function AlgebraStepBuilder({ start = '2x + 3 = 7' }: { start?: string }) {
  const [steps, setSteps] = useState([start]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const check = async () => {
    if (!draft.trim()) return;
    setBusy(true);
    try {
      const { verdict } = await v1.verifyStep(steps[steps.length - 1], draft);
      if (verdict === 'verified') {
        soundFx.playStepVerified();
        setSteps([...steps, draft]);
        setDraft('');
        setMessage({ ok: true, text: `Step ${steps.length} is valid. What's next?` });
      } else if (verdict === 'refuted') {
        soundFx.playMistakeLogged();
        setMessage({ ok: false, text: 'This line changes the solution. Check what you did to each side.' });
      } else {
        setMessage({ ok: false, text: 'I can only check one equation with one "=". Try writing it like 2x = 4.' });
      }
    } catch {
      setMessage({ ok: false, text: "I couldn't check that right now. Please try again." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={card} aria-label="Algebra step builder">
      <h3 className={heading}>Algebra step builder</h3>
      <ol className="space-y-1 font-mono text-sm">
        {steps.map((step, i) => (
          <li key={i} className="rounded bg-[var(--lg-mastery-wash)] px-2 py-1 text-[var(--lg-mastery-text)]">{step}</li>
        ))}
      </ol>
      <div className="flex gap-2">
        <input className={`${input} font-mono`} aria-label="Next step" value={draft} onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && check()} placeholder="Type the next line" />
        <button type="button" className={primary} disabled={busy} onClick={check}>Check</button>
      </div>
      {message && (
        <p role="status" className={`text-sm font-medium ${message.ok ? 'text-[var(--lg-mastery-text)]' : 'text-[var(--lg-repair-text)]'}`}>{message.text}</p>
      )}
    </section>
  );
}

const DEFAULT_DERIVATION = {
  steps: ['2x + 6 = 14', '2x = 20', 'x = 10'],
  flawed: 1,
  fix: '2x = 8',
  why: 'Moving +6 across the equals sign makes it -6, so 14 - 6 = 8.',
};

export function SpotTheErrorChallenge({ derivation = DEFAULT_DERIVATION }: { derivation?: typeof DEFAULT_DERIVATION }) {
  const [picked, setPicked] = useState<number | null>(null);
  const [fix, setFix] = useState('');
  const [state, setState] = useState<'idle' | 'fixed' | 'wrong'>('idle');
  const found = picked === derivation.flawed;

  const checkFix = async () => {
    const { verdict } = await v1.verifyStep(derivation.steps[derivation.flawed - 1], fix);
    if (verdict === 'verified') {
      soundFx.playStepVerified();
      setState('fixed');
    } else {
      soundFx.playMistakeLogged();
      setState('wrong');
    }
  };

  return (
    <section className={card} aria-label="Spot the error">
      <h3 className={heading}>Spot the error</h3>
      <p className={body}>One line doesn't follow from the line before it. Click that line.</p>
      <div className="space-y-1">
        {derivation.steps.map((step, i) => (
          <button key={i} type="button" onClick={() => { setPicked(i); setState('idle'); if (i !== derivation.flawed) soundFx.playMistakeLogged(); }}
            aria-pressed={picked === i}
            className={`block w-full rounded-lg border px-3 py-2 text-left font-mono text-sm text-[var(--text-primary)] ${
              picked === i ? (found ? 'border-[var(--lg-repair)] bg-[var(--lg-repair-wash)]' : 'border-[var(--border-strong)] bg-[var(--bg-hover)]') : 'border-[var(--border)]'
            }`}>
            {step}
          </button>
        ))}
      </div>
      {picked !== null && !found && <p className={body}>That line is fine. Compare the other lines one pair at a time.</p>}
      {found && (
        <div className="flex gap-2">
          <input className={`${input} font-mono`} aria-label="Corrected line" value={fix} onChange={(e) => setFix(e.target.value)} placeholder="Write the corrected line" />
          <button type="button" className={primary} onClick={checkFix}>Fix it</button>
        </div>
      )}
      {state === 'fixed' && <p role="status" className="text-sm font-medium text-[var(--lg-mastery-text)]">Fixed. {derivation.why}</p>}
      {state === 'wrong' && <p role="status" className="text-sm font-medium text-[var(--lg-repair-text)]">Not yet. What happens to +6 when it crosses the equals sign?</p>}
    </section>
  );
}

export function CoordinateGraphPlotter() {
  const [kind, setKind] = useState<'line' | 'parabola'>('line');
  const [a, setA] = useState(1);
  const [b, setB] = useState(0);
  const [c, setC] = useState(0);
  const size = 280;
  const unit = size / 20;
  const toX = (x: number) => size / 2 + x * unit;
  const toY = (y: number) => size / 2 - y * unit;
  const f = (x: number) => (kind === 'line' ? a * x + b : a * x * x + b * x + c);
  const points = useMemo(() => {
    const out: string[] = [];
    for (let x = -10; x <= 10; x += 0.1) {
      const y = f(x);
      if (Math.abs(y) <= 12) out.push(`${toX(x).toFixed(1)},${toY(y).toFixed(1)}`);
    }
    return out.join(' ');
  }, [kind, a, b, c]);
  const discriminant = b * b - 4 * a * c;
  const equation = kind === 'line' ? `y = ${a}x + ${b}` : `y = ${a}x² + ${b}x + ${c}`;
  const slider = (label: string, value: number, set: (n: number) => void) => (
    <label className="block text-sm text-[var(--text-primary)]">
      {label} = {value}
      <input type="range" min={-5} max={5} step={0.5} value={value} onChange={(e) => set(Number(e.target.value))} className="w-full" />
    </label>
  );

  return (
    <section className={card} aria-label="Coordinate graph plotter">
      <h3 className={heading}>Graph plotter</h3>
      <div className="flex gap-2">
        {(['line', 'parabola'] as const).map((k) => (
          <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)} className={kind === k ? primary : secondary}>{k === 'line' ? 'Line' : 'Parabola'}</button>
        ))}
      </div>
      <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-xs border border-[var(--border)] rounded-lg bg-white" role="img" aria-label={`Graph of ${equation}`}>
        <line x1={0} y1={size / 2} x2={size} y2={size / 2} stroke="#475569" />
        <line x1={size / 2} y1={0} x2={size / 2} y2={size} stroke="#475569" />
        <polyline points={points} fill="none" stroke="#1E3A8A" strokeWidth={2.5} />
      </svg>
      <p className="font-mono text-sm text-[var(--text-primary)]">{equation}</p>
      {slider('a', a, setA)}
      {slider('b', b, setB)}
      {kind === 'parabola' && slider('c', c, setC)}
      {kind === 'parabola' && a !== 0 && (
        <p className={body}>Discriminant = {discriminant}: {discriminant > 0 ? 'two real roots' : discriminant === 0 ? 'one repeated root' : 'no real roots'}.</p>
      )}
    </section>
  );
}

/** Thin-lens ray diagram; distances in cm, using the sign convention taught in class. */
export function RayOpticsBench() {
  const [focal, setFocal] = useState(10);
  const [object, setObject] = useState(25);
  const width = 340, height = 180, axis = height / 2, lensX = width / 2, h = 40, scale = 3;
  const denominator = 1 / focal - 1 / object;
  const atInfinity = Math.abs(denominator) < 1e-9;
  const v = atInfinity ? Infinity : 1 / denominator;
  const magnification = atInfinity ? Infinity : -v / object;
  const objectX = lensX - object * scale;
  const imageX = lensX + v * scale;
  const imageY = axis - h * magnification;
  const real = v > 0;

  return (
    <section className={card} aria-label="Ray optics bench">
      <h3 className={heading}>Ray optics bench: convex lens</h3>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full border border-[var(--border)] rounded-lg bg-white" role="img"
        aria-label={atInfinity ? 'Rays leave parallel, so no image forms' : `Image at ${v.toFixed(1)} centimetres from the lens`}>
        <defs><clipPath id="bench"><rect width={width} height={height} /></clipPath></defs>
        <line x1={0} y1={axis} x2={width} y2={axis} stroke="#475569" />
        <line x1={lensX} y1={10} x2={lensX} y2={height - 10} stroke="#1E3A8A" strokeWidth={3} />
        {[-1, 1].map((s) => <circle key={s} cx={lensX + s * focal * scale} cy={axis} r={3} fill="#0F172A" />)}
        <line x1={objectX} y1={axis} x2={objectX} y2={axis - h} stroke="#0D9488" strokeWidth={3} />
        <g clipPath="url(#bench)" stroke="#D97706" strokeWidth={1.5}>
          <line x1={objectX} y1={axis - h} x2={lensX} y2={axis - h} />
          <line x1={lensX} y1={axis - h} x2={lensX + 400} y2={axis - h + (h / (focal * scale)) * 400} />
          <line x1={objectX} y1={axis - h} x2={lensX + 400} y2={axis - h + (h / (object * scale)) * (object * scale + 400)} />
        </g>
        {!atInfinity && <line x1={imageX} y1={axis} x2={imageX} y2={imageY} stroke="#7C3AED" strokeWidth={3} clipPath="url(#bench)" strokeDasharray={real ? undefined : '5 3'} />}
      </svg>
      <label className="block text-sm text-[var(--text-primary)]">Focal length {focal} cm
        <input type="range" min={5} max={20} value={focal} onChange={(e) => setFocal(Number(e.target.value))} className="w-full" /></label>
      <label className="block text-sm text-[var(--text-primary)]">Object distance {object} cm
        <input type="range" min={6} max={45} value={object} onChange={(e) => setObject(Number(e.target.value))} className="w-full" /></label>
      <p className={body} role="status">
        {atInfinity ? 'The object is at the focus: rays leave parallel and no image forms.'
          : `v = ${v.toFixed(1)} cm. The image is ${real ? 'real and inverted' : 'virtual and upright'}, magnification ${Math.abs(magnification).toFixed(2)}×.`}
      </p>
    </section>
  );
}

const Poe = ({ question }: { question: string }) => {
  const [prediction, setPrediction] = useState('');
  const [explanation, setExplanation] = useState('');
  return (
    <div className="space-y-2 rounded-lg bg-[var(--bg-secondary)] p-3">
      <label className="block text-sm font-medium text-[var(--text-primary)]">Predict: {question}
        <input className={`${input} mt-1`} value={prediction} onChange={(e) => setPrediction(e.target.value)} /></label>
      <p className={body}>Observe: move the sliders and watch the readings.</p>
      <label className="block text-sm font-medium text-[var(--text-primary)]">Explain: why did that happen?
        <textarea className={`${input} mt-1`} rows={2} value={explanation} onChange={(e) => setExplanation(e.target.value)} /></label>
    </div>
  );
};

export function VirtualScienceLab() {
  const [lab, setLab] = useState<'ohm' | 'titration'>('ohm');
  const [voltage, setVoltage] = useState(12);
  const [resistance, setResistance] = useState(4);
  const [baseMl, setBaseMl] = useState(0);
  const acidMl = 25, acidMolar = 0.1, baseMolar = 0.1;
  const acidMoles = (acidMl * acidMolar) / 1000;
  const baseMoles = (baseMl * baseMolar) / 1000;
  const totalLitres = (acidMl + baseMl) / 1000;
  let pH = 7;
  if (acidMoles > baseMoles) pH = -Math.log10((acidMoles - baseMoles) / totalLitres);
  else if (baseMoles > acidMoles) pH = 14 + Math.log10((baseMoles - acidMoles) / totalLitres);
  const current = voltage / resistance;

  return (
    <section className={card} aria-label="Virtual science lab">
      <h3 className={heading}>Virtual science lab</h3>
      <div className="flex gap-2">
        <button type="button" aria-pressed={lab === 'ohm'} className={lab === 'ohm' ? primary : secondary} onClick={() => setLab('ohm')}>Ohm's law</button>
        <button type="button" aria-pressed={lab === 'titration'} className={lab === 'titration' ? primary : secondary} onClick={() => setLab('titration')}>Titration</button>
      </div>
      {lab === 'ohm' ? (
        <>
          <Poe question="if voltage doubles and resistance stays the same, what happens to the current?" />
          <label className="block text-sm text-[var(--text-primary)]">Voltage V = {voltage} V
            <input type="range" min={1} max={24} value={voltage} onChange={(e) => setVoltage(Number(e.target.value))} className="w-full" /></label>
          <label className="block text-sm text-[var(--text-primary)]">Resistance R = {resistance} Ω
            <input type="range" min={1} max={20} value={resistance} onChange={(e) => setResistance(Number(e.target.value))} className="w-full" /></label>
          <p className="font-mono text-lg font-semibold text-[var(--lg-indigo)]" role="status">I = V / R = {current.toFixed(2)} A</p>
        </>
      ) : (
        <>
          <Poe question="what pH do you expect when equal amounts of strong acid and strong base are mixed?" />
          <label className="block text-sm text-[var(--text-primary)]">0.1 M NaOH added: {baseMl} mL (into 25 mL of 0.1 M HCl)
            <input type="range" min={0} max={50} step={0.5} value={baseMl} onChange={(e) => setBaseMl(Number(e.target.value))} className="w-full" /></label>
          <div className="h-4 rounded-full" style={{ background: pH < 8.2 ? '#F8FAFC' : '#F5B7D5', border: '1px solid #CBD5E1' }} aria-hidden />
          <p className="font-mono text-lg font-semibold text-[var(--lg-indigo)]" role="status">
            pH = {pH.toFixed(2)}; phenolphthalein is {pH < 8.2 ? 'colourless' : 'pink'}
          </p>
        </>
      )}
    </section>
  );
}

interface Pin { id: string; label: string; x: number; y: number }

const EYE_PINS: Pin[] = [
  { id: 'pole', label: 'Pole', x: 80, y: 50 },
  { id: 'focus', label: 'Focus', x: 50, y: 50 },
  { id: 'centre', label: 'Centre of curvature', x: 20, y: 50 },
];

/** Pin each label on the concave-mirror diagram; placement is checked within 8%. */
export function InteractiveDiagramPin({ pins = EYE_PINS }: { pins?: Pin[] }) {
  const [active, setActive] = useState(0);
  const [placed, setPlaced] = useState<Record<string, boolean>>({});
  const [note, setNote] = useState('');
  const svgRef = useRef<SVGSVGElement>(null);
  const done = active >= pins.length;

  const place = (event: React.MouseEvent<SVGSVGElement> | { x: number; y: number }) => {
    if (done || !svgRef.current) return;
    let x: number, y: number;
    if ('clientX' in event) {
      const rect = svgRef.current.getBoundingClientRect();
      x = ((event.clientX - rect.left) / rect.width) * 100;
      y = ((event.clientY - rect.top) / rect.height) * 100;
    } else {
      ({ x, y } = event);
    }
    const target = pins[active];
    if (Math.hypot(x - target.x, y - target.y) <= 8) {
      soundFx.playStepVerified();
      setPlaced({ ...placed, [target.id]: true });
      setActive(active + 1);
      setNote('');
    } else {
      soundFx.playMistakeLogged();
      setNote('Close, but not quite. Think about where this point sits along the axis.');
    }
  };

  return (
    <section className={card} aria-label="Diagram pin activity">
      <h3 className={heading}>Label the concave mirror</h3>
      <p className={body}>{done ? 'All labels placed correctly.' : `Click where this belongs: ${pins[active].label}`}</p>
      <svg ref={svgRef} viewBox="0 0 100 100" className="w-full max-w-xs cursor-crosshair rounded-lg border border-[var(--border)] bg-white" onClick={place} role="img" aria-label="Concave mirror diagram with principal axis">
        <line x1={5} y1={50} x2={95} y2={50} stroke="#475569" strokeWidth={0.6} />
        <path d="M 72 12 Q 92 50 72 88" fill="none" stroke="#1E3A8A" strokeWidth={1.6} />
        {pins.filter((p) => placed[p.id]).map((p) => (
          <g key={p.id}>
            <circle cx={p.x} cy={p.y} r={1.6} fill="#0D9488" />
            <text x={p.x} y={p.y - 4} fontSize={4} textAnchor="middle" fill="#0F172A">{p.label}</text>
          </g>
        ))}
      </svg>
      {!done && (
        <div className="flex flex-wrap gap-2">
          <span className={body}>Keyboard option:</span>
          {pins.map((p) => (
            <button key={p.id} type="button" className={secondary} onClick={() => place({ x: p.x, y: p.y })}>Place at the {p.id === 'pole' ? 'mirror' : p.id === 'focus' ? 'midpoint' : 'far left'}</button>
          ))}
        </div>
      )}
      {note && <p role="status" className="text-sm font-medium text-[var(--lg-repair-text)]">{note}</p>}
    </section>
  );
}

const MAP_LINKS: [string, string, string][] = [
  ['Linear equations', 'Pair of linear equations', 'needed for'],
  ['Polynomials', 'Quadratic equations', 'needed for'],
  ['Speed and velocity', 'Equations of motion', 'needed for'],
];

export function ConceptMapLinker({ links = MAP_LINKS }: { links?: [string, string, string][] }) {
  const lefts = useMemo(() => links.map((l) => l[0]), [links]);
  const rights = useMemo(() => [...links.map((l) => l[1])].reverse(), [links]);
  const [from, setFrom] = useState<string | null>(null);
  const [made, setMade] = useState<string[]>([]);
  const [note, setNote] = useState('');

  const connect = (to: string) => {
    if (!from) return;
    if (links.some((l) => l[0] === from && l[1] === to)) {
      soundFx.playStepVerified();
      setMade([...made, from]);
      setNote(`Linked: ${from} is needed for ${to}.`);
    } else {
      soundFx.playMistakeLogged();
      setNote(`${from} doesn't lead directly to ${to}. Try another.`);
    }
    setFrom(null);
  };

  return (
    <section className={card} aria-label="Concept map linker">
      <h3 className={heading}>Concept map: what builds on what?</h3>
      <p className={body}>Pick an idea on the left, then the idea that needs it on the right.</p>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          {lefts.map((l) => (
            <button key={l} type="button" disabled={made.includes(l)} aria-pressed={from === l} onClick={() => setFrom(l)}
              className={`block w-full rounded-lg border px-3 py-2 text-left text-sm text-[var(--text-primary)] ${made.includes(l) ? 'border-[var(--lg-mastery)] bg-[var(--lg-mastery-wash)]' : from === l ? 'border-[var(--lg-indigo)] bg-[var(--bg-hover)]' : 'border-[var(--border)]'}`}>{l}</button>
          ))}
        </div>
        <div className="space-y-2">
          {rights.map((r) => (
            <button key={r} type="button" disabled={!from} onClick={() => connect(r)} className="block w-full rounded-lg border border-[var(--border)] px-3 py-2 text-left text-sm text-[var(--text-primary)] disabled:opacity-70">{r}</button>
          ))}
        </div>
      </div>
      {note && <p role="status" className={body}>{note}</p>}
    </section>
  );
}

const VOICE_OPTIONS: { label: string; value: VoiceLanguage }[] = [
  { label: 'English', value: 'en-IN' },
  { label: 'हिन्दी', value: 'hi-IN' },
  { label: 'Hinglish', value: 'hi-IN' },
];

export function StructuredTeachBack({ conceptId, prompt }: { conceptId: string; prompt?: string }) {
  const [text, setText] = useState('');
  const [option, setOption] = useState(0);
  const [result, setResult] = useState<{ score: number; criteria: Record<string, boolean> } | null>(null);
  const [error, setError] = useState('');
  const voice = useVoiceInput({ language: VOICE_OPTIONS[0].value, onFinal: (t) => setText((old) => `${old} ${t}`.trim()) });

  const submit = async () => {
    setError('');
    try {
      const reply = await v1.ask({ message: text, mode: '07_teach_back', concept_id: conceptId });
      if (reply.outcome !== 'answered') {
        setError(reply.text);
        return;
      }
      setResult(reply.payload as { score: number; criteria: Record<string, boolean> });
      if (reply.payload.score >= 2) soundFx.playStepVerified();
    } catch {
      setError("I couldn't grade that right now. Your words are still here, so please try again.");
    }
  };

  const labels: Record<string, string> = { key_terms: 'Used the key ideas', reasoning: 'Explained why', example: 'Gave an example or relation' };

  return (
    <section className={card} aria-label="Teach back">
      <h3 className={heading}>Teach it back</h3>
      <p className={body}>{prompt ?? 'Explain this idea in your own words, as if teaching a friend.'}</p>
      <div className="flex flex-wrap items-center gap-2">
        {VOICE_OPTIONS.map((o, i) => (
          <button key={o.label} type="button" aria-pressed={option === i} className={option === i ? primary : secondary}
            onClick={() => { setOption(i); voice.setLanguage(o.value); }}>{o.label}</button>
        ))}
        {voice.isSupported && (
          <button type="button" className={secondary} onClick={voice.toggleListening} aria-pressed={voice.isListening}>
            {voice.isListening ? <MicOff className="inline w-4 h-4 mr-1" /> : <Mic className="inline w-4 h-4 mr-1" />}
            {voice.isListening ? 'Stop' : 'Speak'}
          </button>
        )}
      </div>
      <textarea className={input} rows={4} aria-label="Your explanation" value={text} onChange={(e) => setText(e.target.value)} />
      <button type="button" className={primary} disabled={!text.trim()} onClick={submit}>Check my explanation</button>
      {error && <p role="alert" className="text-sm font-medium text-[var(--lg-repair-text)]">{error}</p>}
      {result && (
        <div role="status" className="text-sm text-[var(--text-primary)]">
          <p className="font-semibold">Score: {result.score}/3 {result.score >= 2 ? '(+25 XP once per concept)' : ''}</p>
          <ul className="mt-1">
            {Object.entries(result.criteria).map(([key, met]) => (
              <li key={key} className={met ? 'text-[var(--lg-mastery-text)]' : 'text-[var(--lg-repair-text)]'}>{met ? 'Done: ' : 'Add: '}{labels[key]}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

/** Renders the activity the engine prescribes, by the name it sends. */
export function ActivityByName({ name, conceptId }: { name: string; conceptId: string }) {
  switch (name) {
    case 'AlgebraStepBuilder': return <AlgebraStepBuilder />;
    case 'CoordinateGraphPlotter': return <CoordinateGraphPlotter />;
    case 'RayOpticsBench': return <RayOpticsBench />;
    case 'VirtualScienceLab': return <VirtualScienceLab />;
    default: return <StructuredTeachBack conceptId={conceptId} />;
  }
}
