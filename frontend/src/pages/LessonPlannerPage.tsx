import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles, Clock, CheckCircle2, PlayCircle, BookOpen,
  Presentation, Video, HelpCircle, ListChecks, PenTool,
  Loader2, AlertTriangle, Lock, FileText, CheckCircle, Zap,
  Plus, Share2, Download, Compass, X,
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import HistorySidebar from '../components/HistorySidebar';
import { useSidebarCollapse } from '../hooks/useSidebarCollapse';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';

// Types mapping to Backend schemas
type StageStatus = 'locked' | 'available' | 'in_progress' | 'material_ready' | 'taught' | 'assessment_pending' | 'mastered' | 'needs_review' | 'blocked';
type StageReadiness = 'ready' | 'prerequisite_required' | 'review_recommended' | 'blocked';
type ResourceType = 'ppt' | 'video' | 'teach_me' | 'quiz' | 'notes' | 'worksheet' | 'homework' | 'diagram';
type ResourceStatus = 'not_needed' | 'recommended' | 'optional' | 'selected' | 'generating' | 'ready' | 'failed' | 'stale';

interface LearningObjective {
  id: string;
  description: string;
  bloom_level: string;
}

interface StageActivity {
  id?: string;
  type: string;
  title?: string;
  description: string;
  duration_minutes: number;
}

interface ResourceRecommendation {
  resource_type: ResourceType;
  usefulness_score: number;
  status: ResourceStatus;
  reason: string;
  resource_url?: string;
}

interface StageDifferentiation {
  core: string;
  support: string;
  extension: string;
}

interface SourceReference {
  source_type: string;
  title: string;
  page?: number;
  slide?: number;
  timestamp?: string;
}

interface RoadmapStage {
  id: string;
  concept_id: string;
  title: string;
  description: string;
  sequence: number;
  duration_minutes: number;
  status: StageStatus;
  readiness: StageReadiness;
  mastery: number;
  confidence: number;
  objectives: LearningObjective[];
  prerequisite_ids: string[];
  teacher_actions: string[];
  student_actions: string[];
  evidence_of_learning: string;
  activities: StageActivity[];
  checkpoint_questions: string[];
  expected_misconceptions: string[];
  differentiation: StageDifferentiation;
  resource_recommendations: ResourceRecommendation[];
  source_refs: SourceReference[];
  is_remedial?: boolean;
}

interface LearningRoadmap {
  id: string;
  course_id: string;
  topic: string;
  title?: string;
  description?: string;
  level: string;
  language: string;
  class_type: string;
  target_duration_minutes: number;
  status: 'draft' | 'reviewed' | 'published' | 'archived';
  stages: RoadmapStage[];
  next_best_action: string;
  overall_progress: number;
  health_score: number;
  version: number;
}

/** Cards map to the resource_type values the backend recommends. */
const RESOURCE_CARDS: {
  type: string;
  key: ResourceType;
  icon: React.ElementType;
  label: string;
  desc: string;
  cta: string;
}[] = [
  { type: 'PPT', key: 'ppt', icon: Presentation, label: 'PowerPoint', desc: 'Multi-slide deck with concept diagrams and speaker notes.', cta: 'Create PPT deck' },
  { type: 'Video', key: 'video', icon: Video, label: 'Video lesson', desc: 'Micro-learning video storyboard with voice narration.', cta: 'Create video lesson' },
  { type: 'Teach', key: 'teach_me', icon: BookOpen, label: 'Teach Me', desc: 'Interactive dialogue with live checkpoints.', cta: 'Launch Teach Me' },
  { type: 'Quiz', key: 'quiz', icon: HelpCircle, label: 'Quiz', desc: 'Diagnostic questions addressing common misconceptions.', cta: 'Create quiz' },
  { type: 'Notes', key: 'notes', icon: FileText, label: 'Study notes', desc: 'Revision notes with key definitions.', cta: 'Generate notes' },
];

const RESOURCE_STATUS_LABELS: Partial<Record<ResourceStatus, string>> = {
  recommended: 'Recommended',
  optional: 'Optional',
  selected: 'Selected',
  generating: 'Generating',
  ready: 'Ready',
  failed: 'Failed',
  stale: 'Out of date',
  not_needed: 'Not needed',
};

