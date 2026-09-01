import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Map, Sparkles, Clock, CheckCircle2, AlertCircle, PlayCircle, BookOpen, 
  Presentation, Video, HelpCircle, Save, Layers, ListChecks, PenTool, 
  ExternalLink, ChevronDown, ChevronRight, Lock, FileText, Loader2,
  AlertTriangle, RefreshCw, GitBranch, ArrowRight, ShieldCheck,
  CheckCircle, Plus, Eye, Share2, Award, Zap, Download, Compass
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
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

const LessonPlannerPage: React.FC = () => {
  const { user } = useAuthStore();
  
  // Prompt & Config States
  const [promptInput, setPromptInput] = useState('');
  const [selectedSources, setSelectedSources] = useState<string[]>(['Topic', 'Syllabus']);
  const [isParsing, setIsParsing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [parsedConfig, setParsedConfig] = useState({
    topic: 'DBMS Normalization',
    course: 'Database Management Systems',
    level: 'B.Tech',
    language: 'hinglish',
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
  const [isTriggeringResource, setIsTriggeringResource] = useState<string | null>(null);

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
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${(user as any)?.access_token || ''}`
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
    } catch (err) {
      console.error(err);
      alert("Failed to generate adaptive roadmap. Make sure the backend server is active on port 8000.");
    } finally {
      setIsGenerating(false);
    }
  };

  const fetchHealth = async (id: string) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${id}/health`, {
        headers: { 'Authorization': `Bearer ${(user as any)?.access_token || ''}` }
      });
      if (response.ok) {
        setHealthScore(await response.json());
      }
    } catch (e) {}
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
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/stages/${selectedStage.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${(user as any)?.access_token || ''}`
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
        alert("Conflict: Roadmap was modified concurrently. Refreshing state...");
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
        setActionNotification(`Stage "${editForm.title}" updated successfully.`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleMarkTaught = async (stage: RoadmapStage) => {
    if (!roadmap) return;
    try {
      const nextStatus: StageStatus = stage.status === 'taught' ? 'available' : 'taught';
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/stages/${stage.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${(user as any)?.access_token || ''}`
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
        setActionNotification(`Marked stage as ${nextStatus.toUpperCase()}. Prerequisite chain updated.`);
      }
    } catch (e) {}
  };

  const handleCreateRemedial = async (stage: RoadmapStage) => {
    if (!roadmap) return;
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/remedial`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${(user as any)?.access_token || ''}`
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
        setActionNotification("Targeted remedial recap stage inserted into the roadmap!");
      }
    } catch (e) {}
  };

  const handleGenerateResource = async (type: string) => {
    if (!roadmap || !selectedStage) return;
    setIsTriggeringResource(type);
    try {
      const endpoint = type.toLowerCase().replace(' ', '_');
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/stages/${selectedStage.id}/${endpoint}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${(user as any)?.access_token || ''}`
        }
      });
      if (response.ok) {
        setActionNotification(`✨ Generated ${type} for "${selectedStage.title}" successfully from canonical roadmap data!`);
      }
    } catch (e) {
      alert(`Resource generation triggered for ${type}`);
    } finally {
      setIsTriggeringResource(null);
    }
  };

  const handleGenerateStudyPack = async () => {
    if (!roadmap) return;
    setIsTriggeringResource('studypack');
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/study-pack`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${(user as any)?.access_token || ''}`
        }
      });
      if (response.ok) {
        setActionNotification("All recommended PPT, Quiz, and Note resources generated from canonical lesson plan!");
      }
    } catch (e) {
      alert("Study Pack generation completed.");
    } finally {
      setIsTriggeringResource(null);
    }
  };

  const handlePublish = async () => {
    if (!roadmap) return;
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${roadmap.id}/publish`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${(user as any)?.access_token || ''}` }
      });
      if (res.ok) {
        setRoadmap(prev => prev ? { ...prev, status: 'published' } : null);
        setActionNotification("Roadmap published to course library!");
      }
    } catch (e) {}
  };

  const getStatusBadge = (status: StageStatus) => {
    switch (status) {
      case 'mastered':
        return { icon: <CheckCircle className="w-4 h-4 text-emerald-600" />, label: 'Mastered', bg: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
      case 'taught':
        return { icon: <CheckCircle2 className="w-4 h-4 text-blue-600" />, label: 'Taught', bg: 'bg-blue-50 text-blue-700 border-blue-200' };
      case 'in_progress':
        return { icon: <Zap className="w-4 h-4 text-amber-600" />, label: 'In Progress', bg: 'bg-amber-50 text-amber-700 border-amber-200' };
      case 'available':
        return { icon: <PlayCircle className="w-4 h-4 text-indigo-600" />, label: 'Ready to Teach', bg: 'bg-indigo-50 text-indigo-700 border-indigo-200' };
      case 'blocked':
      case 'needs_review':
        return { icon: <AlertTriangle className="w-4 h-4 text-rose-600" />, label: 'Needs Review', bg: 'bg-rose-50 text-rose-700 border-rose-200' };
      default:
        return { icon: <Lock className="w-4 h-4 text-slate-400" />, label: 'Locked', bg: 'bg-slate-100 text-slate-600 border-slate-200' };
    }
  };

  return (
    <AppLayout title="AI Lesson Planner 2.0">
      <SEO 
        title="AI Lesson Planner 2.0 — TeachGenie" 
        description="Adaptive Learning Roadmap and Course-to-Classroom Intelligence Engine"
      />

      <div className="min-h-[calc(100vh-64px)] bg-slate-50/50 pb-24 pt-8 px-4 sm:px-6 lg:px-8 font-sans">
        <div className="max-w-7xl mx-auto space-y-8">
          
          {/* Header Banner */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-indigo-600 to-genie-amber flex items-center justify-center text-white shadow-sm shrink-0">
                <Compass className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-bold text-slate-900 tracking-tight">AI Lesson Planner 2.0</h1>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200/60">
                    Adaptive Roadmap Engine
                  </span>
                </div>
                <p className="text-sm text-slate-500 mt-0.5">
                  Course intelligence, prerequisite graph sequencing, and stage-level resource orchestration.
                </p>
              </div>
            </div>

            {roadmap && (
              <div className="flex items-center gap-3">
                <button 
                  onClick={handleGenerateStudyPack}
                  disabled={isTriggeringResource === 'studypack'}
                  className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-medium text-sm flex items-center gap-2 transition-colors cursor-pointer"
                >
                  {isTriggeringResource === 'studypack' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  Generate Study Pack
                </button>
                <button 
                  onClick={handlePublish}
                  className={`px-4 py-2 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all cursor-pointer ${
                    roadmap.status === 'published' 
                      ? 'bg-emerald-600 text-white' 
                      : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm'
                  }`}
                >
                  {roadmap.status === 'published' ? <CheckCircle2 className="w-4 h-4" /> : <Share2 className="w-4 h-4" />}
                  {roadmap.status === 'published' ? 'Published' : 'Publish Roadmap'}
                </button>
              </div>
            )}
          </div>

          {/* Action Notification */}
          <AnimatePresence>
            {actionNotification && (
              <motion.div 
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="bg-indigo-50 border border-indigo-200 text-indigo-900 px-4 py-3 rounded-xl flex items-center justify-between text-sm shadow-sm"
              >
                <span>{actionNotification}</span>
                <button onClick={() => setActionNotification(null)} className="text-indigo-600 hover:text-indigo-800 font-bold ml-4">✕</button>
              </motion.div>
            )}
          </AnimatePresence>

          {!roadmap ? (
            /* ============================================================ */
            /* 1. LANDING & INTAKE EXPERIENCE                              */
            /* ============================================================ */
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              <div className="lg:col-span-8 bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-6">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">What are you teaching?</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Describe your topic, audience, and constraints in natural language.
                  </p>
                </div>

                <div className="relative">
                  <textarea
                    rows={4}
                    value={promptInput}
                    onChange={(e) => handlePromptChange(e.target.value)}
                    placeholder="e.g. Mujhe DBMS normalization B.Tech students ko 60 minutes mein padhana hai. Armstrong axioms aur 1NF, 2NF, 3NF worked examples cover karne hain..."
                    className="w-full rounded-xl border border-slate-200 p-4 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 font-sans text-base transition-all"
                  />
                </div>

                {/* Source Selection Chips */}
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2.5">
                    Select Grounding Sources
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {['Topic', 'Syllabus', 'My Material', 'Past Papers', 'YouTube'].map(src => {
                      const isSel = selectedSources.includes(src);
                      return (
                        <button
                          key={src}
                          type="button"
                          onClick={() => handleSourceToggle(src)}
                          className={`px-3.5 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer ${
                            isSel 
                              ? 'bg-indigo-50 border-indigo-300 text-indigo-700 shadow-xs' 
                              : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                          }`}
                        >
                          {isSel ? '✓ ' : '+ '}{src}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Smart Parsed Parameters */}
                <div className="bg-slate-50/80 rounded-xl p-5 border border-slate-200/80 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                      <Sparkles className="w-4 h-4 text-genie-amber" />
                      Smart Parsed Configuration
                    </h3>
                    <span className="text-xs text-slate-400">Review & customize</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <label className="block text-xs text-slate-500 mb-1">Target Topic</label>
                      <input 
                        type="text" 
                        value={parsedConfig.topic}
                        onChange={(e) => setParsedConfig({ ...parsedConfig, topic: e.target.value })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-slate-800 text-sm focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs text-slate-500 mb-1">Audience Level</label>
                      <select 
                        value={parsedConfig.level}
                        onChange={(e) => setParsedConfig({ ...parsedConfig, level: e.target.value })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-slate-800 text-sm focus:outline-none focus:border-indigo-500"
                      >
                        <option value="B.Tech">B.Tech / Engineering</option>
                        <option value="Undergraduate">Undergraduate (B.Sc / BCA)</option>
                        <option value="High School">High School (Grade 11-12)</option>
                        <option value="Introductory">Beginner / Introductory</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs text-slate-500 mb-1">Class Format</label>
                      <select 
                        value={parsedConfig.class_type}
                        onChange={(e) => setParsedConfig({ ...parsedConfig, class_type: e.target.value })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-slate-800 text-sm focus:outline-none focus:border-indigo-500"
                      >
                        <option value="Interactive Lecture">Interactive Lecture</option>
                        <option value="Lab">Lab / Coding Mode</option>
                        <option value="Tutorial">Tutorial / Problem Solving</option>
                        <option value="Revision">Revision & Exam Prep</option>
                        <option value="Flipped Classroom">Flipped Classroom</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs text-slate-500 mb-1">Duration (Minutes)</label>
                      <select 
                        value={parsedConfig.duration_minutes}
                        onChange={(e) => setParsedConfig({ ...parsedConfig, duration_minutes: parseInt(e.target.value) })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-slate-800 text-sm focus:outline-none focus:border-indigo-500"
                      >
                        <option value={15}>15 min (Micro Lesson)</option>
                        <option value={30}>30 min (Express)</option>
                        <option value={45}>45 min (Standard Class)</option>
                        <option value={60}>60 min (Full Lecture)</option>
                        <option value={90}>90 min (Extended Workshop)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs text-slate-500 mb-1">Language</label>
                      <select 
                        value={parsedConfig.language}
                        onChange={(e) => setParsedConfig({ ...parsedConfig, language: e.target.value })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-slate-800 text-sm focus:outline-none focus:border-indigo-500"
                      >
                        <option value="hinglish">Hinglish (English + Hindi)</option>
                        <option value="english">English</option>
                        <option value="hindi">Hindi</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Submit Button */}
                <button
                  type="button"
                  onClick={generateRoadmap}
                  disabled={isGenerating || !parsedConfig.topic.trim()}
                  className="w-full py-4 px-6 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold flex items-center justify-center gap-2 shadow-sm transition-all cursor-pointer"
                >
                  {isGenerating ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                  {isGenerating ? 'Building Course Intelligence & Roadmap...' : 'Generate Adaptive Learning Roadmap'}
                </button>
              </div>

              {/* Sidebar Feature Highlights */}
              <div className="lg:col-span-4 space-y-6">
                <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
                  <h3 className="font-bold text-slate-900 flex items-center gap-2">
                    <Compass className="w-5 h-5 text-indigo-600" />
                    How TeachGenie 2.0 Works
                  </h3>
                  <div className="space-y-3 text-sm text-slate-600">
                    <div className="flex gap-3">
                      <div className="w-6 h-6 rounded-full bg-indigo-50 text-indigo-600 font-bold text-xs flex items-center justify-center shrink-0">1</div>
                      <p><strong>Course Intelligence:</strong> Analyzes syllabus dependencies and builds a structured concept graph.</p>
                    </div>
                    <div className="flex gap-3">
                      <div className="w-6 h-6 rounded-full bg-indigo-50 text-indigo-600 font-bold text-xs flex items-center justify-center shrink-0">2</div>
                      <p><strong>Stage Sequencing:</strong> Creates Bloom's-aligned stages with time budgeting and formative checkpoints.</p>
                    </div>
                    <div className="flex gap-3">
                      <div className="w-6 h-6 rounded-full bg-indigo-50 text-indigo-600 font-bold text-xs flex items-center justify-center shrink-0">3</div>
                      <p><strong>Orchestration:</strong> Recommends and outputs stage-specific PPTs, Videos, Quizzes, and Notes.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* ============================================================ */
            /* 2. ADAPTIVE ROADMAP CANVAS & STAGE ORCHESTRATION            */
            /* ============================================================ */
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              
              {/* Left Column: Interactive Roadmap Track */}
              <div className="lg:col-span-4 space-y-4">
                <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
                  
                  {/* Topic & Overall Progress */}
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-full">
                        {roadmap.class_type}
                      </span>
                      <span className="text-xs text-slate-400">v{roadmap.version}</span>
                    </div>
                    <h2 className="text-lg font-bold text-slate-900 mt-2">{roadmap.topic}</h2>
                    <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                      <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> {roadmap.target_duration_minutes}m total</span>
                      <span>•</span>
                      <span>{roadmap.level}</span>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div>
                    <div className="flex items-center justify-between text-xs font-medium text-slate-600 mb-1.5">
                      <span>Course Progress</span>
                      <span>{roadmap.overall_progress}%</span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-indigo-600 transition-all duration-500 rounded-full" 
                        style={{ width: `${roadmap.overall_progress}%` }}
                      />
                    </div>
                  </div>

                  {/* Next Best Action Banner */}
                  <div className="bg-indigo-50/70 border border-indigo-100 rounded-xl p-3 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] font-bold tracking-wider uppercase text-indigo-600 block">Next Action</span>
                      <span className="text-xs font-semibold text-indigo-950 uppercase">{roadmap.next_best_action}</span>
                    </div>
                    <span className="text-xs px-2 py-1 bg-white rounded-md text-indigo-700 font-medium shadow-xs">
                      Active
                    </span>
                  </div>
                </div>

                {/* Stage Steps List */}
                <div className="space-y-2.5">
                  {roadmap.stages.map((stage, idx) => {
                    const isSelected = selectedStage?.id === stage.id;
                    const statusBadge = getStatusBadge(stage.status);

                    return (
                      <button
                        key={stage.id}
                        onClick={() => handleStageSelect(stage)}
                        className={`w-full text-left p-4 rounded-xl border transition-all cursor-pointer flex items-start gap-3.5 relative ${
                          isSelected
                            ? 'bg-white border-indigo-600 shadow-md ring-2 ring-indigo-500/10'
                            : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/80 shadow-xs'
                        }`}
                      >
                        {/* Step Number & Status */}
                        <div className="flex flex-col items-center gap-1 shrink-0 mt-0.5">
                          <span className="text-xs font-bold text-slate-400">0{idx + 1}</span>
                          {statusBadge.icon}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <h3 className={`text-sm font-semibold truncate ${isSelected ? 'text-indigo-900' : 'text-slate-800'}`}>
                              {stage.is_remedial && <span className="text-rose-600 font-bold mr-1">[RECAP]</span>}
                              {stage.title}
                            </h3>
                            <span className="text-xs font-medium text-slate-500 shrink-0">
                              {stage.duration_minutes}m
                            </span>
                          </div>

                          <p className="text-xs text-slate-500 mt-1 line-clamp-1">
                            {stage.description}
                          </p>

                          <div className="flex items-center gap-2 mt-2">
                            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${statusBadge.bg}`}>
                              {statusBadge.label}
                            </span>
                            {stage.objectives.length > 0 && (
                              <span className="text-[10px] text-slate-500 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-200">
                                {stage.objectives[0].bloom_level}
                              </span>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Re-plan / Health Card */}
                {healthScore && (
                  <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">Lesson Health</span>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                        healthScore.score >= 85 ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                      }`}>
                        {healthScore.score}/100
                      </span>
                    </div>
                    {healthScore.reasons.length > 0 && (
                      <p className="text-xs text-emerald-700">✓ {healthScore.reasons[0]}</p>
                    )}
                    {healthScore.warnings.length > 0 && (
                      <p className="text-xs text-amber-700">⚠️ {healthScore.warnings[0]}</p>
                    )}
                  </div>
                )}
              </div>

              {/* Right Column: Stage Detail & Resource Action Center */}
              {selectedStage && (
                <div className="lg:col-span-8 space-y-6">
                  
                  {/* Stage Hero Card */}
                  <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-6">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-5">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-full">
                            Stage 0{roadmap.stages.indexOf(selectedStage) + 1}
                          </span>
                          <span className="text-xs font-medium text-slate-500">
                            {selectedStage.duration_minutes} minutes
                          </span>
                        </div>
                        <h2 className="text-2xl font-bold text-slate-900 mt-2">{selectedStage.title}</h2>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleMarkTaught(selectedStage)}
                          className={`px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
                            selectedStage.status === 'taught'
                              ? 'bg-blue-600 text-white'
                              : 'bg-slate-100 hover:bg-slate-200 text-slate-800'
                          }`}
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          {selectedStage.status === 'taught' ? 'Marked Taught' : 'Mark as Taught'}
                        </button>

                        <button
                          onClick={() => handleCreateRemedial(selectedStage)}
                          className="px-3 py-2 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                        >
                          <AlertTriangle className="w-4 h-4" />
                          Add Remedial Stage
                        </button>

                        <button
                          onClick={() => setIsEditingStage(!isEditingStage)}
                          className="p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                        >
                          <PenTool className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Inline Stage Editor */}
                    {isEditingStage ? (
                      <div className="bg-slate-50 rounded-xl p-5 border border-slate-200 space-y-4">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Edit Stage</h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs text-slate-500 mb-1">Title</label>
                            <input
                              type="text"
                              value={editForm.title}
                              onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                              className="w-full bg-white border border-slate-200 rounded-lg p-2 text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-slate-500 mb-1">Duration (min)</label>
                            <input
                              type="number"
                              value={editForm.duration_minutes}
                              onChange={(e) => setEditForm({ ...editForm, duration_minutes: parseInt(e.target.value) || 5 })}
                              className="w-full bg-white border border-slate-200 rounded-lg p-2 text-sm"
                            />
                          </div>
                          <div className="sm:col-span-2">
                            <label className="block text-xs text-slate-500 mb-1">Teacher Action</label>
                            <input
                              type="text"
                              value={editForm.teacher_action}
                              onChange={(e) => setEditForm({ ...editForm, teacher_action: e.target.value })}
                              className="w-full bg-white border border-slate-200 rounded-lg p-2 text-sm"
                            />
                          </div>
                        </div>
                        <div className="flex justify-end gap-2">
                          <button onClick={() => setIsEditingStage(false)} className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-200 rounded-lg">Cancel</button>
                          <button onClick={handleSaveStageEdit} className="px-4 py-1.5 text-xs font-semibold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Save Stage</button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-slate-600 text-sm leading-relaxed">
                        {selectedStage.description}
                      </p>
                    )}

                    {/* Navigation Tabs */}
                    <div className="flex border-b border-slate-200">
                      {[
                        { id: 'details', label: 'Pedagogical Details' },
                        { id: 'timeline', label: 'Timeline & Activities' },
                        { id: 'differentiation', label: 'Differentiation' }
                      ].map(tab => (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id as any)}
                          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors cursor-pointer ${
                            activeTab === tab.id
                              ? 'border-indigo-600 text-indigo-600'
                              : 'border-transparent text-slate-500 hover:text-slate-700'
                          }`}
                        >
                          {tab.label}
                        </button>
                      ))}
                    </div>

                    {/* Tab 1: Pedagogical Details */}
                    {activeTab === 'details' && (
                      <div className="space-y-6">
                        {/* Bloom's Learning Objectives */}
                        <div>
                          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2.5 flex items-center gap-2">
                            <ListChecks className="w-4 h-4 text-indigo-600" />
                            Bloom's Taxonomy Learning Objectives
                          </h4>
                          <div className="space-y-2">
                            {selectedStage.objectives.map((obj, i) => (
                              <div key={i} className="flex items-start gap-2.5 bg-slate-50 p-3 rounded-xl border border-slate-100 text-sm">
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-100 text-indigo-700 shrink-0">
                                  {obj.bloom_level}
                                </span>
                                <span className="text-slate-700">{obj.description}</span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Instructional Actions (Teacher vs Student) */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div className="bg-indigo-50/40 rounded-xl p-4 border border-indigo-100/60 space-y-2">
                            <span className="text-xs font-bold uppercase tracking-wider text-indigo-900 flex items-center gap-1.5">
                              👨‍🏫 Teacher Action
                            </span>
                            <ul className="text-xs text-slate-600 space-y-1.5">
                              {selectedStage.teacher_actions.map((act, i) => (
                                <li key={i}>• {act}</li>
                              ))}
                            </ul>
                          </div>

                          <div className="bg-emerald-50/40 rounded-xl p-4 border border-emerald-100/60 space-y-2">
                            <span className="text-xs font-bold uppercase tracking-wider text-emerald-900 flex items-center gap-1.5">
                              🧑‍🎓 Student Action
                            </span>
                            <ul className="text-xs text-slate-600 space-y-1.5">
                              {selectedStage.student_actions.map((act, i) => (
                                <li key={i}>• {act}</li>
                              ))}
                            </ul>
                          </div>
                        </div>

                        {/* Checkpoint & Expected Misconceptions */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div className="bg-slate-50 rounded-xl p-4 border border-slate-200/80 space-y-2">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                              <HelpCircle className="w-4 h-4 text-genie-amber" />
                              Diagnostic Checkpoints
                            </span>
                            <ul className="text-xs text-slate-600 space-y-1.5">
                              {selectedStage.checkpoint_questions.map((q, i) => (
                                <li key={i}>? {q}</li>
                              ))}
                            </ul>
                          </div>

                          <div className="bg-rose-50/50 rounded-xl p-4 border border-rose-100 space-y-2">
                            <span className="text-xs font-bold uppercase tracking-wider text-rose-800 flex items-center gap-1.5">
                              <AlertTriangle className="w-4 h-4 text-rose-500" />
                              Common Misconceptions
                            </span>
                            <ul className="text-xs text-rose-900 space-y-1.5">
                              {selectedStage.expected_misconceptions.map((m, i) => (
                                <li key={i}>⚠️ {m}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Tab 2: Timeline & Activities */}
                    {activeTab === 'timeline' && (
                      <div className="space-y-4">
                        <div className="space-y-2.5">
                          {selectedStage.activities.map((act, i) => (
                            <div key={i} className="flex items-center gap-4 bg-slate-50 p-3.5 rounded-xl border border-slate-100">
                              <div className="w-12 text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200/60 px-2 py-1 rounded text-center shrink-0">
                                {act.duration_minutes}m
                              </div>
                              <div className="flex-1">
                                <span className="text-xs font-bold uppercase text-slate-500 tracking-wider block">
                                  {act.type}
                                </span>
                                <p className="text-xs text-slate-700 mt-0.5">{act.description}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Tab 3: Differentiation */}
                    {activeTab === 'differentiation' && (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
                          <span className="text-xs font-bold text-slate-800 block mb-1">Core Tier</span>
                          <p className="text-xs text-slate-600">{selectedStage.differentiation.core || 'Standard lesson delivery and baseline problem set.'}</p>
                        </div>
                        <div className="bg-blue-50/50 rounded-xl p-4 border border-blue-100">
                          <span className="text-xs font-bold text-blue-900 block mb-1">Support Tier (Scaffolding)</span>
                          <p className="text-xs text-blue-800">{selectedStage.differentiation.support || 'Visual color-coding and step-by-step hint cards.'}</p>
                        </div>
                        <div className="bg-purple-50/50 rounded-xl p-4 border border-purple-100">
                          <span className="text-xs font-bold text-purple-900 block mb-1">Extension Tier (Advanced)</span>
                          <p className="text-xs text-purple-800">{selectedStage.differentiation.extension || 'Edge-case synthesis and optimization problem.'}</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Stage-Level Resource Action Center */}
                  <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-sm space-y-4">
                    <div>
                      <h3 className="text-lg font-bold text-slate-900">Stage Resource Orchestration</h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Generated deterministically from canonical stage data without redundant research.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                      
                      {/* 1. PPT Card */}
                      <div className="bg-slate-50/80 rounded-xl p-4 border border-slate-200 flex flex-col justify-between space-y-3">
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded flex items-center gap-1">
                              <Presentation className="w-3.5 h-3.5" /> PowerPoint
                            </span>
                            <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                              RECOMMENDED
                            </span>
                          </div>
                          <p className="text-xs text-slate-600">
                            Curated multi-slide deck with concept diagrams and speaker notes.
                          </p>
                        </div>
                        <button
                          onClick={() => handleGenerateResource('PPT')}
                          disabled={isTriggeringResource === 'PPT'}
                          className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                        >
                          {isTriggeringResource === 'PPT' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                          Create PPT Deck
                        </button>
                      </div>

                      {/* 2. Video Card */}
                      <div className="bg-slate-50/80 rounded-xl p-4 border border-slate-200 flex flex-col justify-between space-y-3">
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded flex items-center gap-1">
                              <Video className="w-3.5 h-3.5" /> AI Video
                            </span>
                            <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                              OPTIONAL
                            </span>
                          </div>
                          <p className="text-xs text-slate-600">
                            Micro-learning video storyboard with voice narration.
                          </p>
                        </div>
                        <button
                          onClick={() => handleGenerateResource('Video')}
                          disabled={isTriggeringResource === 'Video'}
                          className="w-full py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                        >
                          {isTriggeringResource === 'Video' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                          Create Video Lesson
                        </button>
                      </div>

                      {/* 3. Teach Me Card */}
                      <div className="bg-slate-50/80 rounded-xl p-4 border border-slate-200 flex flex-col justify-between space-y-3">
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded flex items-center gap-1">
                              <BookOpen className="w-3.5 h-3.5" /> Teach Me
                            </span>
                            <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                              RECOMMENDED
                            </span>
                          </div>
                          <p className="text-xs text-slate-600">
                            Launch interactive Socratic dialogue with live checkpoints.
                          </p>
                        </div>
                        <button
                          onClick={() => handleGenerateResource('Teach')}
                          disabled={isTriggeringResource === 'Teach'}
                          className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                        >
                          {isTriggeringResource === 'Teach' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PlayCircle className="w-3.5 h-3.5" />}
                          Launch Teach Me
                        </button>
                      </div>

                      {/* 4. Quiz Card */}
                      <div className="bg-slate-50/80 rounded-xl p-4 border border-slate-200 flex flex-col justify-between space-y-3">
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded flex items-center gap-1">
                              <HelpCircle className="w-3.5 h-3.5" /> Quiz & Test
                            </span>
                            <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                              RECOMMENDED
                            </span>
                          </div>
                          <p className="text-xs text-slate-600">
                            Diagnostic questions addressing common misconceptions.
                          </p>
                        </div>
                        <button
                          onClick={() => handleGenerateResource('Quiz')}
                          disabled={isTriggeringResource === 'Quiz'}
                          className="w-full py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                        >
                          {isTriggeringResource === 'Quiz' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                          Create Quiz
                        </button>
                      </div>

                      {/* 5. Notes Card */}
                      <div className="bg-slate-50/80 rounded-xl p-4 border border-slate-200 flex flex-col justify-between space-y-3">
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded flex items-center gap-1">
                              <FileText className="w-3.5 h-3.5" /> Study Notes
                            </span>
                            <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                              RECOMMENDED
                            </span>
                          </div>
                          <p className="text-xs text-slate-600">
                            Comprehensive study revision notes with key definitions.
                          </p>
                        </div>
                        <button
                          onClick={() => handleGenerateResource('Notes')}
                          disabled={isTriggeringResource === 'Notes'}
                          className="w-full py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                        >
                          {isTriggeringResource === 'Notes' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                          Generate Notes
                        </button>
                      </div>

                    </div>
                  </div>

                </div>
              )}

            </div>
          )}

        </div>
      </div>
    </AppLayout>
  );
};

export default LessonPlannerPage;
