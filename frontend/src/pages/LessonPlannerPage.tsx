import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles, Clock, CheckCircle2, PlayCircle, BookOpen,
  Presentation, HelpCircle, ListChecks, PenTool,
  Loader2, AlertTriangle, Lock, Unlock, CheckCircle, Zap,
  Plus, Share2, Download, Compass, X, Video, GraduationCap,
  ExternalLink, FileText, ThumbsUp, ThumbsDown, Shield,
  RefreshCw, Layers, Award, Target, Info, ArrowRight, Check,
  BookMarked, BrainCircuit, Activity
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import HistorySidebar from '../components/HistorySidebar';
import { useSidebarCollapse } from '../hooks/useSidebarCollapse';
import SEO from '../components/SEO';
import { ILLUSTRATIONS } from '../lib/assets';
import { useAuthStore } from '../store/useAuthStore';

// Types mapping to Backend schemas
type StageStatus = 'locked' | 'available' | 'in_progress' | 'material_ready' | 'taught' | 'assessment_pending' | 'mastered' | 'needs_review' | 'blocked';
type StageReadiness = 'ready' | 'prerequisite_required' | 'review_recommended' | 'blocked';
type ResourceType = 'ppt' | 'video' | 'teach_me' | 'quiz' | 'notes' | 'worksheet' | 'homework' | 'diagram' | 'youtube_recommendations' | 'extra_learning_materials';
type ResourceStatus = 'not_needed' | 'recommended' | 'optional' | 'selected' | 'generating' | 'ready' | 'failed' | 'stale' | 'coming_soon' | 'disabled';
export type ProductMode = 'teacher_classroom' | 'student_self_study' | 'research_advanced';

export interface ResourceScoreBreakdown {
  concept_match: number;
  level_fit: number;
  authority: number;
  freshness: number;
  evidence_quality: number;
  accessibility: number;
}

export interface UniversalResourceCard {
  id: string;
  title: string;
  type: string; // video_segment, paper, coding_problem, docs, textbook
  why_recommended: string;
  what_it_covers: string;
  learner_level: string;
  use_during: string;
  exact_section?: string;
  timestamp_start?: string;
  timestamp_end?: string;
  time_required_minutes?: number;
  source_authority: string;
  quality_score: number; // 0 to 100
  score_breakdown?: ResourceScoreBreakdown;
  year?: number;
  access_type: string;
  url: string;
  is_preprint?: boolean;
  has_retraction_notice?: boolean;
  venue_label?: string;
  confidence?: number;
}

export interface PlanRecompileDiff {
  reason: string;
  evidence_summary: string;
  stages_added: any[];
  stages_modified: any[];
  stages_compressed: any[];
  net_duration_change: number;
  requires_teacher_approval: boolean;
}

export interface TeacherLockItem {
  stage_id?: string;
  lock_type: string;
  target_identifier: string;
  is_locked: boolean;
  notes?: string;
}

export interface ExplainabilityStageReport {
  stage_id: string;
  title: string;
  archetype: string;
  duration: number;
  why_this_stage: string;
  why_now: string;
  teaching_goal: string;
  bloom_level: string;
  is_locked: boolean;
}

export interface ExplainabilityReport {
  plan_id: string;
  mode: string;
  domain: string;
  intent: string;
  volatility: string;
  total_duration: number;
  adaptive_reserve: number;
  stages: ExplainabilityStageReport[];
}

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

interface StageAction {
  type: string;
  enabled: boolean;
  status: string;
  title: string;
  description: string;
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
  actions?: StageAction[];
  source_refs: SourceReference[];
  is_remedial?: boolean;
  // VNext fields
  archetype?: string;
  why_this_stage?: string;
  why_now?: string;
  teaching_goal?: string;
  pedagogy_method?: string;
  visual_requirements?: string[];
  assessment_requirement?: string;
  is_locked?: boolean;
  universal_resources?: UniversalResourceCard[];
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
  // VNext fields
  mode?: ProductMode;
  domain?: string;
  intent?: string;
  volatility?: string;
  adaptive_reserve_minutes?: number;
  teacher_locks?: TeacherLockItem[];
}

interface YouTubeVideoItem {
  title: string;
  channel: string;
  thumbnail?: string;
  duration?: string;
  url: string;
  relevance: number;
  difficulty: string;
  source: string;
  reason?: string;
}

interface ExtraLearningMaterialItem {
  title: string;
  url: string;
  description: string;
  source: string;
  type: string;
  relevance: number;
  difficulty: string;
}

interface ExtraMaterialsCategories {
  academic_references: ExtraLearningMaterialItem[];
  research_papers: ExtraLearningMaterialItem[];
  documentation: ExtraLearningMaterialItem[];
  extra_learning_material: ExtraLearningMaterialItem[];
}

