import { useEffect, useState } from 'react';
import AppLayout from '../components/AppLayout';
import { ActivityByName, StepAttributionBanner, StructuredTeachBack } from '../components/activities/Activities';
import ActivitySelector from '../components/activities/ActivitySelector';
import { soundFx } from '../lib/soundFx';
import { v1, type Concept, type Confidence, type NextStep, type PublicItem, type SubmitResult, type TutorMode, type TutorReply } from '../lib/v1Api';

const TABS = ['Today', 'Diagnostic', 'Practice', 'Tutor', 'Boss battle', 'Activities', 'Privacy'] as const;
type Tab = (typeof TABS)[number];

const panel = 'rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4 space-y-3';
const inputClass = 'w-full rounded-lg border border-[var(--border-strong)] bg-[var(--bg-card)] px-3 py-2 text-sm';
const primary = 'rounded-lg bg-[var(--lg-indigo)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50';
const secondary = 'rounded-lg border border-[var(--border-strong)] px-3 py-2 text-sm font-medium text-[var(--text-primary)]';
const muted = 'text-sm text-[var(--text-secondary)]';
const repair = 'text-sm font-medium text-[var(--lg-repair-text)]';

function apiMessage(error: any): string {
  const detail = error?.response?.data?.detail;
  if (detail?.code === 'consent_required') return 'A parent or guardian needs to approve this first. Open the Privacy tab.';
  if (detail?.code === 'class_required') return 'Set your class in Profile & Settings first.';
  if (detail?.code === 'daily_ai_limit') return "You've used today's 30 tutor questions. They refresh over the day.";
  return typeof detail === 'string' ? detail : 'Something went wrong. Please try again.';
}

function ConceptPicker({ concepts, value, onChange }: { concepts: Concept[]; value: string; onChange: (id: string) => void }) {
  return (
    <label className="block text-sm font-medium text-[var(--text-primary)]">Topic
      <select className={`${inputClass} mt-1`} value={value} onChange={(e) => onChange(e.target.value)}>
        {concepts.map((c) => <option key={c.concept_id} value={c.concept_id}>Class {c.class_level}: {c.title}</option>)}
      </select>
    </label>
  );
}

function TodayTab({ goTo }: { goTo: (tab: Tab) => void }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');
  const [when, setWhen] = useState('');
  const [action, setAction] = useState('');
  useEffect(() => { v1.studentDashboard().then(setData).catch((e) => setError(apiMessage(e))); }, []);
  if (error) return <p role="alert" className={repair}>{error}</p>;
  if (!data) return <p className={muted}>Loading your plan...</p>;
  const saveIntention = async () => {
    const saved = await v1.setIntention(when, action);
    setData({ ...data, intention: saved });
  };
  return (
    <div className="space-y-4">
      <section className={panel}>
        <h2 className="font-semibold text-[var(--text-primary)]">Pick your next task</h2>
        <p className={muted}>{data.plan.minutes.spaced_error_repair} min repair, {data.plan.minutes.core_progression} min new learning, {data.plan.minutes.interleaved_transfer} min mixed practice.</p>
        <div className="grid gap-2 sm:grid-cols-3">
          {data.plan.choices.map((task: any) => (
            <button key={`${task.category}-${task.concept_id}`} type="button" className={`${secondary} text-left`} onClick={() => goTo('Practice')}>
              <span className="block font-semibold">{task.title}</span>
              <span className="block text-xs text-[var(--text-secondary)]">{task.action}</span>
            </button>
          ))}
        </div>
      </section>
      <section className={panel}>
        <h2 className="font-semibold text-[var(--text-primary)]">Make a plan you'll keep</h2>
        {data.intention && <p className="text-sm font-medium text-[var(--lg-mastery-text)]">{data.intention.statement}</p>}
        <div className="grid gap-2 sm:grid-cols-2">
          <input className={inputClass} aria-label="When" placeholder="When: after dinner at 7 PM" value={when} onChange={(e) => setWhen(e.target.value)} />
          <input className={inputClass} aria-label="I will" placeholder="I will: do 15 minutes of Maths" value={action} onChange={(e) => setAction(e.target.value)} />
        </div>
        <button type="button" className={primary} disabled={when.length < 2 || action.length < 2} onClick={saveIntention}>Save my plan</button>
      </section>
      <section className={panel}>
        <h2 className="font-semibold text-[var(--text-primary)]">This week</h2>
        <p className={muted}>{data.shield.active_days} of {data.shield.target_days} active days{data.shield.shield_earned ? '. Consistency shield earned, so your rest days are protected.' : '.'}</p>
        <p className={muted}>Effort XP {data.xp.A}. Mastery XP {data.xp.B}.</p>
        <p className={muted}>Daily quest: {data.daily_quest.tasks.length} task(s).</p>
      </section>
    </div>
  );
}

