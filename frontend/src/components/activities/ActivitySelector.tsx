import { useState } from 'react';
import { Blocks, X } from 'lucide-react';
import {
  AlgebraStepBuilder, ConceptMapLinker, CoordinateGraphPlotter, InteractiveDiagramPin, RayOpticsBench,
  SpotTheErrorChallenge, StructuredTeachBack, VirtualScienceLab,
} from './Activities';
import {
  ChemicalEquationBalancer, CircuitBuilderLab, EquationBalanceScale, FadedWorkedExampleStepper, FractionNumberLine,
  FreeBodyVectorLab, GeometryAngleExplorer, SortingClassificationBuckets, TimelineSequenceBuilder,
} from './MoreActivities';

type Vark = 'Visual' | 'Auditory' | 'Read/Write' | 'Kinesthetic';

export const ACTIVITIES: { id: string; label: string; vark: Vark; render: (conceptId: string) => React.ReactNode }[] = [
  { id: 'graph', label: 'Graph plotter', vark: 'Visual', render: () => <CoordinateGraphPlotter /> },
  { id: 'optics', label: 'Ray optics bench', vark: 'Visual', render: () => <RayOpticsBench /> },
  { id: 'vectors', label: 'Free-body vectors', vark: 'Visual', render: () => <FreeBodyVectorLab /> },
  { id: 'angles', label: 'Angle explorer', vark: 'Visual', render: () => <GeometryAngleExplorer /> },
  { id: 'teachback', label: 'Teach it back', vark: 'Auditory', render: (c) => <StructuredTeachBack conceptId={c} /> },
  { id: 'faded', label: 'Faded worked example', vark: 'Read/Write', render: () => <FadedWorkedExampleStepper /> },
  { id: 'spot', label: 'Spot the error', vark: 'Read/Write', render: () => <SpotTheErrorChallenge /> },
  { id: 'sequence', label: 'Sequence builder', vark: 'Read/Write', render: () => <TimelineSequenceBuilder /> },
  { id: 'map', label: 'Concept map', vark: 'Read/Write', render: () => <ConceptMapLinker /> },
  { id: 'algebra', label: 'Algebra step builder', vark: 'Kinesthetic', render: () => <AlgebraStepBuilder /> },
  { id: 'scale', label: 'Balance scale', vark: 'Kinesthetic', render: () => <EquationBalanceScale /> },
  { id: 'fractions', label: 'Fraction number line', vark: 'Kinesthetic', render: () => <FractionNumberLine /> },
  { id: 'lab', label: 'Virtual science lab', vark: 'Kinesthetic', render: () => <VirtualScienceLab /> },
  { id: 'circuit', label: 'Circuit builder', vark: 'Kinesthetic', render: () => <CircuitBuilderLab /> },
  { id: 'chemistry', label: 'Equation balancer', vark: 'Kinesthetic', render: () => <ChemicalEquationBalancer /> },
  { id: 'pin', label: 'Label the diagram', vark: 'Kinesthetic', render: () => <InteractiveDiagramPin /> },
  { id: 'sort', label: 'Sorting buckets', vark: 'Kinesthetic', render: () => <SortingClassificationBuckets /> },
];

export default function ActivitySelector({ conceptId = 'm8_linear_one' }: { conceptId?: string }) {
  const [selected, setSelected] = useState(ACTIVITIES[0].id);
  const activity = ACTIVITIES.find((a) => a.id === selected) ?? ACTIVITIES[0];
  const groups: Vark[] = ['Visual', 'Auditory', 'Read/Write', 'Kinesthetic'];
  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-[var(--text-primary)]">Choose an activity
        <select className="mt-1 w-full rounded-lg border border-[var(--border-strong)] bg-[var(--bg-card)] px-3 py-2 text-sm" value={selected} onChange={(e) => setSelected(e.target.value)}>
          {groups.map((group) => (
            <optgroup key={group} label={group}>
              {ACTIVITIES.filter((a) => a.vark === group).map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
            </optgroup>
          ))}
        </select>
      </label>
      {activity.render(conceptId)}
    </div>
  );
}

/** A slide-over, so that activities can sit beside fixed-height pages such as Chat. */
export function ActivityDrawer({ conceptId }: { conceptId?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="fixed bottom-24 right-4 z-30 flex items-center gap-2 rounded-full bg-[var(--lg-indigo)] px-4 py-2 text-sm font-semibold text-white shadow-lg">
        <Blocks className="h-4 w-4" aria-hidden /> Activities
      </button>
      {open && (
        <div role="dialog" aria-modal="true" aria-label="Learning activities" className="fixed inset-y-0 right-0 z-50 w-full max-w-md space-y-3 overflow-y-auto border-l border-[var(--border)] bg-[var(--bg-primary)] p-4 shadow-2xl">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-[var(--text-primary)]">Activities</h2>
            <button type="button" autoFocus aria-label="Close activities" className="rounded-lg p-2 hover:bg-[var(--bg-hover)]" onClick={() => setOpen(false)}><X className="h-4 w-4" /></button>
          </div>
          <ActivitySelector conceptId={conceptId} />
        </div>
      )}
    </>
  );
}
