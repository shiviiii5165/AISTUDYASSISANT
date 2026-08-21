import React, { useState, useEffect, useRef } from 'react';
import { PlayCircle, Clock, Globe, Filter, Sparkles, ChevronDown, Download, Loader2, BookOpen, Brain, HelpCircle, Lightbulb, FileText, RotateCcw, CheckCircle2, AlertCircle, Layers } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';

// ─── Types ───────────────────────────────────────
interface Scene {
  id: string;
  type: string;
  title: string;
  duration_seconds: number;
  teacher_speech: string;
  visual_type: string;
  visual_content: {
    title?: string;
    bullets?: string[];
    formula?: string;
    diagram_description?: string;
  };
  teacher_emotion: string;
}

interface QuizItem {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

interface Flashcard {
  front: string;
  back: string;
}

interface LessonData {
  lesson_title: string;
  language: string;
  estimated_duration_seconds: number;
  learning_objectives: string[];
  prerequisites: string[];
  scenes: Scene[];
  key_takeaways: string[];
  summary_notes: string;
  revision_notes: string[];
  quiz: QuizItem[];
  important_questions: string[];
  flashcards: Flashcard[];
}

// ─── Component ───────────────────────────────────
const VideoGeneratorPage: React.FC = () => {
  const { user: currentUser } = useAuthStore();
  const [topic, setTopic] = useState('');
  
  // Settings
  const [level, setLevel] = useState('Class 10');
  const [duration, setDuration] = useState('5');
  const [language, setLanguage] = useState('hinglish');
  const [showLevelDropdown, setShowLevelDropdown] = useState(false);
  const [showDurationDropdown, setShowDurationDropdown] = useState(false);
  const [showLanguageDropdown, setShowLanguageDropdown] = useState(false);
  
  // Generation state
  const [generating, setGenerating] = useState(false);
  const [lessonId, setLessonId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [lessonData, setLessonData] = useState<LessonData | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // History
  const [pastLessons, setPastLessons] = useState<any[]>([]);
  
  // Active tab for results view
  const [activeTab, setActiveTab] = useState<'scenes' | 'notes' | 'quiz' | 'flashcards' | 'questions'>('scenes');
  
  // Quiz state
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, string>>({});
  const [showQuizResults, setShowQuizResults] = useState(false);
  
  // Flashcard state
  const [flippedCards, setFlippedCards] = useState<Record<number, boolean>>({});
  
  // Active scene
  const [activeSceneIndex, setActiveSceneIndex] = useState(0);

  const resultsRef = useRef<HTMLDivElement>(null);
  
  const levels = ['Class 6', 'Class 7', 'Class 8', 'Class 9', 'Class 10', 'Class 11', 'Class 12', 'Undergraduate', 'Graduate'];
  const durations = [{ val: '5', label: '5 min' }, { val: '8', label: '8 min' }, { val: '10', label: '10 min' }, { val: '15', label: '15 min' }];
  const languages = [{ val: 'hinglish', label: 'Hinglish' }, { val: 'hindi', label: 'Hindi' }, { val: 'english', label: 'English' }];

  // Load past lessons
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const token = useAuthStore.getState().session?.access_token;
        const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/lessons/`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setPastLessons(data);
        }
      } catch (e) {
        console.error("Failed to load lesson history", e);
      }
    };
    loadHistory();
  }, []);
  
  // Poll for lesson status
  useEffect(() => {
    let intervalId: any;
    if (lessonId && (status === 'processing' || status === 'auditing' || status === 'enhancing')) {
      intervalId = setInterval(async () => {
        try {
          const token = useAuthStore.getState().session?.access_token;
          const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/lessons/${lessonId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          const data = await res.json();
          
          setStatus(data.status);
          
          if (data.status === 'ready' && data.lesson_json) {
            setLessonData(data.lesson_json);
            setGenerating(false);
            clearInterval(intervalId);
            // Scroll to results
            setTimeout(() => {
              resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
            }, 300);
          } else if (data.status === 'failed') {
            setError(data.error_message || 'Generation failed. Please try again.');
            setGenerating(false);
            clearInterval(intervalId);
          }
        } catch (e) {
          console.error("Polling error", e);
        }
      }, 3000);
    }
    return () => clearInterval(intervalId);
  }, [lessonId, status]);

  const handleGenerate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!topic.trim()) return;
    
    setGenerating(true);
    setLessonId(null);
    setLessonData(null);
    setError(null);
    setStatus('processing');
    setActiveTab('scenes');
    setSelectedAnswers({});
    setShowQuizResults(false);
    setFlippedCards({});
    setActiveSceneIndex(0);
    
    try {
      const token = useAuthStore.getState().session?.access_token;
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/lessons/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ topic, level, duration, language })
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to start generation');
      }
      
      setLessonId(data.lesson_id);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to generate lesson');
      setGenerating(false);
      setStatus('failed');
    }
  };

  const loadLesson = async (id: string) => {
    try {
      const token = useAuthStore.getState().session?.access_token;
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/lessons/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.status === 'ready' && data.lesson_json) {
        setLessonData(data.lesson_json);
        setLessonId(id);
        setStatus('ready');
        setTopic(data.topic || '');
        setActiveTab('scenes');
        setSelectedAnswers({});
        setShowQuizResults(false);
        setFlippedCards({});
        setActiveSceneIndex(0);
        setTimeout(() => {
          resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
        }, 300);
      }
    } catch (e) {
      console.error("Failed to load lesson", e);
    }
  };

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const getSceneTypeIcon = (type: string) => {
    switch (type) {
      case 'intro': return '🎬';
      case 'concept': return '💡';
      case 'definition': return '📖';
      case 'formula': return '🔢';
      case 'diagram': return '📊';
      case 'example': return '📝';
      case 'comparison': return '⚖️';
      case 'quiz': return '❓';
      case 'summary': return '📋';
      case 'outro': return '🎯';
      default: return '📌';
    }
  };

  const getStatusMessage = () => {
    switch (status) {
      case 'processing': return 'Understanding your topic & creating lesson plan...';
      case 'auditing': return 'Reviewing lesson for completeness...';
      case 'enhancing': return 'Enhancing with missing content...';
      default: return 'Generating...';
    }
  };

  return (
    <AppLayout title="Video Generator">
      <SEO title="GyanVideo AI — Generate Video Lessons" description="Turn any topic into a structured AI teacher-led lesson with notes, quiz, and flashcards." />
      
      <div className="flex flex-col items-center justify-start min-h-[calc(100vh-64px)] pt-12 px-4 pb-12 bg-white relative overflow-hidden">
        
        {/* ── Header Area ── */}
        <div className="relative mb-6 animate-[bounce_3s_ease-in-out_infinite]">
          <div className="w-20 h-20 bg-purple-50 rounded-full flex items-center justify-center shadow-lg relative z-10 overflow-hidden border-4 border-white">
            <PlayCircle className="w-10 h-10 text-purple-600" />
          </div>
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-28 h-28 bg-purple-300 rounded-full blur-3xl opacity-30 z-0"></div>
        </div>

        <div className="flex items-center gap-3 mb-8">
          <div className="flex items-center gap-1.5 px-4 py-1.5 bg-white border border-gray-100 shadow-sm rounded-full text-xs font-semibold text-gray-700">
            <Sparkles className="w-3.5 h-3.5 text-purple-500" />
            <span>GyanVideo AI</span>
          </div>
          {pastLessons.length > 0 && (
            <div className="flex items-center gap-1.5 px-4 py-1.5 bg-white border border-gray-100 shadow-sm rounded-full text-xs font-semibold text-gray-700">
              <Clock className="w-3.5 h-3.5 text-blue-500" />
              <span>{pastLessons.length} lessons created</span>
            </div>
          )}
        </div>

        <div className="text-center mb-8">
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-3">
            <span className="text-gray-800">What do you want </span>
            <span className="text-purple-600">to learn?</span>
          </h1>
          <p className="text-lg text-gray-500 font-medium">Enter any topic — get a complete lesson with notes, quiz & flashcards</p>
        </div>

        {/* ── Input Area ── */}
        <div className="w-full max-w-3xl mx-auto mb-6 relative z-20">
          <div className={`flex items-center bg-white rounded-2xl border border-gray-200 shadow-sm transition-all duration-300 overflow-hidden ${generating ? 'opacity-60 pointer-events-none' : 'hover:shadow-md hover:border-purple-300'}`}>
            <div className="pl-5 pr-2 py-3">
              <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center">
                <Lightbulb className="w-4 h-4 text-purple-600" />
              </div>
            </div>
            <form onSubmit={handleGenerate} className="flex-1 flex items-center">
              <input
                type="text"
                placeholder="e.g. Newton's Laws of Motion, Binary Search, Photosynthesis..."
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                disabled={generating}
                className="w-full py-4 px-2 text-base outline-none bg-transparent placeholder:text-gray-400 font-medium text-gray-800"
              />
              <button 
                type="submit"
                disabled={generating || !topic.trim()}
                className="mr-3 ml-2 px-5 py-2.5 bg-purple-600 text-white rounded-xl font-semibold text-sm hover:bg-purple-700 transition-colors disabled:opacity-40 disabled:hover:bg-purple-600 flex items-center gap-2 whitespace-nowrap"
              >
                {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                Generate
              </button>
            </form>
          </div>
        </div>

        {/* ── Settings Dropdowns ── */}
        <div className="flex flex-wrap items-center justify-center gap-3 max-w-3xl mx-auto mb-8 relative z-30">
          {/* Level */}
          <div className="relative">
            <button 
              onClick={() => { setShowLevelDropdown(!showLevelDropdown); setShowDurationDropdown(false); setShowLanguageDropdown(false); }}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-700 hover:border-purple-300 cursor-pointer shadow-sm transition-colors"
            >
              <Filter className="w-4 h-4 text-purple-400" />
              {level}
              <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
            </button>
            {showLevelDropdown && (
              <div className="absolute top-full left-0 mt-2 bg-white border border-gray-200 rounded-xl shadow-lg py-1 z-50 min-w-[160px]">
                {levels.map(l => (
                  <button key={l} onClick={() => { setLevel(l); setShowLevelDropdown(false); }} className={`w-full text-left px-4 py-2 text-sm hover:bg-purple-50 transition-colors ${level === l ? 'text-purple-600 font-semibold bg-purple-50' : 'text-gray-700'}`}>
                    {l}
                  </button>
                ))}
              </div>
            )}
          </div>
          
          {/* Duration */}
          <div className="relative">
            <button 
              onClick={() => { setShowDurationDropdown(!showDurationDropdown); setShowLevelDropdown(false); setShowLanguageDropdown(false); }}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-700 hover:border-purple-300 cursor-pointer shadow-sm transition-colors"
            >
              <Clock className="w-4 h-4 text-purple-400" />
              {durations.find(d => d.val === duration)?.label}
              <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
            </button>
            {showDurationDropdown && (
              <div className="absolute top-full left-0 mt-2 bg-white border border-gray-200 rounded-xl shadow-lg py-1 z-50 min-w-[120px]">
                {durations.map(d => (
                  <button key={d.val} onClick={() => { setDuration(d.val); setShowDurationDropdown(false); }} className={`w-full text-left px-4 py-2 text-sm hover:bg-purple-50 transition-colors ${duration === d.val ? 'text-purple-600 font-semibold bg-purple-50' : 'text-gray-700'}`}>
                    {d.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Language */}
          <div className="relative">
            <button 
              onClick={() => { setShowLanguageDropdown(!showLanguageDropdown); setShowLevelDropdown(false); setShowDurationDropdown(false); }}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-700 hover:border-purple-300 cursor-pointer shadow-sm transition-colors"
            >
              <Globe className="w-4 h-4 text-purple-400" />
              {languages.find(l => l.val === language)?.label}
              <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
            </button>
            {showLanguageDropdown && (
              <div className="absolute top-full left-0 mt-2 bg-white border border-gray-200 rounded-xl shadow-lg py-1 z-50 min-w-[140px]">
                {languages.map(l => (
                  <button key={l.val} onClick={() => { setLanguage(l.val); setShowLanguageDropdown(false); }} className={`w-full text-left px-4 py-2 text-sm hover:bg-purple-50 transition-colors ${language === l.val ? 'text-purple-600 font-semibold bg-purple-50' : 'text-gray-700'}`}>
                    {l.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Generation Progress ── */}
        {generating && (
          <div className="w-full max-w-2xl mx-auto mb-10 bg-purple-50 border border-purple-100 rounded-2xl p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-purple-100 rounded-full flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
            </div>
            <h3 className="text-lg font-bold text-purple-900 mb-2">Generating your lesson...</h3>
            <p className="text-sm text-purple-700 mb-6">{getStatusMessage()}</p>
            
            <div className="space-y-3 text-left max-w-sm mx-auto">
              {[
                { key: 'processing', label: 'Understanding topic & creating lesson plan' },
                { key: 'auditing', label: 'Reviewing lesson for completeness' },
                { key: 'enhancing', label: 'Enhancing with missing content' },
                { key: 'ready', label: 'Finalizing lesson' },
              ].map(step => {
                const isComplete = 
                  step.key === 'processing' && (status === 'auditing' || status === 'enhancing' || status === 'ready') ||
                  step.key === 'auditing' && (status === 'enhancing' || status === 'ready') ||
                  step.key === 'enhancing' && status === 'ready' ||
                  step.key === 'ready' && status === 'ready';
                const isCurrent = step.key === status;
                
                return (
                  <div key={step.key} className="flex items-center gap-3">
                    {isComplete ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0" />
                    ) : isCurrent ? (
                      <Loader2 className="w-5 h-5 text-purple-500 animate-spin shrink-0" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-gray-300 shrink-0" />
                    )}
                    <span className={`text-sm ${isComplete ? 'text-green-700 font-medium' : isCurrent ? 'text-purple-700 font-semibold' : 'text-gray-400'}`}>
                      {step.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Error State ── */}
        {error && !generating && (
          <div className="w-full max-w-2xl mx-auto mb-10 bg-red-50 border border-red-100 rounded-2xl p-6 text-center">
            <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
            <h3 className="text-lg font-bold text-red-800 mb-1">Generation Failed</h3>
            <p className="text-sm text-red-600 mb-4">{error}</p>
            <button onClick={() => { setError(null); handleGenerate(); }} className="px-5 py-2 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700 transition-colors inline-flex items-center gap-2">
              <RotateCcw className="w-4 h-4" /> Retry
            </button>
          </div>
        )}

        {/* ═══════════ RESULTS ═══════════ */}
        {lessonData && (
          <div ref={resultsRef} className="w-full max-w-5xl mx-auto mt-4">
            
            {/* Lesson Header */}
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-6 mb-6 text-white">
              <h2 className="text-2xl font-bold mb-2">{lessonData.lesson_title}</h2>
              <div className="flex flex-wrap items-center gap-4 text-sm opacity-90">
                <span className="flex items-center gap-1"><Layers className="w-4 h-4" /> {lessonData.scenes?.length || 0} scenes</span>
                <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> {formatDuration(lessonData.estimated_duration_seconds || 0)}</span>
                <span className="flex items-center gap-1"><Globe className="w-4 h-4" /> {lessonData.language}</span>
              </div>
              {lessonData.learning_objectives && (
                <div className="mt-4 pt-4 border-t border-white/20">
                  <p className="text-xs font-semibold uppercase tracking-wider mb-2 opacity-75">Learning Objectives</p>
                  <ul className="space-y-1">
                    {lessonData.learning_objectives.map((obj, i) => (
                      <li key={i} className="text-sm flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                        {obj}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Tab Navigation */}
            <div className="flex items-center gap-1 border-b border-gray-200 mb-6 overflow-x-auto pb-px">
              {[
                { key: 'scenes' as const, label: 'Lesson Scenes', icon: PlayCircle },
                { key: 'notes' as const, label: 'Summary Notes', icon: FileText },
                { key: 'quiz' as const, label: 'Quiz', icon: HelpCircle },
                { key: 'flashcards' as const, label: 'Flashcards', icon: Brain },
                { key: 'questions' as const, label: 'Important Q&A', icon: BookOpen },
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                    activeTab === tab.key
                      ? 'border-purple-600 text-purple-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* ── TAB: Scenes ── */}
            {activeTab === 'scenes' && lessonData.scenes && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
                {/* Scene List */}
                <div className="lg:col-span-1 space-y-2 max-h-[600px] overflow-y-auto pr-2">
                  {lessonData.scenes.map((scene, i) => (
                    <button
                      key={scene.id}
                      onClick={() => setActiveSceneIndex(i)}
                      className={`w-full text-left p-3 rounded-xl border transition-all ${
                        activeSceneIndex === i
                          ? 'border-purple-300 bg-purple-50 shadow-sm'
                          : 'border-gray-100 bg-white hover:border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-lg">{getSceneTypeIcon(scene.type)}</span>
                        <span className="text-xs font-semibold text-gray-400 uppercase">{scene.type}</span>
                        <span className="ml-auto text-xs text-gray-400">{scene.duration_seconds}s</span>
                      </div>
                      <p className="text-sm font-medium text-gray-800 line-clamp-1">{scene.title}</p>
                    </button>
                  ))}
                </div>