function DiagnosticTab() {
  const [subject, setSubject] = useState('Mathematics');
  const [session, setSession] = useState<string | null>(null);
  const [item, setItem] = useState<PublicItem | null>(null);
  const [answer, setAnswer] = useState('');
  const [report, setReport] = useState<any>(null);
  const [count, setCount] = useState(0);
  const [error, setError] = useState('');

  const start = async () => {
    setError(''); setReport(null); setCount(0);
    try {
      const started = await v1.startDiagnostic(subject);
      setSession(started.session_id); setItem(started.item);
    } catch (e) { setError(apiMessage(e)); }
  };
  const submit = async () => {
    if (!session || !item) return;
    try {
      const step = await v1.answerDiagnostic(session, item.item_id, answer);
      setAnswer(''); setCount(count + 1);
      if (step.complete) { setItem(null); setReport(step.report); soundFx.playSessionComplete(); } else setItem(step.item);
    } catch (e) { setError(apiMessage(e)); }
  };

  return (
    <section className={panel}>
      <h2 className="font-semibold text-[var(--text-primary)]">Find your starting point (8 to 15 questions)</h2>
      {!item && !report && (
        <div className="flex gap-2">
          <select aria-label="Subject" className={inputClass} value={subject} onChange={(e) => setSubject(e.target.value)}>
            <option>Mathematics</option><option>Science</option>
          </select>
          <button type="button" className={primary} onClick={start}>Start</button>
        </div>
      )}
      {item && (
        <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); submit(); }}>
          <p className={muted}>Question {count + 1}</p>
          <p className="font-medium text-[var(--text-primary)]">{item.prompt}</p>
          <input className={inputClass} aria-label="Your answer" value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder={item.unit ? `Answer in ${item.unit}` : 'Your answer'} />
          <button className={primary} disabled={!answer.trim()}>Next</button>
        </form>
      )}
      {report && (
        <ul className="space-y-1 text-sm">
          {report.concepts.map((c: any) => (
            <li key={c.concept_id} className={c.weak ? 'text-[var(--lg-repair-text)]' : 'text-[var(--lg-mastery-text)]'}>
              {c.concept_id}: {c.correct}/{c.asked} correct{c.weak ? ', worth repairing' : ', looking solid'}
            </li>
          ))}
        </ul>
      )}
      {error && <p role="alert" className={repair}>{error}</p>}
    </section>
  );
}