/** Active downstream capabilities in Lesson Planner. */
const RESOURCE_CARDS: {
  type: string;
  key: ResourceType;
  icon: React.ElementType;
  label: string;
  desc: string;
  cta: string;
}[] = [
  { type: 'PPT', key: 'ppt', icon: Presentation, label: 'PowerPoint', desc: 'Multi-slide deck with concept diagrams and speaker notes.', cta: 'Create PPT deck' },
  { type: 'Teach', key: 'teach_me', icon: BookOpen, label: 'Teach Me', desc: 'Interactive dialogue with live checkpoints.', cta: 'Launch Teach Me' },
  { type: 'Quiz', key: 'quiz', icon: HelpCircle, label: 'Quiz', desc: 'Diagnostic questions addressing common misconceptions.', cta: 'Create quiz' },
  { type: 'YouTube', key: 'youtube_recommendations', icon: Video, label: 'YouTube Lectures', desc: 'Live curated video lectures and worked tutorials for this stage.', cta: 'Explore Videos' },
  { type: 'Materials', key: 'extra_learning_materials', icon: GraduationCap, label: 'Learning Hub', desc: 'Live academic references, arXiv papers, and documentation.', cta: 'Browse Hub' },
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
  coming_soon: 'Coming Soon',
  disabled: 'Disabled',
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

interface HistoryItem {
  id: string;
  title: string;
  date: string;
  topic?: string;
  created_at?: string;
}

interface LessonHealthReport {
  score: number;
  reasons: string[];
  warnings: string[];
  recommended_fixes: { type: string; label: string }[];
}

  // Roadmap & Stage States
  const [roadmap, setRoadmap] = useState<LearningRoadmap | null>(null);
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'details' | 'timeline' | 'differentiation'>('details');
  const [healthScore, setHealthScore] = useState<LessonHealthReport | null>(null);
  const [isEditingStage, setIsEditingStage] = useState(false);
  const [editForm, setEditForm] = useState({ title: '', duration_minutes: 15, teacher_action: '', student_action: '' });
  const [actionNotification, setActionNotification] = useState<string | null>(null);
  /* Separate from actionNotification so a failure is never styled or worded
     as a success. Previously some failures reported success. */
  const [errorNotification, setErrorNotification] = useState<string | null>(null);
  const [isTriggeringResource, setIsTriggeringResource] = useState<string | null>(null);
  
  // Product Mode & Adaptive States
  const [selectedMode, setSelectedMode] = useState<ProductMode>('teacher_classroom');
  const [adaptationAlert, setAdaptationAlert] = useState<PlanRecompileDiff | null>(null);
  const [isRecompiling, setIsRecompiling] = useState(false);
  const [isSimulatingEvidence, setIsSimulatingEvidence] = useState(false);
  
  // Explainability Modal
  const [explainModalOpen, setExplainModalOpen] = useState(false);
  const [explainReport, setExplainReport] = useState<ExplainabilityReport | null>(null);
  const [isExplainLoading, setIsExplainLoading] = useState(false);
  
  // Universal Resources Modal
  const [universalModalOpen, setUniversalModalOpen] = useState(false);
  const [universalResourcesList, setUniversalResourcesList] = useState<UniversalResourceCard[]>([]);
  const [universalFilter, setUniversalFilter] = useState<'all' | 'video_segment' | 'paper' | 'coding_problem' | 'docs'>('all');
  const [isUniversalLoading, setIsUniversalLoading] = useState(false);

  // Modal states for live viewers
  const [activeViewer, setActiveViewer] = useState<'youtube' | 'materials' | null>(null);
  const [youtubeData, setYoutubeData] = useState<YouTubeVideoItem[] | null>(null);
  const [materialsData, setMaterialsData] = useState<ExtraMaterialsCategories | null>(null);
  const [materialsTab, setMaterialsTab] = useState<'academic_references' | 'research_papers' | 'documentation' | 'extra_learning_material'>('academic_references');
  const [isViewerLoading, setIsViewerLoading] = useState(false);

  const formatArchetype = (archetype?: string) => {
    if (!archetype) return 'Explanation';
    return archetype
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  };

  const getArchetypeBadgeClass = (archetype?: string) => {
    switch (archetype) {
      case 'hook_and_anchor':
        return 'bg-amber-100 text-amber-900 border-amber-300';
      case 'worked_example_fading':
      case 'worked_example':
        return 'bg-blue-100 text-blue-900 border-blue-300';
      case 'guided_practice_peer_check':
      case 'guided_practice':
        return 'bg-emerald-100 text-emerald-900 border-emerald-300';
      case 'socratic_dialogue':
        return 'bg-purple-100 text-purple-900 border-purple-300';
      case 'contrastive_analogy':
        return 'bg-rose-100 text-rose-900 border-rose-300';
      case 'formative_exit_ticket':
      case 'diagnostic_check':
        return 'bg-orange-100 text-orange-900 border-orange-300';
      case 'remediation':
        return 'bg-red-100 text-red-900 border-red-300';
      default:
        return 'bg-[var(--accent-baby)]/30 text-[var(--accent-royal)] border-[var(--border)]';
    }
  };

  const handleToggleStageLock = async (stage: RoadmapStage) => {
    if (!roadmap) return;
    const newLockStatus = !stage.is_locked;
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/v2/${roadmap.id}/locks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        },
        body: JSON.stringify({
          stage_id: stage.id,
          lock_type: 'stage',
          target_identifier: stage.id,
          is_locked: newLockStatus,
          notes: newLockStatus ? 'Teacher locked' : 'Teacher unlocked'
        })
      });
      if (res.ok) {
        setRoadmap(prev => {
          if (!prev) return null;
          return {
            ...prev,
            stages: prev.stages.map(s => s.id === stage.id ? { ...s, is_locked: newLockStatus } : s)
          };
        });
        setActionNotification(newLockStatus ? `Stage "${stage.title}" locked. It will not be altered during adaptive recompilation.` : `Stage "${stage.title}" unlocked.`);
      } else {
        setErrorNotification('Failed to toggle stage lock.');
      }
    } catch (err) {
      console.error('Failed to toggle lock', err);
      setErrorNotification('Failed to toggle stage lock.');
    }
  };

  const handleSimulateEvidence = async (misconceptionCandidate = "Primary Key vs Candidate Key confusion") => {
    if (!roadmap || !selectedStage) return;
    setIsSimulatingEvidence(true);
    setErrorNotification(null);
    try {
      // 1. Ingest formative diagnostic evidence
      await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/v2/${roadmap.id}/evidence`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        },
        body: JSON.stringify({
          student_id: 'student_batch_simulated',
          concept_id: selectedStage.concept_id || selectedStage.id,
          source_type: 'checkpoint',
          correctness: false,
          misconception_candidate: misconceptionCandidate,
          confidence: 0.88
        })
      });

      // 2. Request adaptive recompile diff with 20% threshold
      const recompileRes = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/v2/${roadmap.id}/recompile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        },
        body: JSON.stringify({
          threshold: 0.20,
          teacher_decision: (roadmap.mode || selectedMode) === 'student_self_study' ? 'accept' : undefined
        })
      });

      if (recompileRes.ok) {
        const data = await recompileRes.json();
        if (data.recompiled) {
          if ((roadmap.mode || selectedMode) === 'student_self_study') {
            setRoadmap(prev => prev ? { ...prev, stages: data.stages } : null);
            setActionNotification('Self-study adaptive repair automatically inserted into roadmap!');
          } else {
            setAdaptationAlert(data.diff);
            setActionNotification('Formative misconception detected (>20% threshold). Review adaptive recommendation below.');
          }
        } else {
          setActionNotification('Formative checkpoint recorded. Error rate is below adaptive threshold.');
        }
      }
    } catch (err) {
      console.error('Evidence simulation failed', err);
      setErrorNotification('Could not simulate diagnostic evidence.');
    } finally {
      setIsSimulatingEvidence(false);
    }
  };

  const handleAcceptAdaptation = async () => {
    if (!roadmap) return;
    setIsRecompiling(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/v2/${roadmap.id}/recompile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        },
        body: JSON.stringify({
          threshold: 0.20,
          teacher_decision: 'accept'
        })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.stages) {
          setRoadmap(prev => prev ? { ...prev, stages: data.stages } : null);
          setAdaptationAlert(null);
          setActionNotification('Adaptive plan approved! Remediation inserted and recap compressed successfully.');
        }
      } else {
        setErrorNotification('Could not accept adaptation.');
      }
    } catch (err) {
      console.error('Failed to accept adaptation', err);
      setErrorNotification('Could not accept adaptation.');
    } finally {
      setIsRecompiling(false);
    }
  };

  const handleDismissAdaptation = () => {
    setAdaptationAlert(null);
    setActionNotification('Adaptive intervention dismissed. Current plan preserved.');
  };

  const handleFetchWhyReport = async () => {
    if (!roadmap) return;
    setExplainModalOpen(true);
    setIsExplainLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/v2/${roadmap.id}/why`, {
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setExplainReport(data);
      }
    } catch (err) {
      console.error('Failed to fetch why report', err);
    } finally {
      setIsExplainLoading(false);
    }
  };

  const openUniversalResourcesModal = async (stage: RoadmapStage) => {
    if (!roadmap) return;
    setUniversalModalOpen(true);
    setIsUniversalLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/v2/${roadmap.id}/stages/${stage.id}/resources`, {
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setUniversalResourcesList(data.resources || []);
      } else if (stage.universal_resources && stage.universal_resources.length > 0) {
        setUniversalResourcesList(stage.universal_resources);
      }
    } catch (e) {
      console.error('Failed to fetch universal resources', e);
      if (stage.universal_resources) setUniversalResourcesList(stage.universal_resources);
    } finally {
      setIsUniversalLoading(false);
    }
  };

  const handleResourceFeedback = async (resourceId: string, helpful: boolean) => {
    if (!roadmap || !selectedStage) return;
    try {
      await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/v2/${roadmap.id}/resource-feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}`
        },
        body: JSON.stringify({
          resource_id: resourceId,
          stage_id: selectedStage.id,
          helpful,
          feedback: helpful ? 'High relevance to lesson stage' : 'Irrelevant or misaligned'
        })
      });
      setActionNotification(helpful ? 'Resource feedback saved (Trust Boosted).' : 'Resource feedback saved (De-emphasized).');
    } catch (e) {
      console.error('Resource feedback failed', e);
    }
  };

  const openYouTubeViewer = async (stage: RoadmapStage) => {
    if (!roadmap) return;
    setActiveViewer('youtube');
    setIsViewerLoading(true);
    setErrorNotification(null);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/stages/${stage.id}/youtube-recommendations`, {
        headers: { 'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setYoutubeData(data.items || []);
      } else {
        setErrorNotification('Could not load YouTube recommendations. Please try again.');
      }
    } catch (e) {
      console.error(e);
      setErrorNotification('Could not load YouTube recommendations.');
    } finally {
      setIsViewerLoading(false);
    }
  };

  const openMaterialsViewer = async (stage: RoadmapStage) => {
    if (!roadmap) return;
    setActiveViewer('materials');
    setIsViewerLoading(true);
    setErrorNotification(null);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/stages/${stage.id}/learning-materials`, {
        headers: { 'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMaterialsData(data.categories || null);
      } else {
        setErrorNotification('Could not load extra learning materials. Please try again.');
      }
    } catch (e) {
      console.error(e);
      setErrorNotification('Could not load extra learning materials.');
    } finally {
      setIsViewerLoading(false);
    }
  };
  
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);

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

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/`, {
          headers: { 'Authorization': `Bearer ${useAuthStore.getState().session?.access_token}` }
        });
        if (res.ok) {
          const data = await res.json();
          const items: HistoryItem[] = (data.roadmaps || []).map((r: any) => ({
            id: r.id,
            title: r.topic || r.title || 'Untitled Roadmap',
            date: r.created_at || r.date || new Date().toISOString(),
            topic: r.topic,
            created_at: r.created_at
          }));
          setHistoryItems(items);
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
    setAdaptationAlert(null);
    try {
      let data: LearningRoadmap;
      try {
        const v2Response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/v2/plan`, {
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
            mode: selectedMode,
            custom_context: `Sources used: ${selectedSources.join(', ')}. Goal: ${parsedConfig.goal}`
          })
        });
        if (v2Response.ok) {
          data = await v2Response.json();
        } else {
          throw new Error("V2 fallback");
        }
      } catch {
        // Safe backward-compatible fallback to V1
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
        data = await response.json();
      }

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

    if (type === 'YouTube') {
      openYouTubeViewer(selectedStage);
      return;
    }
    if (type === 'Materials') {
      openMaterialsViewer(selectedStage);
      return;
    }

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
        } else if (type === 'Teach') {
          navigate('/teach', { state: { presetBrief: data.brief } });
        } else if (type === 'Quiz') {
          navigate('/quizzes', { state: { presetConfig: data.config } });
        }
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
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="font-display text-xl font-bold tracking-tight text-[var(--text-primary)]">
                  Adaptive lesson roadmap
                </h2>
                {roadmap && (
                  <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold tracking-wide uppercase border ${
                    (roadmap.mode || selectedMode) === 'teacher_classroom'
                      ? 'bg-blue-50 text-blue-800 border-blue-200'
                      : (roadmap.mode || selectedMode) === 'student_self_study'
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : 'bg-purple-50 text-purple-800 border-purple-200'
                  }`}>
                    {(roadmap.mode || selectedMode) === 'teacher_classroom' && <Shield className="h-3 w-3" />}
                    {(roadmap.mode || selectedMode) === 'student_self_study' && <Sparkles className="h-3 w-3" />}
                    {(roadmap.mode || selectedMode) === 'research_advanced' && <GraduationCap className="h-3 w-3" />}
                    {(roadmap.mode || selectedMode).replace(/_/g, ' ')}
                  </span>
                )}
                {roadmap?.adaptive_reserve_minutes ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-semibold text-amber-900">
                    <Clock className="h-3 w-3" />
                    Adaptive reserve: {roadmap.adaptive_reserve_minutes}m
                  </span>
                ) : null}
              </div>
              <p className="mt-0.5 text-sm text-[var(--text-secondary)]">
                Evidence-Adaptive Teaching Operating System. Autonomous pedagogy, time-budget scaffolding, and live diagnostic adaptation.
              </p>
            </div>
          </div>

          {roadmap && (
            <div className="flex shrink-0 items-center gap-2 flex-wrap">
              <button
                type="button"
                onClick={handleFetchWhyReport}
                className="flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-xs font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
              >
                <Info className="h-4 w-4 text-[var(--accent-royal)]" aria-hidden="true" />
                Why this plan?
              </button>
              {selectedStage && (
                <button
                  type="button"
                  onClick={() => openUniversalResourcesModal(selectedStage)}
                  className="flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-2 text-xs font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
                >
                  <Layers className="h-4 w-4 text-[var(--accent-royal)]" aria-hidden="true" />
                  Universal resources
                </button>
              )}
              <button
                type="button"
                onClick={handleGenerateStudyPack}
                disabled={isTriggeringResource === 'studypack'}
                className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--bg-card)] px-4 py-2 text-xs font-semibold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)] disabled:opacity-50"
              >
                {isTriggeringResource === 'studypack' ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                ) : (
                  <Download className="h-3.5 w-3.5" aria-hidden="true" />
                )}
                Study pack
              </button>
              <button
                type="button"
                onClick={handlePublish}
                className="flex items-center gap-2 rounded-full bg-[var(--accent-royal)] px-3.5 py-2 text-xs font-bold text-white shadow-sm shadow-[var(--accent-royal)]/25 transition-all hover:bg-[var(--accent-green-deep)] active:translate-y-px"
              >
                {roadmap.status === 'published' ? (
                  <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                ) : (
                  <Share2 className="h-3.5 w-3.5" aria-hidden="true" />
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

              {/* Product Mode Selector */}
              <fieldset>
                <legend className="mb-2.5 block text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                  Operating Mode
                </legend>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    {
                      id: 'teacher_classroom',
                      title: 'Teacher Classroom',
                      icon: Shield,
                      badge: 'Teacher-in-Control',
                      desc: 'Active checkpoints & teacher locks. Recompilations require 1-click approval.'
                    },
                    {
                      id: 'student_self_study',
                      title: 'Student Self-Study',
                      icon: Sparkles,
                      badge: 'Autonomous Repair',
                      desc: 'Self-paced confidence building. Automatically detects and fixes prerequisite gaps.'
                    },
                    {
                      id: 'research_advanced',
                      title: 'Research / Advanced',
                      icon: GraduationCap,
                      badge: 'Q1-Q4 & A*/A Papers',
                      desc: 'Deep scholarly literature, arXiv papers, journal quartile rankings, and proofs.'
                    }
                  ].map((mode) => {
                    const isSelected = selectedMode === mode.id;
                    const ModeIcon = mode.icon;
                    return (
                      <button
                        key={mode.id}
                        type="button"
                        onClick={() => setSelectedMode(mode.id as ProductMode)}
                        className={`flex flex-col justify-between text-left p-3.5 rounded-xl border transition-all ${
                          isSelected
                            ? 'border-[var(--accent-royal)] bg-[var(--accent-baby)]/15 shadow-sm ring-1 ring-[var(--accent-royal)]'
                            : 'border-[var(--border)] bg-[var(--bg-card)] hover:border-[var(--accent-royal)]/40 hover:bg-[var(--bg-hover)]'
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="flex items-center gap-1.5 text-xs font-bold text-[var(--text-primary)]">
                              <ModeIcon className={`h-4 w-4 ${isSelected ? 'text-[var(--accent-royal)]' : 'text-[var(--text-secondary)]'}`} />
                              {mode.title}
                            </span>
                            {isSelected && (
                              <CheckCircle2 className="h-4 w-4 text-[var(--accent-royal)]" />
                            )}
                          </div>
                          <span className="inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[var(--bg-secondary)] text-[var(--text-secondary)] mb-1.5">
                            {mode.badge}
                          </span>
                          <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                            {mode.desc}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </fieldset>

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
                <img
                  src={ILLUSTRATIONS.lessonPlan}
                  alt=""
                  aria-hidden="true"
                  className="h-28 w-full rounded-lg object-cover"
                  onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                />
                <h3 className="flex items-center gap-2 font-display text-base font-semibold text-[var(--text-primary)]">
                  <Compass className="h-4 w-4 text-[var(--accent-green-text)]" aria-hidden="true" />
                  How it works
                </h3>
                <ol className="space-y-3 text-sm text-[var(--text-secondary)]">
                  {[
                    { t: 'Concept graph', d: 'Analyses topic dependencies and builds an ordered concept map.' },
                    { t: 'Stage sequencing', d: 'Creates stages aligned to Bloom levels, with time budgets and checkpoints.' },
                    { t: 'Resources', d: 'Recommends and generates stage-specific decks, interactive Socratic sessions, and quizzes.' },
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
          <div className="space-y-6">
            {/* Adaptation Alert Banner */}
            <AnimatePresence>
              {adaptationAlert && (
                <motion.div
                  initial={{ opacity: 0, y: -12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  className="rounded-2xl border-2 border-amber-400 bg-gradient-to-r from-amber-500/10 via-rose-500/5 to-purple-500/10 p-5 shadow-lg backdrop-blur-md"
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1.5 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500 text-white font-bold shadow-sm">
                          <Zap className="h-4 w-4" />
                        </span>
                        <h4 className="font-display text-base font-bold text-[var(--text-primary)]">
                          Evidence-Adaptive Intervention Triggered
                        </h4>
                        <span className="rounded-full bg-amber-100 text-amber-900 border border-amber-300 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                          &gt;20% Misconception Threshold
                        </span>
                      </div>
                      <p className="text-sm text-[var(--text-secondary)]">
                        <strong className="text-[var(--text-primary)]">Diagnosis:</strong> {adaptationAlert.reason || adaptationAlert.evidence_summary || 'Diagnostic failure detected on prerequisite concept.'}
                      </p>

                      {/* Before / After Diff Breakdown */}
                      <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-2 border-t border-amber-200/60">
                        <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-2.5">
                          <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">
                            + Added Remediation
                          </span>
                          <span className="text-xs font-semibold text-emerald-900 line-clamp-1">
                            {adaptationAlert.stages_added?.[0]?.title || 'Targeted Prerequisite Repair'}
                          </span>
                          <span className="text-[11px] font-medium text-emerald-700">
                            +{adaptationAlert.stages_added?.[0]?.duration_minutes || 5} mins
                          </span>
                        </div>

                        <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-2.5">
                          <span className="text-[10px] font-bold text-amber-800 uppercase tracking-wider block">
                            - Compressed Stage
                          </span>
                          <span className="text-xs font-semibold text-amber-900 line-clamp-1">
                            {adaptationAlert.stages_compressed?.[0]?.stage_id ? 'Review & Recap Stage' : 'Recap Stage Compressed'}
                          </span>
                          <span className="text-[11px] font-medium text-amber-700">
                            -{adaptationAlert.stages_compressed?.[0]?.reduction_minutes || 3} mins
                          </span>
                        </div>

                        <div className="rounded-xl border border-purple-200 bg-purple-50/80 p-2.5">
                          <span className="text-[10px] font-bold text-purple-800 uppercase tracking-wider block">
                            Net Duration Impact
                          </span>
                          <span className="text-xs font-semibold text-purple-900">
                            {adaptationAlert.net_duration_change >= 0 ? `+${adaptationAlert.net_duration_change}` : adaptationAlert.net_duration_change} min net
                          </span>
                          <span className="text-[11px] font-medium text-purple-700">
                            Absorbed by {roadmap.adaptive_reserve_minutes || 10}m Reserve
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Teacher Action Controls */}
                    <div className="flex md:flex-col shrink-0 gap-2 justify-end">
                      <button
                        type="button"
                        onClick={handleAcceptAdaptation}
                        disabled={isRecompiling}
                        className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-[var(--accent-royal)] px-4 py-2.5 text-xs font-bold text-white shadow-md hover:bg-[var(--accent-green-deep)] transition-all disabled:opacity-50"
                      >
                        {isRecompiling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                        Accept Adaptation
                      </button>
                      <button
                        type="button"
                        onClick={handleDismissAdaptation}
                        className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-[var(--border)] bg-white px-4 py-2 text-xs font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition-all"
                      >
                        <X className="h-3.5 w-3.5" />
                        Keep Current Plan
                      </button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

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
                  const archetypeClass = getArchetypeBadgeClass(stage.archetype);

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
                            <span className="truncate text-sm font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
                              {stage.is_locked && (
                                <span title="Locked by teacher"><Lock className="h-3 w-3 text-amber-600 shrink-0" /></span>
                              )}
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

                          <span className="mt-2 flex items-center gap-1.5 flex-wrap">
                            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${badge.cls}`}>
                              {badge.label}
                            </span>
                            {stage.archetype && (
                              <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${archetypeClass}`}>
                                {formatArchetype(stage.archetype)}
                              </span>
                            )}
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
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="rounded-full bg-[var(--accent-green-light)] px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider text-[var(--accent-green-text)]">
                          Stage {roadmap.stages.indexOf(selectedStage) + 1}
                        </span>
                        {selectedStage.archetype && (
                          <span className={`rounded-full border px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider ${getArchetypeBadgeClass(selectedStage.archetype)}`}>
                            {formatArchetype(selectedStage.archetype)}
                          </span>
                        )}
                        <span className="text-xs font-medium tabular-nums text-[var(--text-secondary)]">
                          {selectedStage.duration_minutes} minutes
                        </span>
                      </div>
                      <h3 className="mt-2 font-display text-2xl font-bold text-[var(--text-primary)]">
                        {selectedStage.title}
                      </h3>
                    </div>

                    <div className="flex shrink-0 items-center gap-2 flex-wrap">
                      <button
                        type="button"
                        onClick={() => handleToggleStageLock(selectedStage)}
                        aria-pressed={selectedStage.is_locked}
                        className={`flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold transition-colors ${
                          selectedStage.is_locked
                            ? 'bg-amber-100 text-amber-900 border border-amber-300'
                            : 'border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
                        }`}
                        title={selectedStage.is_locked ? 'Unlock stage' : 'Lock stage to protect against adaptive changes'}
                      >
                        {selectedStage.is_locked ? (
                          <>
                            <Lock className="h-4 w-4 text-amber-700" aria-hidden="true" />
                            Locked
                          </>
                        ) : (
                          <>
                            <Unlock className="h-4 w-4" aria-hidden="true" />
                            Lock stage
                          </>
                        )}
                      </button>

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
                        Add recap
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

                  {/* Why Now / Pedagogical Scaffolding Callout */}
                  {(selectedStage.why_now || selectedStage.why_this_stage) && (
                    <div className="flex items-start gap-3 rounded-xl border border-blue-200/80 bg-gradient-to-r from-blue-50/70 to-indigo-50/70 p-4">
                      <div className="rounded-lg bg-blue-100 p-2 text-blue-700 shrink-0 mt-0.5">
                        <BrainCircuit className="h-4 w-4" />
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold uppercase tracking-wider text-blue-900">
                            Pedagogical Sequence: Why Now?
                          </span>
                          {selectedStage.pedagogy_method && (
                            <span className="rounded bg-blue-200/60 px-2 py-0.5 text-[10px] font-semibold text-blue-800">
                              {selectedStage.pedagogy_method}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-blue-950 leading-relaxed">
                          {selectedStage.why_now || selectedStage.why_this_stage}
                        </p>
                      </div>
                    </div>
                  )}

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
                        onClick={() => setActiveTab(tab.id as 'details' | 'timeline' | 'differentiation')}
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
                        <div className="space-y-3 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4">
                          <div className="flex items-center justify-between gap-2 flex-wrap">
                            <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
                              <HelpCircle className="h-4 w-4 text-[var(--accent-green-text)]" aria-hidden="true" />
                              Checkpoint questions
                            </h4>
                            <button
                              type="button"
                              onClick={() => handleSimulateEvidence("Primary Key vs Candidate Key confusion")}
                              disabled={isSimulatingEvidence}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-amber-50 px-2 py-1 text-[10px] font-bold text-amber-900 hover:bg-amber-100 transition-colors disabled:opacity-50"
                              title="Simulate class evidence with >20% error rate on candidate keys"
                            >
                              {isSimulatingEvidence ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                <Activity className="h-3 w-3 text-amber-600" />
                              )}
                              Simulate Checkpoint Diagnostic
                            </button>
                          </div>
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
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div>
                      <h3 className="font-display text-lg font-semibold text-[var(--text-primary)]">
                        Stage resources
                      </h3>
                      <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                        Generated from this stage's objectives, timings and checkpoints.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => openUniversalResourcesModal(selectedStage)}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] px-3 py-1.5 text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
                    >
                      <Layers className="h-3.5 w-3.5 text-[var(--accent-royal)]" />
                      Browse Universal Resources Hub
                    </button>
                  </div>

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
                    {RESOURCE_CARDS.map((card) => {
                      /* Badge reflects the backend's recommendation for this
                         stage. */
                      const rec = selectedStage.resource_recommendations?.find(
                        r => r.resource_type === card.key
                      );
                      const badgeLabel = rec ? RESOURCE_STATUS_LABELS[rec.status] : undefined;
                      const Icon = card.icon;

                      return (
                        <div
                          key={card.type}
                          className="flex flex-col justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4 transition-all hover:border-[var(--accent-green)]/30"
                        >
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between gap-2">
                              <span className="flex items-center gap-1.5 rounded bg-[var(--bg-card)] px-2 py-0.5 text-xs font-bold text-[var(--text-primary)]">
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
        </div>
      )}

          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* LIVE VIEWER MODALS: YOUTUBE & LEARNING MATERIALS HUB          */}
      {/* ============================================================ */}
      <AnimatePresence>
        {activeViewer === 'youtube' && selectedStage && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] shadow-2xl overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-100 text-red-600">
                    <Video className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div>
                    <h3 className="font-display text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
                      YouTube Recommendations
                      <span className="rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 uppercase tracking-wider">
                        Live
                      </span>
                    </h3>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Curated educational lectures for stage: <span className="font-semibold text-[var(--text-primary)]">"{selectedStage.title}"</span>
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveViewer(null)}
                  aria-label="Close modal"
                  className="rounded-lg p-2 text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition-colors"
                >
                  <X className="h-5 w-5" aria-hidden="true" />
                </button>
              </div>

              {/* Content Body */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {isViewerLoading ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center space-y-3">
                    <Loader2 className="h-8 w-8 animate-spin text-[var(--accent-green)]" />
                    <p className="text-sm font-medium text-[var(--text-primary)]">
                      Searching and ranking educational video lectures...
                    </p>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Matching pedagogical depth to {selectedStage.title}
                    </p>
                  </div>
                ) : youtubeData && youtubeData.length > 0 ? (
                  <div className="space-y-4">
                    {youtubeData.map((item, idx) => (
                      <div
                        key={idx}
                        className="flex flex-col sm:flex-row gap-4 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4 transition-all hover:border-[var(--accent-green)]/40 hover:shadow-sm"
                      >
                        {/* Thumbnail / Duration */}
                        <div className="relative shrink-0 w-full sm:w-44 h-28 rounded-lg overflow-hidden bg-black/10">
                          {item.thumbnail ? (
                            <img
                              src={item.thumbnail}
                              alt={item.title}
                              className="h-full w-full object-cover"
                            />
                          ) : (
                            <div className="flex h-full w-full items-center justify-center bg-gray-900 text-white">
                              <Video className="h-8 w-8 text-red-500" />
                            </div>
                          )}
                          {item.duration && (
                            <span className="absolute bottom-2 right-2 rounded bg-black/80 px-1.5 py-0.5 text-[10px] font-bold text-white tracking-wider">
                              {item.duration}
                            </span>
                          )}
                        </div>

                        {/* Info */}
                        <div className="flex-1 flex flex-col justify-between space-y-2">
                          <div>
                            <div className="flex items-center gap-2 flex-wrap mb-1">
                              <span className="rounded bg-[var(--bg-card)] px-2 py-0.5 text-[11px] font-semibold text-[var(--text-secondary)]">
                                {item.channel}
                              </span>
                              <span className="rounded bg-emerald-50 text-emerald-700 text-[10px] font-bold px-2 py-0.5">
                                {Math.round(item.relevance * 100)}% Match
                              </span>
                              <span className="rounded bg-blue-50 text-blue-700 text-[10px] font-bold px-2 py-0.5 capitalize">
                                {item.difficulty}
                              </span>
                            </div>
                            <h4 className="font-semibold text-sm text-[var(--text-primary)] line-clamp-2">
                              {item.title}
                            </h4>
                            {item.reason && (
                              <p className="mt-1 text-xs text-[var(--text-secondary)] line-clamp-2">
                                {item.reason}
                              </p>
                            )}
                          </div>

                          <div>
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition-all hover:bg-red-700"
                            >
                              <PlayCircle className="h-3.5 w-3.5" aria-hidden="true" />
                              Watch on YouTube
                              <ExternalLink className="h-3 w-3 ml-0.5" aria-hidden="true" />
                            </a>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-12 text-center text-sm text-[var(--text-secondary)]">
                    No educational videos available for this specific stage.
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="border-t border-[var(--border)] px-6 py-3.5 bg-[var(--bg-secondary)] flex justify-between items-center text-xs text-[var(--text-secondary)]">
                <span>Educational recommendations are ranked by topic alignment.</span>
                <button
                  type="button"
                  onClick={() => openYouTubeViewer(selectedStage)}
                  className="font-semibold text-[var(--accent-green-text)] hover:underline"
                >
                  Refresh search
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {activeViewer === 'materials' && selectedStage && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] shadow-2xl overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-100 text-purple-600">
                    <GraduationCap className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div>
                    <h3 className="font-display text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
                      Extra Learning Materials Hub
                      <span className="rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 uppercase tracking-wider">
                        Live
                      </span>
                    </h3>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Academic references & research papers for <span className="font-semibold text-[var(--text-primary)]">"{selectedStage.title}"</span>
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveViewer(null)}
                  aria-label="Close modal"
                  className="rounded-lg p-2 text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition-colors"
                >
                  <X className="h-5 w-5" aria-hidden="true" />
                </button>
              </div>

              {/* Category Tabs */}
              <div className="flex border-b border-[var(--border)] bg-[var(--bg-secondary)] px-6 overflow-x-auto">
                {[
                  { id: 'academic_references', label: 'Academic References', icon: BookOpen, count: materialsData?.academic_references?.length || 0 },
                  { id: 'research_papers', label: 'Research Papers (arXiv)', icon: FileText, count: materialsData?.research_papers?.length || 0 },
                  { id: 'documentation', label: 'Documentation', icon: ListChecks, count: materialsData?.documentation?.length || 0 },
                  { id: 'extra_learning_material', label: 'Extra Material & Guides', icon: Sparkles, count: materialsData?.extra_learning_material?.length || 0 }
                ].map(tab => {
                  const TabIcon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setMaterialsTab(tab.id as any)}
                      className={`flex items-center gap-2 border-b-2 px-4 py-3 text-xs font-semibold whitespace-nowrap transition-colors ${
                        materialsTab === tab.id
                          ? 'border-[var(--accent-green)] text-[var(--accent-green-text)]'
                          : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                      }`}
                    >
                      <TabIcon className="h-3.5 w-3.5" aria-hidden="true" />
                      {tab.label}
                      <span className="ml-1 rounded-full bg-[var(--bg-card)] px-1.5 py-0.5 text-[10px] font-bold text-[var(--text-secondary)]">
                        {tab.count}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Content Body */}
              <div className="flex-1 overflow-y-auto p-6 space-y-3">
                {isViewerLoading ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center space-y-3">
                    <Loader2 className="h-8 w-8 animate-spin text-[var(--accent-green)]" />
                    <p className="text-sm font-medium text-[var(--text-primary)]">
                      Fetching verified academic references and research papers...
                    </p>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Connecting to Wikipedia, arXiv, and official documentation
                    </p>
                  </div>
                ) : (materialsData && materialsData[materialsTab]?.length > 0) ? (
                  <div className="space-y-3">
                    {materialsData[materialsTab].map((item, idx) => (
                      <div
                        key={idx}
                        className="flex flex-col justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4 transition-all hover:border-[var(--accent-green)]/40 hover:shadow-sm"
                      >
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between gap-2">
                            <span className="rounded bg-[var(--bg-card)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                              {item.source}
                            </span>
                            <span className="rounded bg-blue-50 text-blue-700 px-2 py-0.5 text-[10px] font-bold capitalize">
                              {item.difficulty}
                            </span>
                          </div>
                          <h4 className="font-semibold text-sm text-[var(--text-primary)]">
                            {item.title}
                          </h4>
                          <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                            {item.description}
                          </p>
                        </div>

                        <div className="pt-1">
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--bg-card)] px-3 py-1.5 text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
                          >
                            Open Resource
                            <ExternalLink className="h-3 w-3 ml-0.5 text-[var(--text-secondary)]" aria-hidden="true" />
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-12 text-center text-sm text-[var(--text-secondary)]">
                    No materials found in this category for this stage.
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="border-t border-[var(--border)] px-6 py-3.5 bg-[var(--bg-secondary)] flex justify-between items-center text-xs text-[var(--text-secondary)]">
                <span>Sourced from Wikipedia, arXiv, and developer documentation.</span>
                <button
                  type="button"
                  onClick={() => openMaterialsViewer(selectedStage)}
                  className="font-semibold text-[var(--accent-green-text)] hover:underline"
                >
                  Refresh search
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {/* ============================================================ */}
        {/* EXPLAINABILITY MODAL: WHY THIS PLAN?                         */}
        {/* ============================================================ */}
        {explainModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="relative flex max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] shadow-2xl overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4 bg-gradient-to-r from-blue-50/60 to-purple-50/60">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent-royal)] text-white shadow-sm">
                    <BrainCircuit className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div>
                    <h3 className="font-display text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
                      Pedagogical Rationale: Why This Plan?
                      <span className="rounded-full bg-blue-100 text-blue-800 text-[10px] font-bold px-2 py-0.5 uppercase tracking-wider">
                        Deterministic OS
                      </span>
                    </h3>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Scaffolding, Bloom progression, and cognitive load audit.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setExplainModalOpen(false)}
                  aria-label="Close modal"
                  className="rounded-lg p-2 text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition-colors"
                >
                  <X className="h-5 w-5" aria-hidden="true" />
                </button>
              </div>

              {/* Body */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {isExplainLoading ? (
                  <div className="flex flex-col items-center justify-center py-16 space-y-3">
                    <Loader2 className="h-8 w-8 animate-spin text-[var(--accent-royal)]" />
                    <p className="text-sm font-medium text-[var(--text-primary)]">
                      Synthesizing explainability audit...
                    </p>
                  </div>
                ) : explainReport ? (
                  <div className="space-y-6">
                    {/* Meta stats */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] block mb-1">
                          Canonical Domain
                        </span>
                        <span className="text-xs font-bold text-[var(--text-primary)] capitalize">
                          {explainReport.domain?.replace(/_/g, ' ') || 'General Academic'}
                        </span>
                      </div>
                      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] block mb-1">
                          Teaching Intent
                        </span>
                        <span className="text-xs font-bold text-[var(--text-primary)] capitalize">
                          {explainReport.intent?.replace(/_/g, ' ') || 'Teach'}
                        </span>
                      </div>
                      <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-3.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] block mb-1">
                          Topic Volatility
                        </span>
                        <span className="text-xs font-bold text-[var(--text-primary)] capitalize">
                          {explainReport.volatility || 'Low'}
                        </span>
                      </div>
                      <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-3.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 block mb-1">
                          Adaptive Reserve
                        </span>
                        <span className="text-xs font-bold text-amber-900">
                          {explainReport.adaptive_reserve || 10} minutes
                        </span>
                      </div>
                    </div>

                    {/* Stage Breakdown Table */}
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)] flex items-center gap-1.5">
                        <ListChecks className="h-4 w-4 text-[var(--accent-royal)]" />
                        Stage Sequencing Justification
                      </h4>

                      <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="border-b border-[var(--border)] bg-[var(--bg-secondary)] text-[var(--text-secondary)] font-bold">
                              <th className="p-3 w-12 text-center">#</th>
                              <th className="p-3">Stage &amp; Archetype</th>
                              <th className="p-3 w-20">Duration</th>
                              <th className="p-3">Why This Stage?</th>
                              <th className="p-3">Why Now?</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[var(--border)]">
                            {explainReport.stages?.map((st, idx) => (
                              <tr key={st.stage_id} className="hover:bg-[var(--bg-secondary)]/50 transition-colors">
                                <td className="p-3 font-bold text-center text-[var(--text-secondary)]">
                                  {idx + 1}
                                </td>
                                <td className="p-3 font-medium">
                                  <div className="flex items-center gap-1.5">
                                    {st.is_locked && <Lock className="h-3 w-3 text-amber-600 shrink-0" />}
                                    <span className="text-[var(--text-primary)] font-semibold">{st.title}</span>
                                  </div>
                                  <span className={`inline-block mt-1 text-[10px] font-bold uppercase tracking-wider rounded-full px-2 py-0.5 border ${getArchetypeBadgeClass(st.archetype)}`}>
                                    {formatArchetype(st.archetype)}
                                  </span>
                                </td>
                                <td className="p-3 font-semibold tabular-nums text-[var(--text-secondary)]">
                                  {st.duration}m
                                </td>
                                <td className="p-3 text-[var(--text-secondary)] leading-relaxed">
                                  {st.why_this_stage || st.teaching_goal || 'Builds core conceptual competency.'}
                                </td>
                                <td className="p-3 text-[var(--text-secondary)] leading-relaxed">
                                  {st.why_now || 'Sequenced following prerequisite readiness.'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="py-12 text-center text-sm text-[var(--text-secondary)]">
                    No explainability data available for this roadmap.
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="border-t border-[var(--border)] px-6 py-3.5 bg-[var(--bg-secondary)] flex justify-between items-center text-xs text-[var(--text-secondary)]">
                <span>Deterministic explanation generated from curriculum graph &amp; Bloom taxonomy.</span>
                <button
                  type="button"
                  onClick={() => setExplainModalOpen(false)}
                  className="rounded-lg bg-[var(--accent-royal)] text-white px-4 py-1.5 text-xs font-bold hover:bg-[var(--accent-green-deep)] transition-all"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {/* ============================================================ */}
        {/* UNIVERSAL RESOURCES HUB MODAL                                */}
        {/* ============================================================ */}
        {universalModalOpen && selectedStage && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="relative flex max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl border border-[var(--border)] bg-[var(--bg-card)] shadow-2xl overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4 bg-gradient-to-r from-emerald-50/60 to-blue-50/60">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm">
                    <Layers className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div>
                    <h3 className="font-display text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
                      Universal Resources Hub
                      <span className="rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 uppercase tracking-wider">
                        Verified
                      </span>
                    </h3>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Precision-targeted video segments, Q1-Q4 papers, and official documentation for <span className="font-semibold text-[var(--text-primary)]">"{selectedStage.title}"</span>
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setUniversalModalOpen(false)}
                  aria-label="Close modal"
                  className="rounded-lg p-2 text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] transition-colors"
                >
                  <X className="h-5 w-5" aria-hidden="true" />
                </button>
              </div>

              {/* Filter Tabs */}
              <div className="flex border-b border-[var(--border)] bg-[var(--bg-secondary)] px-6 overflow-x-auto gap-2 py-2.5">
                {[
                  { id: 'all', label: 'All Resources' },
                  { id: 'video_segment', label: 'Timestamped Videos' },
                  { id: 'paper', label: 'Academic Papers (Q1-Q4)' },
                  { id: 'coding_problem', label: 'Coding Progression' },
                  { id: 'docs', label: 'Official Docs' }
                ].map(tab => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setUniversalFilter(tab.id as any)}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-all ${
                      universalFilter === tab.id
                        ? 'bg-[var(--accent-royal)] text-white shadow-sm'
                        : 'bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Content List */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {isUniversalLoading ? (
                  <div className="flex flex-col items-center justify-center py-16 space-y-3">
                    <Loader2 className="h-8 w-8 animate-spin text-[var(--accent-royal)]" />
                    <p className="text-sm font-medium text-[var(--text-primary)]">
                      Retrieving verified universal resource cards...
                    </p>
                  </div>
                ) : universalResourcesList && universalResourcesList.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {universalResourcesList
                      .filter(r => universalFilter === 'all' || r.type === universalFilter)
                      .map((res) => (
                        <div
                          key={res.id}
                          className="flex flex-col justify-between rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-4 hover:border-[var(--accent-royal)]/40 hover:shadow-sm transition-all"
                        >
                          <div className="space-y-2">
                            <div className="flex items-center justify-between gap-2 flex-wrap">
                              <span className="rounded bg-[var(--bg-card)] border border-[var(--border)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[var(--accent-royal)]">
                                {res.type.replace(/_/g, ' ')}
                              </span>
                              <div className="flex items-center gap-1.5">
                                {res.timestamp_start && res.timestamp_end && (
                                  <span className="rounded bg-rose-50 text-rose-800 border border-rose-200 px-1.5 py-0.5 text-[10px] font-mono font-bold">
                                    ⏱️ {res.timestamp_start}–{res.timestamp_end}
                                  </span>
                                )}
                                {res.venue_label && (
                                  <span className="rounded bg-purple-100 text-purple-900 border border-purple-300 px-1.5 py-0.5 text-[10px] font-bold">
                                    {res.venue_label}
                                  </span>
                                )}
                                <span className="rounded bg-emerald-100 text-emerald-900 px-1.5 py-0.5 text-[10px] font-bold">
                                  {res.quality_score}/100
                                </span>
                              </div>
                            </div>

                            <h4 className="text-sm font-bold text-[var(--text-primary)] line-clamp-2">
                              {res.title}
                            </h4>

                            <p className="text-xs text-[var(--text-secondary)] line-clamp-2 leading-relaxed">
                              {res.what_it_covers || res.why_recommended}
                            </p>

                            <div className="flex items-center gap-2 text-[11px] text-[var(--text-muted)]">
                              <span>Source: {res.source_authority}</span>
                              {res.use_during && (
                                <>
                                  <span>•</span>
                                  <span className="capitalize">Use during: {res.use_during.replace(/_/g, ' ')}</span>
                                </>
                              )}
                            </div>
                          </div>

                          <div className="mt-3 pt-3 border-t border-[var(--border)] flex items-center justify-between">
                            <a
                              href={res.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-xs font-bold text-[var(--accent-royal)] hover:underline"
                            >
                              Open Resource
                              <ExternalLink className="h-3 w-3" />
                            </a>

                            {/* Trust Feedback buttons */}
                            <div className="flex items-center gap-1">
                              <button
                                type="button"
                                onClick={() => handleResourceFeedback(res.id, true)}
                                title="Resource was helpful"
                                className="rounded p-1.5 hover:bg-emerald-100 text-emerald-700 transition-colors"
                              >
                                <ThumbsUp className="h-3.5 w-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleResourceFeedback(res.id, false)}
                                title="Resource was not helpful"
                                className="rounded p-1.5 hover:bg-red-100 text-red-700 transition-colors"
                              >
                                <ThumbsDown className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                ) : (
                  <div className="py-12 text-center text-sm text-[var(--text-secondary)]">
                    No universal resource cards found for this category.
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="border-t border-[var(--border)] px-6 py-3.5 bg-[var(--bg-secondary)] flex justify-between items-center text-xs text-[var(--text-secondary)]">
                <span>Verified deterministic resources. No hallucinatory or simulated links.</span>
                <button
                  type="button"
                  onClick={() => openUniversalResourcesModal(selectedStage)}
                  className="font-semibold text-[var(--accent-royal)] hover:underline"
                >
                  Refresh resources
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </AppLayout>
  );
};

export default LessonPlannerPage;