                {/* Active Scene Detail */}
                <div className="lg:col-span-2 bg-gray-50 rounded-2xl p-6 border border-gray-100">
                  {lessonData.scenes[activeSceneIndex] && (() => {
                    const scene = lessonData.scenes[activeSceneIndex];
                    return (
                      <>
                        <div className="flex items-center gap-3 mb-4">
                          <span className="text-2xl">{getSceneTypeIcon(scene.type)}</span>
                          <div>
                            <h3 className="text-lg font-bold text-gray-900">{scene.title}</h3>
                            <p className="text-xs text-gray-500">{scene.type} • {scene.duration_seconds}s • {scene.teacher_emotion}</p>
                          </div>
                        </div>
                        
                        {/* Visual Content */}
                        {scene.visual_content && (
                          <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4">
                            <p className="text-xs font-semibold text-purple-600 uppercase mb-2">{scene.visual_type}</p>
                            {scene.visual_content.title && (
                              <p className="font-bold text-gray-800 mb-2">{scene.visual_content.title}</p>
                            )}
                            {scene.visual_content.bullets && scene.visual_content.bullets.length > 0 && (
                              <ul className="space-y-1.5">
                                {scene.visual_content.bullets.map((b, bi) => (
                                  <li key={bi} className="text-sm text-gray-700 flex items-start gap-2">
                                    <span className="text-purple-400 mt-1">•</span>
                                    {b}
                                  </li>
                                ))}
                              </ul>
                            )}
                            {scene.visual_content.formula && (
                              <div className="mt-2 bg-purple-50 text-purple-800 font-mono text-lg font-bold rounded-lg p-3 text-center">
                                {scene.visual_content.formula}
                              </div>
                            )}
                          </div>
                        )}
                        
                        {/* Teacher Speech */}
                        <div className="bg-white rounded-xl border border-gray-200 p-4">
                          <p className="text-xs font-semibold text-green-600 uppercase mb-2">🎙️ Teacher Script</p>
                          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{scene.teacher_speech}</p>
                        </div>
                      </>
                    );
                  })()}
                </div>
              </div>
            )}

            {/* ── TAB: Notes ── */}
            {activeTab === 'notes' && (
              <div className="space-y-6 mb-10">
                {/* Summary */}
                <div className="bg-white rounded-2xl border border-gray-200 p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2"><FileText className="w-5 h-5 text-purple-500" /> Summary Notes</h3>
                  <p className="text-sm text-gray-700 leading-relaxed">{lessonData.summary_notes}</p>
                </div>
                
                {/* Revision Notes */}
                {lessonData.revision_notes && lessonData.revision_notes.length > 0 && (
                  <div className="bg-white rounded-2xl border border-gray-200 p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2"><BookOpen className="w-5 h-5 text-blue-500" /> Revision Notes</h3>
                    <ul className="space-y-2">
                      {lessonData.revision_notes.map((note, i) => (
                        <li key={i} className="text-sm text-gray-700 flex items-start gap-3 p-2 bg-blue-50 rounded-lg">
                          <span className="text-blue-500 font-bold shrink-0">{i + 1}.</span>
                          {note}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Key Takeaways */}
                {lessonData.key_takeaways && lessonData.key_takeaways.length > 0 && (
                  <div className="bg-gradient-to-r from-yellow-50 to-orange-50 rounded-2xl border border-yellow-200 p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2"><Lightbulb className="w-5 h-5 text-yellow-500" /> Key Takeaways</h3>
                    <ul className="space-y-2">
                      {lessonData.key_takeaways.map((takeaway, i) => (
                        <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                          <span className="text-yellow-500 mt-0.5">🔥</span>
                          {takeaway}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* ── TAB: Quiz ── */}
            {activeTab === 'quiz' && lessonData.quiz && (
              <div className="space-y-6 mb-10">
                {lessonData.quiz.map((q, qi) => (
                  <div key={qi} className="bg-white rounded-2xl border border-gray-200 p-6">
                    <p className="text-sm font-bold text-gray-900 mb-4">
                      <span className="text-purple-600 mr-2">Q{qi + 1}.</span>
                      {q.question}
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                      {q.options.map((opt, oi) => {
                        const letter = String.fromCharCode(65 + oi);
                        const isSelected = selectedAnswers[qi] === letter;
                        const isCorrect = q.correct_answer === letter;
                        const showResult = showQuizResults;
                        
                        return (
                          <button
                            key={oi}
                            onClick={() => { if (!showQuizResults) setSelectedAnswers(prev => ({ ...prev, [qi]: letter })); }}
                            className={`text-left p-3 rounded-xl border text-sm font-medium transition-all ${
                              showResult && isCorrect
                                ? 'border-green-400 bg-green-50 text-green-800'
                                : showResult && isSelected && !isCorrect
                                  ? 'border-red-400 bg-red-50 text-red-800'
                                  : isSelected
                                    ? 'border-purple-400 bg-purple-50 text-purple-800'
                                    : 'border-gray-200 text-gray-700 hover:border-purple-200 hover:bg-purple-50/50'
                            }`}
                          >
                            <span className="font-bold mr-2">{letter}.</span>
                            {opt}
                          </button>
                        );
                      })}
                    </div>
                    {showQuizResults && (
                      <div className={`mt-3 p-3 rounded-lg text-sm ${selectedAnswers[qi] === q.correct_answer ? 'bg-green-50 text-green-700' : 'bg-yellow-50 text-yellow-700'}`}>
                        <p className="font-semibold mb-1">{selectedAnswers[qi] === q.correct_answer ? '✅ Correct!' : `❌ Correct answer: ${q.correct_answer}`}</p>
                        <p>{q.explanation}</p>
                      </div>
                    )}
                  </div>
                ))}
                
                {!showQuizResults && (
                  <button
                    onClick={() => setShowQuizResults(true)}
                    disabled={Object.keys(selectedAnswers).length < lessonData.quiz.length}
                    className="w-full py-3 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700 transition-colors disabled:opacity-40"
                  >
                    Check Answers ({Object.keys(selectedAnswers).length}/{lessonData.quiz.length} answered)
                  </button>
                )}
                {showQuizResults && (
                  <div className="text-center bg-purple-50 rounded-2xl p-6">
                    <p className="text-2xl font-bold text-purple-800 mb-1">
                      {lessonData.quiz.filter((q, i) => selectedAnswers[i] === q.correct_answer).length} / {lessonData.quiz.length}
                    </p>
                    <p className="text-sm text-purple-600">Correct Answers</p>
                    <button onClick={() => { setSelectedAnswers({}); setShowQuizResults(false); }} className="mt-4 px-5 py-2 bg-purple-600 text-white rounded-lg text-sm font-semibold hover:bg-purple-700 transition-colors inline-flex items-center gap-2">
                      <RotateCcw className="w-4 h-4" /> Retry Quiz
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* ── TAB: Flashcards ── */}
            {activeTab === 'flashcards' && lessonData.flashcards && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
                {lessonData.flashcards.map((card, ci) => (
                  <div 
                    key={ci}
                    onClick={() => setFlippedCards(prev => ({ ...prev, [ci]: !prev[ci] }))}
                    className="cursor-pointer group perspective"
                  >
                    <div className={`relative h-48 rounded-2xl border-2 transition-all duration-500 ${flippedCards[ci] ? 'border-green-300 bg-green-50' : 'border-purple-200 bg-white hover:border-purple-400 hover:shadow-md'}`}>
                      <div className="absolute inset-0 flex flex-col items-center justify-center p-5 text-center">
                        {!flippedCards[ci] ? (
                          <>
                            <p className="text-xs font-semibold text-purple-400 uppercase mb-2">Question</p>
                            <p className="text-sm font-bold text-gray-800">{card.front}</p>
                            <p className="text-xs text-gray-400 mt-3">Tap to flip</p>
                          </>
                        ) : (
                          <>
                            <p className="text-xs font-semibold text-green-500 uppercase mb-2">Answer</p>
                            <p className="text-sm text-gray-700">{card.back}</p>
                            <p className="text-xs text-gray-400 mt-3">Tap to flip back</p>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* ── TAB: Important Questions ── */}
            {activeTab === 'questions' && lessonData.important_questions && (
              <div className="space-y-3 mb-10">
                {lessonData.important_questions.map((q, qi) => (
                  <div key={qi} className="bg-white rounded-xl border border-gray-200 p-4 flex items-start gap-3">
                    <div className="w-7 h-7 rounded-full bg-purple-100 flex items-center justify-center text-purple-600 font-bold text-xs shrink-0">
                      {qi + 1}
                    </div>
                    <p className="text-sm text-gray-800 font-medium">{q}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Past Lessons History ── */}
        {!lessonData && !generating && pastLessons.length > 0 && (
          <div className="w-full max-w-3xl mx-auto mt-6">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">Recent Lessons</h3>
            <div className="space-y-2">
              {pastLessons.slice(0, 5).map(lesson => (
                <button
                  key={lesson.id}
                  onClick={() => { if (lesson.status === 'ready') loadLesson(lesson.id); }}
                  className={`w-full text-left p-4 bg-white rounded-xl border border-gray-100 hover:border-purple-200 hover:shadow-sm transition-all flex items-center gap-4 ${lesson.status !== 'ready' ? 'opacity-50' : ''}`}
                >
                  <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center shrink-0">
                    <PlayCircle className="w-5 h-5 text-purple-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-800 truncate">{lesson.topic}</p>
                    <p className="text-xs text-gray-400">{lesson.level} • {lesson.language} • {lesson.scene_count || '...'} scenes</p>
                  </div>
                  <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                    lesson.status === 'ready' ? 'bg-green-100 text-green-700' : 
                    lesson.status === 'failed' ? 'bg-red-100 text-red-700' : 
                    'bg-yellow-100 text-yellow-700'
                  }`}>
                    {lesson.status}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default VideoGeneratorPage;