function PracticeTab({ concepts }: { concepts: Concept[] }) {
  const [conceptId, setConceptId] = useState(concepts[0]?.concept_id ?? '');
  const [session, setSession] = useState<string | null>(null);
  const [next, setNext] = useState<NextStep | null>(null);
  const [prescription, setPrescription] = useState<any>(null);
  const [answer, setAnswer] = useState('');
  const [working, setWorking] = useState('');
  const [confidence, setConfidence] = useState<Confidence | null>(null);
  const [hintLevel, setHintLevel] = useState(0);
  const [hint, setHint] = useState('');
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [error, setError] = useState('');

  const start = async () => {
    setError(''); setResult(null);
    try {
      const started = await v1.startPractice(conceptId);
      setSession(started.session_id); setNext(started.next); setPrescription(started.prescription);
    } catch (e) { setError(apiMessage(e)); }
  };
  const item = next?.action === 'item' ? next.item : null;

  const requestHint = async () => {
    if (!item) return;
    const level = Math.min(hintLevel + 1, 3);
    const reply = await v1.ask({ message: 'hint', mode: '02_hint', concept_id: item.concept_id, item_id: item.item_id, hint_level: level });
    setHintLevel(level); setHint(reply.text); soundFx.playHintReveal();
  };
  const submit = async () => {
    if (!session || !item || !confidence) return;
    try {
      const steps = working.split('\n').map((l) => l.trim()).filter(Boolean);
      const r = await v1.submitPractice(session, { item_id: item.item_id, response: answer, steps, confidence, hints_used: hintLevel });
      setResult(r); setNext(r.next); setAnswer(''); setWorking(''); setConfidence(null); setHint(''); setHintLevel(0);
      if (r.correct) soundFx.playStepVerified(); else soundFx.playMistakeLogged();
    } catch (e) { setError(apiMessage(e)); }
  };
  const finishIntervention = async () => {
    if (!session) return;
    const done = await v1.interventionComplete(session);
    setNext(done.next); setPrescription(null); soundFx.playStepVerified();
  };

  return (
    <div className="space-y-4">
      <section className={panel}>
        <ConceptPicker concepts={concepts} value={conceptId} onChange={setConceptId} />
        <button type="button" className={primary} onClick={start}>{session ? 'Restart' : 'Start practice'}</button>
      </section>
      {prescription && (
        <section className={panel}>
          <h3 className="font-semibold text-[var(--text-primary)]">Quick repair first (about {prescription.estimated_minutes} minutes)</h3>
          <p className="text-sm text-[var(--text-primary)]">{prescription.worked_example.problem}</p>
          <ol className="list-decimal pl-5 text-sm text-[var(--text-primary)]">
            {prescription.worked_example.shown_steps.map((s: any) => <li key={s.equation}><span className="font-mono">{s.equation}</span>: {s.note}</li>)}
          </ol>
          <p className={muted}>Source: {prescription.worked_example.citation_id}</p>
          <button type="button" className={secondary} onClick={finishIntervention}>I've worked through this</button>
        </section>
      )}
      {result?.attribution && <StepAttributionBanner succeeded={result.attribution.succeeded} fix={result.attribution.fix} />}
      {result && (
        <p role="status" className={result.correct ? 'text-sm font-medium text-[var(--lg-mastery-text)]' : repair}>
          {result.correct ? `Verified. Tier ${result.tier}.` : `Not yet: the answer is ${result.correct_answer}.`}
          {result.entrenched_misconception ? " You felt sure about this one, so it's worth a closer look." : ''}
          {result.xp_awarded.map((x) => ` +${x.amount} XP${x.badge ? `, ${x.badge}` : ''}.`).join('')}
        </p>
      )}
      {item && (
        <form className={panel} onSubmit={(e) => { e.preventDefault(); submit(); }}>
          <p className="font-medium text-[var(--text-primary)]">{item.prompt}</p>
          <fieldset className="flex flex-wrap items-center gap-2">
            <legend className={`${muted} mb-1`}>How sure are you, before answering?</legend>
            {(['Sure', 'Unsure', 'Guess'] as Confidence[]).map((c) => (
              <button key={c} type="button" aria-pressed={confidence === c} className={confidence === c ? primary : secondary} onClick={() => setConfidence(c)}>{c}</button>
            ))}
          </fieldset>
          <textarea className={`${inputClass} font-mono`} rows={3} aria-label="Your working, one line per step" placeholder={'Optional working, one step per line\n2x + 3 = 7'} value={working} onChange={(e) => setWorking(e.target.value)} />
          <input className={inputClass} aria-label="Your answer" value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder={item.unit ? `Answer in ${item.unit}` : 'Your answer'} />
          {hint && <p role="status" className="rounded-lg bg-[var(--bg-secondary)] p-2 text-sm text-[var(--text-primary)]">{hint}</p>}
          <div className="flex gap-2">
            <button className={primary} disabled={!answer.trim() || !confidence}>Check</button>
            <button type="button" className={secondary} disabled={hintLevel >= 3} onClick={requestHint}>Hint ({hintLevel}/3)</button>
          </div>
        </form>
      )}
      {next?.action === 'simulation' && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-[var(--text-primary)]">{next.reason}</p>
          <ActivityByName name={next.activity} conceptId={conceptId} />
          <button type="button" className={secondary} onClick={finishIntervention}>I'm ready to try again</button>
        </div>
      )}
      {next?.action === 'exhausted' && <p className={muted}>You've done every question for this topic. Try another topic.</p>}
      {error && <p role="alert" className={repair}>{error}</p>}
    </div>
  );
}

