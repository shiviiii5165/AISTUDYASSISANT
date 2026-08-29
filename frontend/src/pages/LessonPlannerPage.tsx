import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Map, Sparkles, Clock, CheckCircle2, AlertCircle, PlayCircle, BookOpen, 
  Presentation, Video, HelpCircle, Save, Layers, ListChecks, PenTool, ExternalLink, ChevronDown, ChevronRight, Lock, FileText, Loader2
} from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';

// Types mapping to Backend schemas
type StageStatus = 'locked' | 'available' | 'in_progress' | 'material_ready' | 'taught' | 'assessment_pending' | 'mastered' | 'needs_review' | 'blocked';

interface StageActivity {
  type: string;
  description: string;
  duration_minutes: number;
}

interface RoadmapStage {
  id: string;
  concept_id: string;
  title: string;
  description: string;
  duration_minutes: number;
  status: StageStatus;
  activities: StageActivity[];
  checkpoint_questions: string[];
  recommended_resources: string[];
}

interface LearningRoadmap {
  id: string;
  topic: string;
  target_duration_minutes: number;
  stages: RoadmapStage[];
  version: number;
  next_best_action: string;
}

const LessonPlannerPage: React.FC = () => {
  const { user } = useAuthStore();
  const [topic, setTopic] = useState('');
  const [duration, setDuration] = useState('60');
  const [isGenerating, setIsGenerating] = useState(false);
  const [roadmap, setRoadmap] = useState<LearningRoadmap | null>(null);
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null);
  const [healthScore, setHealthScore] = useState<any>(null);

  const generateRoadmap = async () => {
    setIsGenerating(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${(user as any)?.access_token || ''}`
        },
        body: JSON.stringify({
          topic: topic || "DBMS Normalization",
          level: "B.Tech",
          language: "hinglish",
          class_type: "Interactive Lecture",
          target_duration_minutes: parseInt(duration)
        })
      });

      if (!response.ok) throw new Error("Failed to generate");
      const data = await response.json();
      setRoadmap(data);
      if (data.stages.length > 0) {
        setSelectedStageId(data.stages[0].id);
      }
      
      // Fetch Health Score
      checkHealth(data.id);
    } catch (err) {
      console.error(err);
      alert("Failed to generate roadmap.");
    } finally {
      setIsGenerating(false);
    }
  };

  const checkHealth = async (id: string) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/lesson-planner/${id}/health`, {
        headers: { 'Authorization': `Bearer ${(user as any)?.access_token || ''}` }
      });
      if (response.ok) {
        setHealthScore(await response.json());
      }
    } catch (e) { }
  };

  const generateResource = (type: string) => {
    alert(`Triggering ${type} generation for stage: ${selectedStageId}. This integrates with the new adapters in the backend!`);
  };

  const StatusIcon = ({ status }: { status: StageStatus }) => {
    switch (status) {
      case 'mastered': return <CheckCircle2 className="w-5 h-5 text-emerald-500" />;
      case 'taught': return <CheckCircle2 className="w-5 h-5 text-blue-500" />;
      case 'available': return <PlayCircle className="w-5 h-5 text-indigo-500" />;
      case 'locked': return <Lock className="w-5 h-5 text-slate-400" />;
      default: return <div className="w-3 h-3 rounded-full bg-slate-300" />;
    }
  };

  return (
    <AppLayout title="Lesson Planner">
      <SEO title="AI Lesson Planner | TeachGenie" description="Adaptive Course-to-Classroom Intelligence" />
      
      <div className="max-w-7xl mx-auto px-4 py-8">
        
        {/* Header & Input */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
            <Map className="w-8 h-8 text-indigo-600" />
            AI Lesson Planner 2.0
          </h1>
          <p className="text-slate-600 mt-2 text-lg">Adaptive Course-to-Classroom Intelligence</p>
        </div>

        {!roadmap ? (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 max-w-2xl">
            <h2 className="text-xl font-semibold mb-6">What are you teaching?</h2>
            <textarea
              className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4 min-h-[120px] focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
              placeholder="E.g., Mujhe DBMS normalization B.Tech students ko 60 minutes mein padhana hai..."
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />
            
            <div className="flex gap-4 mt-6">
              <div className="flex-1">
                <label className="block text-sm font-medium text-slate-700 mb-2">Duration (min)</label>
                <select 
                  className="w-full bg-white border border-slate-200 rounded-lg p-3"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                >
                  <option value="15">15 min</option>
                  <option value="30">30 min</option>
                  <option value="45">45 min</option>
                  <option value="60">60 min</option>
                  <option value="90">90 min</option>
                </select>
              </div>
            </div>

            <button
              onClick={generateRoadmap}
              disabled={isGenerating || !topic.trim()}
              className="mt-8 w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium py-3 px-6 rounded-xl flex items-center justify-center gap-2 transition-colors"
            >
              {isGenerating ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
              {isGenerating ? 'Generating Roadmap...' : 'Generate Roadmap'}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Left Panel: Roadmap */}
            <div className="lg:col-span-4 bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
              <h2 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                <Layers className="w-5 h-5 text-indigo-600" />
                {roadmap.topic.toUpperCase()}
              </h2>
              
              <div className="space-y-3">
                {roadmap.stages.map((stage, idx) => (
                  <button
                    key={stage.id}
                    onClick={() => setSelectedStageId(stage.id)}
                    className={`w-full text-left p-4 rounded-xl border transition-all flex items-start gap-4 ${
                      selectedStageId === stage.id 
                        ? 'border-indigo-500 bg-indigo-50/50 shadow-sm' 
                        : 'border-slate-100 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <div className="mt-0.5">
                      <StatusIcon status={stage.status} />
                    </div>
                    <div>
                      <h3 className={`font-medium ${selectedStageId === stage.id ? 'text-indigo-900' : 'text-slate-800'}`}>
                        {stage.title}
                      </h3>
                      <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
                        <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5"/> {stage.duration_minutes}m</span>
                        <span className="capitalize">{stage.status.replace('_', ' ')}</span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Center & Right Panels */}
            {selectedStageId && (
              <div className="lg:col-span-8 flex flex-col gap-6">
                
                {/* Health Score Banner */}
                {healthScore && (
                  <div className={`p-4 rounded-xl border flex items-center justify-between ${
                    healthScore.score >= 90 ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'
                  }`}>
                    <div>
                      <h4 className="font-semibold flex items-center gap-2">
                        Lesson Health: {healthScore.score}/100
                      </h4>
                      {healthScore.warnings.length > 0 && (
                        <p className="text-sm text-amber-700 mt-1">
                          {healthScore.warnings[0]}
                        </p>
                      )}
                    </div>
                    <div className="px-3 py-1 bg-white rounded-full text-sm font-medium border shadow-sm">
                      Next: {roadmap.next_best_action.toUpperCase()}
                    </div>
                  </div>
                )}

                {/* Stage Detail Panel */}
                {roadmap.stages.filter(s => s.id === selectedStageId).map(stage => (
                  <div key={stage.id} className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
                    <div className="flex items-center justify-between mb-6">
                      <h2 className="text-2xl font-bold text-slate-800">{stage.title}</h2>
                      <div className="flex items-center gap-2">
                        <button className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors">
                          <PenTool className="w-5 h-5" />
                        </button>
                      </div>
                    </div>

                    <p className="text-slate-600 mb-8">{stage.description}</p>

                    <div className="grid grid-cols-2 gap-6 mb-8">
                      <div className="bg-slate-50 rounded-xl p-5 border border-slate-100">
                        <h4 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                          <ListChecks className="w-4 h-4 text-indigo-500" />
                          Activities
                        </h4>
                        <ul className="space-y-3">
                          {stage.activities.map((act, i) => (
                            <li key={i} className="text-sm flex items-start gap-2 text-slate-600">
                              <span className="px-2 py-0.5 bg-white border rounded text-xs font-medium shrink-0">
                                {act.duration_minutes}m
                              </span>
                              <span>{act.description}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="bg-slate-50 rounded-xl p-5 border border-slate-100">
                        <h4 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                          <HelpCircle className="w-4 h-4 text-rose-500" />
                          Checkpoints
                        </h4>
                        <ul className="space-y-2 list-disc list-inside text-sm text-slate-600">
                          {stage.checkpoint_questions.map((q, i) => (
                            <li key={i}>{q}</li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* Resource Action Bar */}
                    <div className="border-t pt-6">
                      <h4 className="font-medium text-slate-800 mb-4">Generate Stage Resources</h4>
                      <div className="flex flex-wrap gap-3">
                        <button onClick={() => generateResource('PPT')} className="flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-lg font-medium transition-colors">
                          <Presentation className="w-4 h-4" /> PPT Deck
                        </button>
                        <button onClick={() => generateResource('Video')} className="flex items-center gap-2 px-4 py-2 bg-rose-50 text-rose-700 hover:bg-rose-100 rounded-lg font-medium transition-colors">
                          <Video className="w-4 h-4" /> Video Lesson
                        </button>
                        <button onClick={() => generateResource('TeachMe')} className="flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg font-medium transition-colors">
                          <BookOpen className="w-4 h-4" /> Teach Me
                        </button>
                        <button onClick={() => generateResource('Quiz')} className="flex items-center gap-2 px-4 py-2 bg-amber-50 text-amber-700 hover:bg-amber-100 rounded-lg font-medium transition-colors">
                          <FileText className="w-4 h-4" /> Worksheet
                        </button>
                      </div>
                    </div>

                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default LessonPlannerPage;