const LessonPlannerPage: React.FC = () => {
  const { collapsed: historySidebarCollapsed, toggle: toggleHistorySidebar } = useSidebarCollapse('lesson-history');
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialRoadmapId = searchParams.get('id') || null;

  // Prompt & Config States
  const [promptInput, setPromptInput] = useState('');
  const [selectedSources, setSelectedSources] = useState<string[]>(['Topic', 'Syllabus']);
  const [isParsing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [parsedConfig, setParsedConfig] = useState({
    topic: 'DBMS Normalization',
    course: 'Database Management Systems',
    level: 'B.Tech',
    language: 'english',
    class_type: 'Interactive Lecture',
    duration_minutes: 60,
    goal: 'Step-by-step normal forms with decomposition examples.'
  });

  // Roadmap & Stage States
  const [roadmap, setRoadmap] = useState<LearningRoadmap | null>(null);
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'details' | 'timeline' | 'differentiation'>('details');
  const [healthScore, setHealthScore] = useState<any>(null);
  const [isEditingStage, setIsEditingStage] = useState(false);
  const [editForm, setEditForm] = useState({ title: '', duration_minutes: 15, teacher_action: '', student_action: '' });
  const [actionNotification, setActionNotification] = useState<string | null>(null);
  /* Separate from actionNotification so a failure is never styled or worded
     as a success. Previously some failures reported success. */
  const [errorNotification, setErrorNotification] = useState<string | null>(null);
  const [isTriggeringResource, setIsTriggeringResource] = useState<string | null>(null);
  
  const [historyItems, setHistoryItems] = useState<any[]>([]);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/`, {
          headers: { 'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setHistoryItems(data.roadmaps || []);
        }
        
        // Auto-load roadmap if id in URL
        if (initialRoadmapId && !roadmap) {
          loadRoadmap(initialRoadmapId);
        }
      } catch (err) {
        console.error('Failed to load history:', err);
      }
    };
    fetchHistory();
  }, [initialRoadmapId]);

  const loadRoadmap = async (id: string) => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${id}`, {
        headers: { 'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setRoadmap(data.roadmap);
        setSearchParams(prev => { prev.set('id', id); return prev; });
        if (data.roadmap.stages.length > 0) setSelectedStageId(data.roadmap.stages[0].id);
        fetchHealth(id);
      } else {
        throw new Error('Failed to fetch');
      }
    } catch (e) {
      console.error(e);
      setErrorNotification('Failed to load past roadmap.');
    }
  };

  const selectedStage = roadmap?.stages.find(s => s.id === selectedStageId) || roadmap?.stages[0] || null;

  // Auto-parse prompt heuristics
  const handlePromptChange = async (val: string) => {
    setPromptInput(val);
    if (val.length > 20 && !isParsing) {
      // Auto-extract topic
      const clean = val.replace(/^mujhe\s+/i, '').replace(/\s+padhana\s+hai.*/i, '');
      if (clean.length > 5 && clean.length < 60) {
        setParsedConfig(prev => ({ ...prev, topic: clean }));
      }
    }
  };

  const handleSourceToggle = (src: string) => {
    setSelectedSources(prev =>
      prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]
    );
  };

  const generateRoadmap = async () => {
    setIsGenerating(true);
    setActionNotification(null);
    setErrorNotification(null);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        },
        body: JSON.stringify({
          topic: parsedConfig.topic || "DBMS Normalization",
          level: parsedConfig.level,
          language: parsedConfig.language,
          class_type: parsedConfig.class_type,
          target_duration_minutes: parsedConfig.duration_minutes,
          custom_context: `Sources used: ${selectedSources.join(', ')}. Goal: ${parsedConfig.goal}`
        })
      });

      if (!response.ok) throw new Error("Failed to generate roadmap.");
      const data: LearningRoadmap = await response.json();
      setRoadmap(data);
      if (data.stages.length > 0) {
        setSelectedStageId(data.stages[0].id);
      }
      fetchHealth(data.id);
      // add to history top
      setHistoryItems(prev => [{ id: data.id, title: data.topic, date: new Date().toISOString() }, ...prev]);
    } catch (err) {
      console.error(err);
      setErrorNotification('Could not generate the roadmap. Please check your connection and try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const fetchHealth = async (id: string) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${id}/health`, {
        headers: { 'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}` }
      });
      if (response.ok) {
        setHealthScore(await response.json());
      }
    } catch (e) {
      console.error('Failed to fetch lesson health', e);
    }
  };

  const handleStageSelect = (stage: RoadmapStage) => {
    setSelectedStageId(stage.id);
    setIsEditingStage(false);
    setEditForm({
      title: stage.title,
      duration_minutes: stage.duration_minutes,
      teacher_action: stage.teacher_actions[0] || '',
      student_action: stage.student_actions[0] || ''
    });
  };

  const handleSaveStageEdit = async () => {
    if (!roadmap || !selectedStage) return;
    setErrorNotification(null);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/stages/${selectedStage.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        },
        body: JSON.stringify({
          title: editForm.title,
          duration_minutes: editForm.duration_minutes,
          teacher_actions: editForm.teacher_action ? [editForm.teacher_action] : selectedStage.teacher_actions,
          student_actions: editForm.student_action ? [editForm.student_action] : selectedStage.student_actions,
          expected_version: roadmap.version
        })
      });

      if (response.status === 409) {
        setErrorNotification('This roadmap was changed elsewhere. Reload the page before saving again.');
        return;
      }

      if (response.ok) {
        const resData = await response.json();
        setRoadmap(prev => {
          if (!prev) return null;
          return {
            ...prev,
            version: resData.new_version,
            next_best_action: resData.next_best_action,
            stages: prev.stages.map(s => s.id === selectedStage.id ? { ...s, ...resData.stage } : s)
          };
        });
        setIsEditingStage(false);
        fetchHealth(roadmap.id);
        setActionNotification(`Stage "${editForm.title}" updated.`);
      } else {
        setErrorNotification('Could not save the stage. Please try again.');
      }
    } catch (err) {
      console.error(err);
      setErrorNotification('Could not save the stage. Please try again.');
    }
  };

  const handleMarkTaught = async (stage: RoadmapStage) => {
    if (!roadmap) return;
    setErrorNotification(null);
    try {
      const nextStatus: StageStatus = stage.status === 'taught' ? 'available' : 'taught';
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/stages/${stage.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        },
        body: JSON.stringify({
          status: nextStatus,
          expected_version: roadmap.version
        })
      });

      if (response.ok) {
        const resData = await response.json();
        setRoadmap(prev => {
          if (!prev) return null;
          const updatedStages = prev.stages.map(s => s.id === stage.id ? { ...s, status: nextStatus } : s);
          return {
            ...prev,
            version: resData.new_version,
            next_best_action: resData.next_best_action,
            stages: updatedStages
          };
        });
        setActionNotification(`Stage marked as ${nextStatus.replace('_', ' ')}.`);
      } else {
        setErrorNotification('Could not update the stage status. Please try again.');
      }
    } catch (e) {
      console.error('Failed to mark stage taught', e);
      setErrorNotification('Could not update the stage status. Please try again.');
    }
  };

  const handleCreateRemedial = async (stage: RoadmapStage) => {
    if (!roadmap) return;
    setErrorNotification(null);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/remedial`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        },
        body: JSON.stringify({
          target_stage_id: stage.id,
          weak_prereq_title: stage.title,
          expected_version: roadmap.version
        })
      });

      if (response.ok) {
        const resData = await response.json();
        setRoadmap(prev => {
          if (!prev) return null;
          const idx = prev.stages.findIndex(s => s.id === stage.id);
          const newStages = [...prev.stages];
          newStages.splice(idx, 0, resData.remedial_stage);
          return {
            ...prev,
            version: resData.new_version,
            stages: newStages
          };
        });
        setSelectedStageId(resData.remedial_stage.id);
        setActionNotification('Remedial recap stage added to the roadmap.');
      } else {
        setErrorNotification('Could not add a remedial stage. Please try again.');
      }
    } catch (e) {
      console.error('Failed to create remedial stage', e);
      setErrorNotification('Could not add a remedial stage. Please try again.');
    }
  };

  const handleGenerateResource = async (type: string) => {
    if (!roadmap || !selectedStage) return;
    setIsTriggeringResource(type);
    setErrorNotification(null);
    try {
      const endpoint = type.toLowerCase().replace(' ', '_');
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/stages/${selectedStage.id}/${endpoint}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        
        // Update local roadmap to mark resource as ready
        setRoadmap(prev => {
          if (!prev) return prev;
          const updatedStages = prev.stages.map(s => {
            if (s.id === selectedStage.id) {
              const updatedRecs = s.resource_recommendations?.map(r => {
                if (r.resource_type === endpoint) {
                  return { ...r, status: 'ready' as ResourceStatus };
                }
                return r;
              });
              return { ...s, resource_recommendations: updatedRecs };
            }
            return s;
          });
          return { ...prev, stages: updatedStages };
        });

        setActionNotification(`Generated ${type} for "${selectedStage.title}".`);
        
        if (type === 'PPT') {
          navigate('/decks', { state: { presetConfig: data.config } });
        } else if (type === 'Video') {
          navigate('/video', { state: { presetConfig: data.config } });
        } else if (type === 'Teach') {
          navigate('/teach', { state: { presetBrief: data.brief } });
        } else if (type === 'Quiz') {
          navigate('/quizzes', { state: { presetConfig: data.config } });
        }
        // Notes doesn't have dedicated pages yet, so they just stay here and show notification.
      } else {
        /* Previously this path was silent, and the catch below reported
           success. A failure now reports a failure. */
        setErrorNotification(`Could not generate ${type}. Please try again.`);
      }
    } catch (e) {
      console.error('Resource generation failed', e);
      setErrorNotification(`Could not generate ${type}. Please try again.`);
    } finally {
      setIsTriggeringResource(null);
    }
  };

  const handleGenerateStudyPack = async () => {
    if (!roadmap) return;
    setIsTriggeringResource('studypack');
    setErrorNotification(null);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/study-pack`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        }
      });
      if (response.ok) {
        await loadRoadmap(roadmap.id);
        setActionNotification('Study pack generated from the lesson plan.');
      } else {
        setErrorNotification('Could not generate the study pack. Please try again.');
      }
    } catch (e) {
      console.error('Study pack generation failed', e);
      setErrorNotification('Could not generate the study pack. Please try again.');
    } finally {
      setIsTriggeringResource(null);
    }
  };

  const handlePublish = async () => {
    if (!roadmap) return;
    setErrorNotification(null);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/publish`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}` }
      });
      if (res.ok) {
        setRoadmap(prev => prev ? { ...prev, status: 'published' } : null);
        setActionNotification('Roadmap published to your course library.');
      } else {
        setErrorNotification('Could not publish the roadmap. Please try again.');
      }
    } catch (e) {
      console.error('Publish failed', e);
      setErrorNotification('Could not publish the roadmap. Please try again.');
    }
  };

  /* Status always carries a word plus an icon, never colour alone. */
  const getStatusBadge = (status: StageStatus) => {
    switch (status) {
      case 'mastered':
        return { icon: CheckCircle, label: 'Mastered', cls: 'bg-green-100 text-green-800 border-green-200' };
      case 'taught':
        return { icon: CheckCircle2, label: 'Taught', cls: 'bg-green-100 text-green-800 border-green-200' };
      case 'in_progress':
        return { icon: Zap, label: 'In progress', cls: 'bg-amber-100 text-amber-800 border-amber-200' };
      case 'available':
        return { icon: PlayCircle, label: 'Ready to teach', cls: 'bg-[var(--accent-green-light)] text-[var(--accent-green-text)] border-[var(--accent-green)]' };
      case 'blocked':
      case 'needs_review':
        return { icon: AlertTriangle, label: 'Needs review', cls: 'bg-red-100 text-red-800 border-red-200' };
      default:
        return { icon: Lock, label: 'Locked', cls: 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] border-[var(--border)]' };
    }
  };

  const fieldClass =
    'w-full rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-3 text-sm font-medium text-[var(--text-primary)] focus:border-[var(--accent-royal)] focus:ring-1 focus:ring-[var(--accent-royal)] focus:outline-none transition-colors';

  return (
    <AppLayout title="Lesson Planner">
      <SEO 
        title="AI Lesson Planner" 
        description="Generate comprehensive lesson roadmaps." 
      />
      <div className="flex h-full w-full">
        <HistorySidebar
          title="Roadmaps"
          items={historyItems}
          selectedId={roadmap?.id || null}
          onSelect={loadRoadmap}
          onNew={() => { setRoadmap(null); setSearchParams(prev => { prev.delete('id'); return prev; }); }}
          collapsed={historySidebarCollapsed}
          onToggle={toggleHistorySidebar}
        />
        
        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 md:py-8">
          <div className="mx-auto max-w-5xl space-y-6">

        {/* Header */}
        <div className="flex flex-col justify-between gap-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5 md:flex-row md:items-center">
          <div className="flex items-center gap-3.5">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-green-light)]">
              <Compass className="h-5 w-5 text-[var(--accent-green-text)]" aria-hidden="true" />
            </span>
            <div>
              <h2 className="font-display text-xl font-bold tracking-tight text-[var(--text-primary)]">
                Adaptive lesson roadmap
              </h2>
              <p className="mt-0.5 text-sm text-[var(--text-secondary)]">
                Sequences your topic by prerequisite, budgets time per stage, and generates the
                teaching resources for each one.
              </p>
            </div>
          </div>

          {roadmap && (
            <div className="flex shrink-0 items-center gap-2">
              <button
                type="button"
                onClick={handleGenerateStudyPack}
                disabled={isTriggeringResource === 'studypack'}
                className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-2 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)] disabled:opacity-50"
              >
                {isTriggeringResource === 'studypack' ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Download className="h-4 w-4" aria-hidden="true" />
                )}
                Generate study pack
              </button>
              <button
                type="button"
                onClick={handlePublish}
                className="flex items-center gap-2 rounded-full bg-[var(--accent-royal)] px-4 py-2 text-sm font-bold text-white shadow-sm shadow-[var(--accent-royal)]/25 transition-all hover:bg-[var(--accent-green-deep)] active:translate-y-px"
              >
                {roadmap.status === 'published' ? (
                  <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Share2 className="h-4 w-4" aria-hidden="true" />
                )}
                {roadmap.status === 'published' ? 'Published' : 'Publish roadmap'}
              </button>
            </div>
          )}
        </div>

        {/* Notifications */}
        <AnimatePresence>
          {actionNotification && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              aria-live="polite"
              className="flex items-center justify-between rounded-xl border border-[var(--accent-green)] bg-[var(--accent-green-light)] px-4 py-3 text-sm text-[var(--accent-green-text)]"
            >
              <span>{actionNotification}</span>
              <button
                type="button"
                onClick={() => setActionNotification(null)}
                aria-label="Dismiss message"
                className="ml-4 rounded p-0.5 hover:bg-white/60"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </motion.div>
          )}
          {errorNotification && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              role="alert"
              className="flex items-center justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
            >
              <span className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
                {errorNotification}
              </span>
              <button
                type="button"
                onClick={() => setErrorNotification(null)}
                aria-label="Dismiss error"
                className="ml-4 rounded p-0.5 hover:bg-red-100"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {!roadmap ? (
          /* ============================================================ */
          /* 1. INTAKE                                                    */
          /* ============================================================ */
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            <div className="space-y-5 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5 md:p-6 lg:col-span-8">
              <div>
                <h3 className="font-display text-lg font-semibold text-[var(--text-primary)]">
                  What are you teaching?
                </h3>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">
                  Describe your topic, audience, and constraints in plain language.
                </p>
              </div>

              <div>
                <label htmlFor="planner-prompt" className="sr-only">Lesson description</label>
                <textarea
                  id="planner-prompt"
                  rows={4}
                  value={promptInput}
                  onChange={(e) => handlePromptChange(e.target.value)}
                  placeholder="I need to teach database normalization to B.Tech students in 60 minutes. I have to cover Armstrong's axioms and worked examples for 1NF, 2NF, and 3NF."
                  className="w-full rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] p-5 text-base text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-royal)] focus:outline-none focus:ring-1 focus:ring-[var(--accent-royal)] transition-all"
                />
              </div>

              <fieldset>
                <legend className="mb-3 block text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                  Grounding sources
                </legend>
                <div className="flex flex-wrap gap-2.5">
                  {['Topic', 'Syllabus', 'My Material', 'Past Papers', 'YouTube'].map(src => {
                    const isSel = selectedSources.includes(src);
                    return (
                      <button
                        key={src}
                        type="button"
                        onClick={() => handleSourceToggle(src)}
                        aria-pressed={isSel}
                        className={`flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-bold transition-all ${
                          isSel
                            ? 'border-[var(--accent-royal)] bg-[var(--accent-baby)]/20 text-[var(--accent-royal)] shadow-sm ring-1 ring-[var(--accent-royal)]'
                            : 'border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:border-[var(--accent-royal)] hover:text-[var(--accent-royal)] hover:shadow-sm'
                        }`}
                      >
                        {isSel ? (
                          <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                        ) : (
                          <Plus className="h-4 w-4" aria-hidden="true" />
                        )}
                        {src}
                      </button>
                    );
                  })}
                </div>
              </fieldset>

              {/* Parsed configuration */}
              <div className="space-y-4 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5">
                <div className="flex items-center justify-between gap-3">
                  <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                    <Sparkles className="h-4 w-4 text-[var(--accent-royal)]" aria-hidden="true" />
                    Lesson configuration
                  </h4>
                  <span className="text-xs text-[var(--text-secondary)]">Review and adjust</span>
                </div>

                <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 md:grid-cols-3">
                  <div>
                    <label htmlFor="cfg-topic" className="mb-1 block text-xs text-[var(--text-secondary)]">
                      Target topic
                    </label>
                    <input
                      id="cfg-topic"
                      type="text"
                      value={parsedConfig.topic}
                      onChange={(e) => setParsedConfig({ ...parsedConfig, topic: e.target.value })}
                      className={fieldClass}
                    />
                  </div>

                  <div>
                    <label htmlFor="cfg-level" className="mb-1 block text-xs text-[var(--text-secondary)]">
                      Audience level
                    </label>
                    <select
                      id="cfg-level"
                      value={parsedConfig.level}
                      onChange={(e) => setParsedConfig({ ...parsedConfig, level: e.target.value })}
                      className={fieldClass}
                    >
                      <option value="B.Tech">B.Tech / Engineering</option>
                      <option value="Undergraduate">Undergraduate (B.Sc / BCA)</option>
                      <option value="High School">High School (Grade 11-12)</option>
                      <option value="Introductory">Beginner / Introductory</option>
                    </select>
                  </div>

                  <div>
                    <label htmlFor="cfg-format" className="mb-1 block text-xs text-[var(--text-secondary)]">
                      Class format
                    </label>
                    <select
                      id="cfg-format"
                      value={parsedConfig.class_type}
                      onChange={(e) => setParsedConfig({ ...parsedConfig, class_type: e.target.value })}
                      className={fieldClass}
                    >
                      <option value="Interactive Lecture">Interactive Lecture</option>
                      <option value="Lab">Lab / Coding Mode</option>
                      <option value="Tutorial">Tutorial / Problem Solving</option>
                      <option value="Revision">Revision and Exam Prep</option>
                      <option value="Flipped Classroom">Flipped Classroom</option>
                    </select>
                  </div>

                  <div>
                    <label htmlFor="cfg-duration" className="mb-1 block text-xs text-[var(--text-secondary)]">
                      Duration
                    </label>
                    <select
                      id="cfg-duration"
                      value={parsedConfig.duration_minutes}
                      onChange={(e) => setParsedConfig({ ...parsedConfig, duration_minutes: parseInt(e.target.value) })}
                      className={fieldClass}
                    >
                      <option value={15}>15 min (micro lesson)</option>
                      <option value={30}>30 min (express)</option>
                      <option value={45}>45 min (standard class)</option>
                      <option value={60}>60 min (full lecture)</option>
                      <option value={90}>90 min (extended workshop)</option>
                    </select>
                  </div>

                  <div>
                    <label htmlFor="cfg-language" className="mb-1 block text-xs text-[var(--text-secondary)]">
                      Language
                    </label>
                    <select
                      id="cfg-language"
                      value={parsedConfig.language}
                      onChange={(e) => setParsedConfig({ ...parsedConfig, language: e.target.value })}
                      className={fieldClass}
                    >
                      <option value="english">English</option>
                      <option value="hindi">Hindi</option>
                      <option value="hinglish">Hinglish</option>
                    </select>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={generateRoadmap}
                disabled={isGenerating || !parsedConfig.topic.trim()}
                className="flex w-full items-center justify-center gap-3 rounded-full bg-[var(--accent-royal)] px-6 py-4 text-base font-bold text-white shadow-md shadow-[var(--accent-royal)]/25 transition-all hover:bg-[var(--accent-green-deep)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isGenerating ? (
                  <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                ) : (
                  <Sparkles className="h-5 w-5" aria-hidden="true" />
                )}
                {isGenerating ? 'Building your roadmap' : 'Generate lesson roadmap'}
              </button>
            </div>

            {/* Sidebar */}
            <div className="lg:col-span-4">
              <div className="space-y-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
                <h3 className="flex items-center gap-2 font-display text-base font-semibold text-[var(--text-primary)]">
                  <Compass className="h-4 w-4 text-[var(--accent-green-text)]" aria-hidden="true" />
                  How it works
                </h3>
                <ol className="space-y-3 text-sm text-[var(--text-secondary)]">
                  {[
                    { t: 'Concept graph', d: 'Analyses topic dependencies and builds an ordered concept map.' },
                    { t: 'Stage sequencing', d: 'Creates stages aligned to Bloom levels, with time budgets and checkpoints.' },
                    { t: 'Resources', d: 'Recommends and generates stage-specific decks, videos, quizzes and notes.' },
                  ].map((step, i) => (
                    <li key={step.t} className="flex gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--accent-green-light)] text-xs font-bold tabular-nums text-[var(--accent-green-text)]">
                        {i + 1}
                      </span>
                      <p>
                        <strong className="font-semibold text-[var(--text-primary)]">{step.t}.</strong>{' '}
                        {step.d}
                      </p>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>
        ) : (
          /* ============================================================ */
          /* 2. ROADMAP CANVAS                                            */
          /* ============================================================ */
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">

            {/* Left: roadmap track */}
            <div className="space-y-4 lg:col-span-4">
              <div className="space-y-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">

                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="rounded-full bg-[var(--accent-green-light)] px-2.5 py-0.5 text-xs font-semibold text-[var(--accent-green-text)]">
                      {roadmap.class_type}
                    </span>
                    <span className="text-xs tabular-nums text-[var(--text-muted)]">
                      v{roadmap.version}
                    </span>
                  </div>
                  <h3 className="mt-2 font-display text-lg font-bold text-[var(--text-primary)]">
                    {roadmap.topic}
                  </h3>
                  <p className="mt-1 flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                    <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                    <span className="tabular-nums">{roadmap.target_duration_minutes}</span> min total,{' '}
                    {roadmap.level}
                  </p>
                </div>

                <div>
                  <div className="mb-1.5 flex items-center justify-between text-xs font-medium text-[var(--text-secondary)]">
                    <span>Course progress</span>
                    <span className="tabular-nums">{roadmap.overall_progress}%</span>
                  </div>
                  <div
                    className="h-2 w-full overflow-hidden rounded-full bg-[var(--bg-secondary)]"
                    role="progressbar"
                    aria-valuenow={roadmap.overall_progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label="Course progress"
                  >
                    <div
                      className="h-full rounded-full bg-[var(--accent-green)] transition-all duration-500"
                      style={{ width: `${roadmap.overall_progress}%` }}
                    />
                  </div>
                </div>

                <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                    Next action
                  </span>
                  <span className="text-xs font-semibold text-[var(--text-primary)]">
                    {roadmap.next_best_action}
                  </span>
                </div>
              </div>

              {/* Stage list */}
              <ol className="space-y-2.5">
                {roadmap.stages.map((stage, idx) => {
                  const isSelected = selectedStage?.id === stage.id;
                  const badge = getStatusBadge(stage.status);
                  const BadgeIcon = badge.icon;

                  return (
                    <li key={stage.id}>
                      <button
                        type="button"
                        onClick={() => handleStageSelect(stage)}
                        aria-current={isSelected ? 'true' : undefined}
                        className={`flex w-full items-start gap-3.5 rounded-xl border p-4 text-left transition-colors ${
                          isSelected
                            ? 'border-[var(--accent-green)] bg-[var(--accent-green-light)]'
                            : 'border-[var(--border)] bg-[var(--bg-card)] hover:bg-[var(--bg-hover)]'
                        }`}
                      >
                        <span className="mt-0.5 flex shrink-0 flex-col items-center gap-1">
                          <span className="text-xs font-bold tabular-nums text-[var(--text-secondary)]">
                            {idx + 1}
                          </span>
                          <BadgeIcon
                            className="h-4 w-4 text-[var(--text-secondary)]"
                            aria-hidden="true"
                          />
                        </span>

                        <span className="min-w-0 flex-1">
                          <span className="flex items-center justify-between gap-2">
                            <span className="truncate text-sm font-semibold text-[var(--text-primary)]">
                              {stage.is_remedial && (
                                <span className="mr-1 font-bold text-[var(--accent-green-text)]">
                                  Recap:
                                </span>
                              )}
                              {stage.title}
                            </span>
                            <span className="shrink-0 text-xs font-medium tabular-nums text-[var(--text-secondary)]">
                              {stage.duration_minutes}m
                            </span>
                          </span>

                          <span className="mt-1 line-clamp-1 block text-xs text-[var(--text-secondary)]">
                            {stage.description}
                          </span>

                          <span className="mt-2 flex items-center gap-2">
                            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${badge.cls}`}>
                              {badge.label}
                            </span>
                            {stage.objectives.length > 0 && (
                              <span className="rounded border border-[var(--border)] bg-[var(--bg-secondary)] px-1.5 py-0.5 text-[10px] text-[var(--text-secondary)]">
                                {stage.objectives[0].bloom_level}
                              </span>
                            )}
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ol>

              {/* Health */}
              {healthScore && (
                <div className="space-y-2 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
                      Lesson health
                    </span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-bold tabular-nums ${
                      healthScore.score >= 85
                        ? 'bg-green-100 text-green-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}>
                      {healthScore.score}/100
                    </span>
                  </div>
                  {healthScore.reasons?.length > 0 && (
                    <p className="flex items-start gap-1.5 text-xs text-[var(--text-secondary)]">
                      <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--accent-green-text)]" aria-hidden="true" />
                      {healthScore.reasons[0]}
                    </p>
                  )}
                  {healthScore.warnings?.length > 0 && (
                    <p className="flex items-start gap-1.5 text-xs text-amber-800">
                      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                      {healthScore.warnings[0]}
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Right: stage detail */}
            {selectedStage && (
              <div className="space-y-5 lg:col-span-8">

                <div className="space-y-5 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5 md:p-6">
                  <div className="flex flex-col justify-between gap-4 border-b border-[var(--border)] pb-5 sm:flex-row sm:items-center">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="rounded-full bg-[var(--accent-green-light)] px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider text-[var(--accent-green-text)]">
                          Stage {roadmap.stages.indexOf(selectedStage) + 1}
                        </span>
                        <span className="text-xs font-medium tabular-nums text-[var(--text-secondary)]">
                          {selectedStage.duration_minutes} minutes
                        </span>
                      </div>
                      <h3 className="mt-2 font-display text-2xl font-bold text-[var(--text-primary)]">
                        {selectedStage.title}
                      </h3>
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleMarkTaught(selectedStage)}
                        aria-pressed={selectedStage.status === 'taught'}
                        className={`flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold transition-colors ${
                          selectedStage.status === 'taught'
                            ? 'bg-[var(--accent-green)] text-white'
                            : 'border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)]'
                        }`}
                      >
                        <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                        {selectedStage.status === 'taught' ? 'Marked taught' : 'Mark as taught'}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleCreateRemedial(selectedStage)}
                        className="flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-3 py-2 text-xs font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
                      >
                        <Plus className="h-4 w-4" aria-hidden="true" />
                        Add recap stage
                      </button>

                      <button
                        type="button"
                        onClick={() => setIsEditingStage(!isEditingStage)}
                        aria-label="Edit stage"
                        aria-expanded={isEditingStage}
                        className="rounded-xl p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                      >
                        <PenTool className="h-4 w-4" aria-hidden="true" />
                      </button>
                    </div>
                  </div>

                  {/* Inline editor */}
                  {isEditingStage ? (
                    <div className="space-y-4 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
                        Edit stage
                      </h4>
                      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <div>
                          <label htmlFor="edit-title" className="mb-1 block text-xs text-[var(--text-secondary)]">
                            Title
                          </label>
                          <input
                            id="edit-title"
                            type="text"
                            value={editForm.title}
                            onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                            className={fieldClass}
                          />
                        </div>
                        <div>
                          <label htmlFor="edit-duration" className="mb-1 block text-xs text-[var(--text-secondary)]">
                            Duration (minutes)
                          </label>
                          <input
                            id="edit-duration"
                            type="number"
                            value={editForm.duration_minutes}
                            onChange={(e) => setEditForm({ ...editForm, duration_minutes: parseInt(e.target.value) || 5 })}
                            className={fieldClass}
                          />
                        </div>
                        <div className="sm:col-span-2">
                          <label htmlFor="edit-teacher" className="mb-1 block text-xs text-[var(--text-secondary)]">
                            Teacher action
                          </label>
                          <input
                            id="edit-teacher"
                            type="text"
                            value={editForm.teacher_action}
                            onChange={(e) => setEditForm({ ...editForm, teacher_action: e.target.value })}
                            className={fieldClass}
                          />
                        </div>
                      </div>
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setIsEditingStage(false)}
                          className="rounded-lg px-3 py-1.5 text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={handleSaveStageEdit}
                          className="rounded-lg bg-[var(--accent-green)] px-4 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)]"
                        >
                          Save stage
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                      {selectedStage.description}
                    </p>
                  )}

                  {/* Tabs */}
                  <div role="tablist" aria-label="Stage details" className="flex border-b border-[var(--border)]">
                    {[
                      { id: 'details', label: 'Pedagogy' },
                      { id: 'timeline', label: 'Timeline' },
                      { id: 'differentiation', label: 'Differentiation' }
                    ].map(tab => (
                      <button
                        key={tab.id}
                        type="button"
                        role="tab"
                        aria-selected={activeTab === tab.id}
                        onClick={() => setActiveTab(tab.id as any)}
                        className={`border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
                          activeTab === tab.id
                            ? 'border-[var(--accent-green)] text-[var(--accent-green-text)]'
                            : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  {/* Tab: details */}
                  {activeTab === 'details' && (
                    <div className="space-y-5" role="tabpanel">
                      <div>
                        <h4 className="mb-2.5 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                          <ListChecks className="h-4 w-4 text-[var(--accent-green-text)]" aria-hidden="true" />
                          Learning objectives
                        </h4>
                        <ul className="space-y-2">
                          {selectedStage.objectives.map((obj, i) => (
                            <li
                              key={i}
                              className="flex items-start gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3 text-sm"
                            >
                              <span className="shrink-0 rounded bg-[var(--accent-green-light)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[var(--accent-green-text)]">
                                {obj.bloom_level}
                              </span>
                              <span className="text-[var(--text-primary)]">{obj.description}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <div className="space-y-2 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                          <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
                            Teacher actions
                          </h4>
                          <ul className="list-disc space-y-1.5 pl-4 text-xs text-[var(--text-secondary)]">
                            {selectedStage.teacher_actions.map((act, i) => (
                              <li key={i}>{act}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="space-y-2 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                          <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
                            Student actions
                          </h4>
                          <ul className="list-disc space-y-1.5 pl-4 text-xs text-[var(--text-secondary)]">
                            {selectedStage.student_actions.map((act, i) => (
                              <li key={i}>{act}</li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <div className="space-y-2 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                          <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
                            <HelpCircle className="h-4 w-4 text-[var(--accent-green-text)]" aria-hidden="true" />
                            Checkpoint questions
                          </h4>
                          <ul className="list-disc space-y-1.5 pl-4 text-xs text-[var(--text-secondary)]">
                            {selectedStage.checkpoint_questions.map((q, i) => (
                              <li key={i}>{q}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="space-y-2 rounded-xl border border-amber-200 bg-amber-50 p-4">
                          <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-amber-900">
                            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                            Common misconceptions
                          </h4>
                          <ul className="list-disc space-y-1.5 pl-4 text-xs text-amber-900">
                            {selectedStage.expected_misconceptions.map((m, i) => (
                              <li key={i}>{m}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Tab: timeline */}
                  {activeTab === 'timeline' && (
                    <ul className="space-y-2.5" role="tabpanel">
                      {selectedStage.activities.map((act, i) => (
                        <li
                          key={i}
                          className="flex items-center gap-4 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3.5"
                        >
                          <span className="w-12 shrink-0 rounded border border-[var(--border)] bg-[var(--bg-card)] px-2 py-1 text-center text-xs font-bold tabular-nums text-[var(--accent-green-text)]">
                            {act.duration_minutes}m
                          </span>
                          <span className="flex-1">
                            <span className="block text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                              {act.type}
                            </span>
                            <span className="mt-0.5 block text-xs text-[var(--text-primary)]">
                              {act.description}
                            </span>
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {/* Tab: differentiation */}
                  {activeTab === 'differentiation' && (
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3" role="tabpanel">
                      {[
                        { title: 'Core', body: selectedStage.differentiation.core || 'Standard lesson delivery and baseline problem set.' },
                        { title: 'Support', body: selectedStage.differentiation.support || 'Visual colour-coding and step-by-step hint cards.' },
                        { title: 'Extension', body: selectedStage.differentiation.extension || 'Edge-case synthesis and optimisation problem.' },
                      ].map((tier) => (
                        <div
                          key={tier.title}
                          className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4"
                        >
                          <h4 className="mb-1 block text-xs font-bold text-[var(--text-primary)]">
                            {tier.title}
                          </h4>
                          <p className="text-xs text-[var(--text-secondary)]">{tier.body}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Resource generation */}
                <div className="space-y-4 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5 md:p-6">
                  <div>
                    <h3 className="font-display text-lg font-semibold text-[var(--text-primary)]">
                      Stage resources
                    </h3>
                    <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                      Generated from this stage's objectives, timings and checkpoints.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
                    {RESOURCE_CARDS.map((card) => {
                      /* Badge reflects the backend's recommendation for this
                         stage. Previously these labels were hardcoded. */
                      const rec = selectedStage.resource_recommendations?.find(
                        r => r.resource_type === card.key
                      );
                      const badgeLabel = rec ? RESOURCE_STATUS_LABELS[rec.status] : undefined;
                      const Icon = card.icon;

                      return (
                        <div
                          key={card.type}
                          className="flex flex-col justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4"
                        >
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between gap-2">
                              <span className="flex items-center gap-1 rounded bg-[var(--bg-card)] px-2 py-0.5 text-xs font-bold text-[var(--text-primary)]">
                                <Icon className="h-3.5 w-3.5 text-[var(--accent-green-text)]" aria-hidden="true" />
                                {card.label}
                              </span>
                              {badgeLabel && (
                                <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                                  rec?.status === 'recommended'
                                    ? 'bg-[var(--accent-green-light)] text-[var(--accent-green-text)]'
                                    : 'bg-[var(--bg-card)] text-[var(--text-secondary)]'
                                }`}>
                                  {badgeLabel}
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-[var(--text-secondary)]">{card.desc}</p>
                            {rec?.reason && (
                              <p className="text-[11px] italic text-[var(--text-muted)]">{rec.reason}</p>
                            )}
                          </div>
                          <button
                            type="button"
                            onClick={() => handleGenerateResource(card.type)}
                            disabled={isTriggeringResource === card.type}
                            className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-[var(--accent-green)] py-2 text-xs font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)] disabled:opacity-50"
                          >
                            {isTriggeringResource === card.type ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                            ) : (
                              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                            )}
                            {card.cta}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>

              </div>
            )}
          </div>
        )}

          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default LessonPlannerPage;