const MODES: { id: TutorMode; label: string }[] = [
  { id: '01_explain', label: 'Explain' }, { id: '03_step_by_step', label: 'Step by step' },
  { id: '04_socratic', label: 'Socratic' }, { id: '05_mistake_repair', label: 'Mistake repair' },
  { id: '06_quiz', label: 'Quiz' }, { id: '08_revision', label: 'Revision' },
  { id: '09_exam_simulation', label: 'Exam simulation' }, { id: '10_challenge_transfer', label: 'Challenge' },
];

function TutorTab({ concepts }: { concepts: Concept[] }) {
  const [conceptId, setConceptId] = useState(concepts[0]?.concept_id ?? '');
  const [mode, setMode] = useState<TutorMode>('01_explain');
  const [message, setMessage] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [reply, setReply] = useState<TutorReply | null>(null);
  const [answer, setAnswer] = useState('');
  const [confidence, setConfidence] = useState<Confidence>('Unsure');
  const [fadeStage, setFadeStage] = useState(0);
  const [paperAnswers, setPaperAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState('');

  const send = async (extra: Record<string, unknown> = {}) => {
    setError('');
    try {
      const r = await v1.ask({ message: message || mode, mode, concept_id: conceptId, session_id: sessionId, fade_stage: fadeStage, ...extra });
      setReply(r);
      if (r.payload.session_id) setSessionId(r.payload.session_id);
      if (r.payload.next_stage !== undefined) setFadeStage(r.payload.next_stage);
    } catch (e) { setError(apiMessage(e)); }
  };
  const pickMode = (id: TutorMode) => { setMode(id); setSessionId(undefined); setReply(null); setFadeStage(0); setPaperAnswers({}); };
  const quizItem = reply?.payload.item;
  const paper: PublicItem[] | undefined = reply?.payload.items;

  return (
    <div className="space-y-4">
      <section className={panel}>
        <ConceptPicker concepts={concepts} value={conceptId} onChange={(id) => { setConceptId(id); setSessionId(undefined); setReply(null); }} />
        <div className="flex flex-wrap gap-2" role="group" aria-label="Tutor mode">
          {MODES.map((m) => <button key={m.id} type="button" aria-pressed={mode === m.id} className={mode === m.id ? primary : secondary} onClick={() => pickMode(m.id)}>{m.label}</button>)}
        </div>
        <textarea className={inputClass} rows={2} aria-label="Your question" placeholder="Ask about this topic" value={message} onChange={(e) => setMessage(e.target.value)} />
        <button type="button" className={primary} onClick={() => send()}>Ask</button>
      </section>
      {reply && (
        <section className={panel} aria-live="polite">
          {reply.outcome === 'support' ? <p className="font-medium text-[var(--text-primary)]">{reply.text}</p> : (
            <p className="text-[var(--text-primary)]">{reply.text}</p>
          )}
          {reply.fallback_card?.card && Object.entries(reply.fallback_card.card as Record<string, string>).map(([k, v]) => <p key={k} className="text-sm text-[var(--text-primary)]"><strong>{k.replace('_', ' ')}:</strong> {v}</p>)}
          {reply.fallback_card?.topics && <p className={muted}>{(reply.fallback_card.topics as string[]).join(', ')}</p>}
          {reply.citations.length > 0 && <p className={muted}>Source: {reply.citations.join(', ')}</p>}
          {reply.payload.flashcards?.map((f: any) => <p key={f.front} className="text-sm text-[var(--text-primary)]"><strong>{f.front}</strong> {f.back}</p>)}
          {quizItem && (
            <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); send({ answer, confidence }); setAnswer(''); }}>
              <input className={inputClass} aria-label="Your answer" value={answer} onChange={(e) => setAnswer(e.target.value)} />
              <select aria-label="Confidence" className={inputClass} value={confidence} onChange={(e) => setConfidence(e.target.value as Confidence)}>
                <option>Sure</option><option>Unsure</option><option>Guess</option>
              </select>
              <button className={primary} disabled={!answer.trim()}>Submit</button>
            </form>
          )}
          {reply.payload.correct !== undefined && (
            <p role="status" className={reply.payload.correct ? 'text-sm font-medium text-[var(--lg-mastery-text)]' : repair}>
              {reply.payload.entrenched_misconception ? 'You felt sure, so this may be a misunderstanding worth repairing.' : ''}
            </p>
          )}
          {paper && (
            <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); send({ answers: paperAnswers }); }}>
              {paper.map((q, i) => (
                <label key={q.item_id} className="block text-sm text-[var(--text-primary)]">{i + 1}. {q.prompt}
                  <input className={`${inputClass} mt-1`} value={paperAnswers[q.item_id] ?? ''} onChange={(e) => setPaperAnswers({ ...paperAnswers, [q.item_id]: e.target.value })} />
                </label>
              ))}
              <button className={primary}>Finish paper</button>
            </form>
          )}
          {reply.payload.score !== undefined && reply.payload.total !== undefined && <p className="font-semibold text-[var(--text-primary)]">Score: {reply.payload.score}/{reply.payload.total}</p>}
        </section>
      )}
      <StructuredTeachBack conceptId={conceptId} />
      {error && <p role="alert" className={repair}>{error}</p>}
    </div>
  );
}

function BossTab({ concepts }: { concepts: Concept[] }) {
  const [picked, setPicked] = useState<string[]>([]);
  const [boss, setBoss] = useState<any>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [outcome, setOutcome] = useState<any>(null);
  const [error, setError] = useState('');
  const start = async () => {
    setError(''); setOutcome(null);
    try { setBoss(await v1.startBoss(picked)); setAnswers({}); } catch (e) { setError(apiMessage(e)); }
  };
  const finish = async () => {
    try {
      const result = await v1.submitBoss(boss.quest_id, answers);
      setOutcome(result); setBoss(null);
      if (result.boss_mastered) soundFx.playBossMastery(); else soundFx.playMistakeLogged();
    } catch (e) { setError(apiMessage(e)); }
  };
  return (
    <section className="rounded-xl border-2 border-[var(--lg-boss)] bg-[var(--bg-card)] p-4 space-y-3">
      <h2 className="font-semibold text-[var(--lg-boss-text)]">Chapter boss battle (20 to 25 minutes)</h2>
      {!boss && (
        <>
          <p className={muted}>Choose 2 to 5 topics to combine.</p>
          <div className="flex flex-wrap gap-2">
            {concepts.map((c) => {
              const on = picked.includes(c.concept_id);
              return <button key={c.concept_id} type="button" aria-pressed={on} className={on ? primary : secondary} onClick={() => setPicked(on ? picked.filter((p) => p !== c.concept_id) : [...picked, c.concept_id].slice(0, 5))}>{c.title}</button>;
            })}
          </div>
          <button type="button" className={primary} disabled={picked.length < 2} onClick={start}>Begin battle</button>
        </>
      )}
      {boss && (
        <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); finish(); }}>
          {boss.items.map((q: PublicItem, i: number) => (
            <label key={q.item_id} className="block text-sm text-[var(--text-primary)]">{i + 1}. {q.prompt}
              <input className={`${inputClass} mt-1`} value={answers[q.item_id] ?? ''} onChange={(e) => setAnswers({ ...answers, [q.item_id]: e.target.value })} />
            </label>
          ))}
          <button className={primary}>Finish battle</button>
        </form>
      )}
      {outcome && <p role="status" className={outcome.boss_mastered ? 'font-semibold text-[var(--lg-boss-text)]' : repair}>{outcome.correct}/{outcome.total} correct. {outcome.boss_mastered ? 'Boss mastered!' : 'You need 80%. Repair the gaps, then come back.'}</p>}
      {error && <p role="alert" className={repair}>{error}</p>}
    </section>
  );
}

function ActivitiesTab({ conceptId }: { conceptId: string }) {
  return <ActivitySelector conceptId={conceptId} />;
}

function downloadBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = name; link.click();
  URL.revokeObjectURL(url);
}

const PURPOSE_LABELS: Record<string, string> = {
  learning_analytics: 'Personalised learning', parent_reports: 'Parent progress reports', school_sharing: 'Sharing with my school',
};

function PrivacyTab() {
  const [status, setStatus] = useState<Record<string, boolean>>({});
  const [contact, setContact] = useState('');
  const [purpose, setPurpose] = useState('learning_analytics');
  const [requestId, setRequestId] = useState('');
  const [otp, setOtp] = useState('');
  const [message, setMessage] = useState('');
  const [confirmErase, setConfirmErase] = useState('');
  const [mfa, setMfa] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [mfaCode, setMfaCode] = useState('');
  const refresh = () => v1.consentStatus().then(setStatus).catch((e) => setMessage(apiMessage(e)));
  useEffect(() => { refresh(); }, []);
  const send = async () => {
    try {
      const r = await v1.requestOtp(contact, purpose);
      setRequestId(r.request_id);
      setMessage(r.dev_otp ? `Development mode, code: ${r.dev_otp}` : 'Code sent to your parent or guardian.');
    } catch (e) { setMessage(apiMessage(e)); }
  };
  const verify = async () => {
    try { await v1.verifyOtp(requestId, otp); setMessage('Approved. Thank you.'); setRequestId(''); setOtp(''); refresh(); } catch (e) { setMessage(apiMessage(e)); }
  };
  const verifyMfa = async () => {
    try {
      const { mfa_token } = await v1.verifyMfa(mfaCode);
      const { saveMfaToken } = await import('../lib/v1Api');
      saveMfaToken(mfa_token); setMessage('Two-step verification is active for this session.'); setMfa(null);
    } catch (e) { setMessage(apiMessage(e)); }
  };
  return (
    <div className="space-y-4">
      <section className={panel}>
        <h2 className="font-semibold text-[var(--text-primary)]">Parent or guardian approval</h2>
        <ul className="text-sm">
          {Object.entries(status).map(([key, granted]) => (
            <li key={key} className="flex items-center justify-between gap-2 py-1 text-[var(--text-primary)]">
              <span>{PURPOSE_LABELS[key] ?? key}: {granted ? 'approved' : 'not approved'}</span>
              {granted && <button type="button" className={secondary} onClick={async () => { await v1.withdrawConsent(key); refresh(); }}>Withdraw</button>}
            </li>
          ))}
        </ul>
        <select aria-label="What to approve" className={inputClass} value={purpose} onChange={(e) => setPurpose(e.target.value)}>
          {Object.entries(PURPOSE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input className={inputClass} aria-label="Parent or guardian mobile or email" placeholder="Parent or guardian mobile or email" value={contact} onChange={(e) => setContact(e.target.value)} />
        <button type="button" className={primary} disabled={contact.length < 5} onClick={send}>Send code</button>
        {requestId && (
          <div className="flex gap-2">
            <input className={inputClass} aria-label="6-digit code" inputMode="numeric" value={otp} onChange={(e) => setOtp(e.target.value)} />
            <button type="button" className={primary} disabled={otp.length !== 6} onClick={verify}>Confirm</button>
          </div>
        )}
      </section>
      <section className={panel}>
        <h2 className="font-semibold text-[var(--text-primary)]">Your data</h2>
        <div className="flex gap-2">
          <button type="button" className={secondary} onClick={async () => downloadBlob(await v1.exportData('json'), 'learn-genie-data.json')}>Download JSON</button>
          <button type="button" className={secondary} onClick={async () => downloadBlob(await v1.exportData('pdf'), 'learn-genie-data.pdf')}>Download PDF</button>
        </div>
        <label className="block text-sm text-[var(--text-primary)]">To permanently delete your learning data, type ERASE
          <input className={`${inputClass} mt-1`} value={confirmErase} onChange={(e) => setConfirmErase(e.target.value)} /></label>
        <button type="button" className="rounded-lg border-2 border-[var(--lg-destructive)] bg-[var(--lg-destructive-wash)] px-3 py-2 text-sm font-semibold text-[var(--lg-destructive)] disabled:opacity-50" disabled={confirmErase !== 'ERASE'} onClick={async () => {
          const result = await v1.eraseData();
          setMessage(result.status === 'completed' ? 'Your learning data has been deleted.' : 'Deletion has started and will finish within 72 hours.');
          setConfirmErase('');
        }}>Delete my data</button>
      </section>
      <section className={panel}>
        <h2 className="font-semibold text-[var(--text-primary)]">Two-step verification (teachers and admins)</h2>
        {!mfa && <button type="button" className={secondary} onClick={async () => { try { setMfa(await v1.enrollMfa()); } catch (e) { setMessage(apiMessage(e)); } }}>Set up</button>}
        {mfa && <p className="break-all text-sm text-[var(--text-primary)]">Add this key to your authenticator app: <span className="font-mono">{mfa.secret}</span></p>}
        <div className="flex gap-2">
          <input className={inputClass} aria-label="Authenticator code" inputMode="numeric" placeholder="6-digit code" value={mfaCode} onChange={(e) => setMfaCode(e.target.value)} />
          <button type="button" className={primary} disabled={mfaCode.length !== 6} onClick={verifyMfa}>Verify</button>
        </div>
      </section>
      {message && <p role="status" className="text-sm font-medium text-[var(--text-primary)]">{message}</p>}
    </div>
  );
}

export default function LearnStudioPage() {
  const [tab, setTab] = useState<Tab>(() => {
    const requested = new URLSearchParams(window.location.search).get('tab');
    return TABS.find((t) => t === requested) ?? 'Today';
  });
  const [concepts, setConcepts] = useState<Concept[]>([]);
  useEffect(() => { v1.concepts().then(setConcepts).catch(() => setConcepts([])); }, []);

  return (
    <AppLayout title="Learn Studio">
      <div className="mx-auto w-full max-w-5xl space-y-4 p-4 sm:p-6">
        <nav className="flex flex-wrap gap-2" aria-label="Learn Studio sections">
          {TABS.map((t) => <button key={t} type="button" aria-current={tab === t ? 'page' : undefined} className={tab === t ? primary : secondary} onClick={() => setTab(t)}>{t}</button>)}
        </nav>
        {tab === 'Today' && <TodayTab goTo={setTab} />}
        {tab === 'Diagnostic' && <DiagnosticTab />}
        {tab === 'Practice' && (concepts.length ? <PracticeTab concepts={concepts} /> : <p className={muted}>Loading topics...</p>)}
        {tab === 'Tutor' && (concepts.length ? <TutorTab concepts={concepts} /> : <p className={muted}>Loading topics...</p>)}
        {tab === 'Boss battle' && <BossTab concepts={concepts} />}
        {tab === 'Activities' && <ActivitiesTab conceptId={concepts[0]?.concept_id ?? 'm8_linear_one'} />}
        {tab === 'Privacy' && <PrivacyTab />}
      </div>
    </AppLayout>
  );
}
