import React, { useState, useEffect } from 'react';
import { ArrowUp, Clock, FileText, Globe, Sparkles, Filter, ChevronDown, CheckCircle2, Download, Loader2, AlertTriangle, Layers, Palette, Users, Zap, Settings2, Eye, RotateCcw } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';
import UpgradeModal from '../components/billing/UpgradeModal';

// ═══════════════════════════════════════════════════════════════════════════
// CONFIGURATION OPTIONS
// ═══════════════════════════════════════════════════════════════════════════

const PRESET_OPTIONS = [
  { value: 'academic', label: 'Academic', icon: '🎓', desc: 'University lecture with learning progression' },
  { value: 'pitch', label: 'Business', icon: '🚀', desc: 'Data-driven pitch with KPIs & strategy' },
  { value: 'technical', label: 'Technical', icon: '⚙️', desc: 'Architecture diagrams & system deep-dive' },
  { value: 'research', label: 'Research', icon: '🔬', desc: 'Evidence-based findings & methodology' },
  { value: 'teaching', label: 'Teaching', icon: '📚', desc: "Scaffolded lesson with Bloom's alignment" },
];

const DEPTH_OPTIONS = [
  { value: 'full', label: 'Full (10-16 slides)', icon: '📚' },
  { value: 'quick', label: 'Quick (6-8 slides)', icon: '⚡' },
];

const AUDIENCE_OPTIONS = [
  { value: 'university', label: 'University', icon: '🎓' },
  { value: 'high_school', label: 'High School', icon: '🏫' },
  { value: 'professional', label: 'Professional', icon: '💼' },
  { value: 'beginner', label: 'Beginner', icon: '🌱' },
];

const THEME_OPTIONS = [
  { value: '', label: 'AI Pick', colors: ['#1E40AF', '#3B82F6', '#DBEAFE'], desc: 'AI selects best theme' },
  { value: 'blue_professional', label: 'Blue Pro', colors: ['#1E40AF', '#3B82F6', '#DBEAFE'], desc: 'Corporate & Tech' },
  { value: 'indigo_innovation', label: 'Indigo', colors: ['#4F46E5', '#818CF8', '#E0E7FF'], desc: 'AI & Innovation' },
  { value: 'emerald_academic', label: 'Emerald', colors: ['#059669', '#10B981', '#D1FAE5'], desc: 'Science & Research' },
  { value: 'teal_corporate', label: 'Teal', colors: ['#0D9488', '#14B8A6', '#CCFBF1'], desc: 'Enterprise' },
  { value: 'orange_energy', label: 'Orange', colors: ['#C2410C', '#EA580C', '#FFEDD5'], desc: 'Startup & Creative' },
  { value: 'minimal_charcoal', label: 'Minimal', colors: ['#18181B', '#52525B', '#E4E4E7'], desc: 'Executive & Law' },
];

const VISUAL_OPTIONS = [
  { value: 'standard', label: 'Standard', desc: 'Clean layouts, minimal visuals', icon: '📄' },
  { value: 'smart', label: 'Smart', desc: 'AI picks images, diagrams & charts', icon: '🧠' },
  { value: 'premium', label: 'Premium', desc: 'Maximum visual richness', icon: '✨' },
];

const GENERATION_STAGES = [
  { key: 'outline', label: 'Designing narrative & structure', icon: '📝' },
  { key: 'expand', label: 'Writing educational content', icon: '📖' },
  { key: 'render', label: 'Rendering visuals & PPTX', icon: '🎨' },
];

// ═══════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

const TopicDeckPage: React.FC = () => {
  const { user: currentUser } = useAuthStore();
  const [topic, setTopic] = useState('');
  
  // Core config
  const [preset, setPreset] = useState('academic');
  const [depth, setDepth] = useState('full');
  const [audience, setAudience] = useState('university');
  const [themeId, setThemeId] = useState('');
  const [visualMode, setVisualMode] = useState('smart');
  
  // UI state
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showDepthDropdown, setShowDepthDropdown] = useState(false);
  const [showAudienceDropdown, setShowAudienceDropdown] = useState(false);
  
  // Toggles (education features)
  const [activeToggles, setActiveToggles] = useState<Record<string, boolean>>({
    rbt: true,
  });
  
  // Generation state
  const [generating, setGenerating] = useState(false);
  const [currentStage, setCurrentStage] = useState(0);
  const [status, setStatus] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [slideCount, setSlideCount] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [resultTitle, setResultTitle] = useState('');
  
  // History
  const [deckHistory, setDeckHistory] = useState<any[]>([]);
  
  const isPro = true;

  const toggleFilter = (key: string) => {
    setActiveToggles(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Fetch deck history on mount
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const token = useAuthStore.getState().session?.access_token;
        if (!token) return;
        const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/decks/`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setDeckHistory(data || []);
        }
      } catch (e) {
        console.error("Failed to fetch deck history", e);
      }
    };
    fetchHistory();
  }, []);

  // ═══════════════════════════════════════════════════════════════════════
  // GENERATION HANDLER
  // ═══════════════════════════════════════════════════════════════════════

  const handleGenerate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!isPro) { setShowUpgradeModal(true); return; }
    if (!topic.trim()) return;
    
    setGenerating(true);
    setDownloadUrl(null);
    setSlideCount(null);
    setErrorMessage(null);
    setStatus('processing');
    setCurrentStage(0);
    
    const token = useAuthStore.getState().session?.access_token;
    const apiUrl = import.meta.env.VITE_API_URL || '';
    
    try {
      // STEP 1: Outline
      setCurrentStage(0);
      const outlineRes = await fetch(`${apiUrl}/api/decks/outline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ topic, depth, audience }),
      });
      
      if (!outlineRes.ok) {
        if (outlineRes.status === 403) { setShowUpgradeModal(true); setGenerating(false); setStatus(null); return; }
        throw new Error((await outlineRes.json()).detail || 'Failed at outline stage');
      }
      
      const { deck_id, outline_data } = await outlineRes.json();
      
      // STEP 2: Expand
      setCurrentStage(1);
      const expandRes = await fetch(`${apiUrl}/api/decks/expand`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ topic, audience, outline_data }),
      });
      
      if (!expandRes.ok) throw new Error((await expandRes.json()).detail || 'Failed at content expansion stage');
      
      const { expanded_data } = await expandRes.json();

      // STEP 3: Render
      setCurrentStage(2);
      const renderRes = await fetch(`${apiUrl}/api/decks/render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ deck_id, topic, depth, audience, expanded_data }),
      });
      
      if (!renderRes.ok) throw new Error((await renderRes.json()).detail || 'Failed to render PowerPoint');
      
      const renderData = await renderRes.json();
      
      if (renderData.status === 'ready' && renderData.download_url) {
        setStatus('ready');
        setDownloadUrl(renderData.download_url);
        setSlideCount(renderData.slide_count);
        setResultTitle(expanded_data?.deck_title || topic);
      } else {
        throw new Error('Generation completed but download URL is missing.');
      }
      
      setGenerating(false);
      
    } catch (err: any) {
      console.error('[PPT Generator] Error:', err);
      const msg = err?.message || 'Unknown error';
      setErrorMessage(msg.includes('Failed to fetch') 
        ? 'Network error: could not reach the server. Please check your connection and try again.'
        : msg
      );
      setStatus('failed');
      setGenerating(false);
    }
  };

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClick = () => {
      setShowDepthDropdown(false);
      setShowAudienceDropdown(false);
    };
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  const totalCreated = deckHistory.length;
  const readyCount = deckHistory.filter((d: any) => d.status === 'ready').length;

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  // ═══════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════

  return (
    <AppLayout title="PPT Generator">
      <SEO title="AI Presentation Studio" description="Generate professional PowerPoint presentations with AI-powered design intelligence." />
      
      <div className="flex flex-col items-center justify-start min-h-[calc(100vh-64px)] pt-12 px-4 pb-12 bg-[#FAFAFA] relative overflow-hidden">
        
        {/* Subtle background gradient */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-to-b from-blue-50/50 to-transparent rounded-full blur-3xl" />
        </div>

        {/* Top Stats Badges */}
        <div className="flex items-center gap-3 mb-8 relative z-10">
          <div className="flex items-center gap-1.5 px-4 py-1.5 bg-white border border-gray-100 shadow-sm rounded-full text-xs font-semibold text-gray-600">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            <span>{readyCount} decks generated</span>
          </div>
          <div className="flex items-center gap-1.5 px-4 py-1.5 bg-white border border-gray-100 shadow-sm rounded-full text-xs font-semibold text-gray-600">
            <Clock className="w-3.5 h-3.5 text-blue-500" />
            <span>{totalCreated} total</span>
          </div>
        </div>

        {/* Greeting */}
        <div className="text-center mb-8 relative z-10">
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-3">
            <span className="text-gray-800">{getGreeting()}, </span>
            <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              {currentUser?.full_name?.split(' ')[0] || 'User'}
            </span>
          </h1>
          <p className="text-lg text-gray-500 font-medium">What would you like to present today?</p>
        </div>

        {/* ─── Topic Input ─── */}
        <div className="w-full max-w-3xl mx-auto mb-6 relative z-20">
          <div className={`flex items-center bg-white rounded-2xl border border-gray-200 shadow-sm transition-all duration-300 overflow-hidden ${generating ? 'opacity-50 pointer-events-none' : 'hover:shadow-md hover:border-gray-300 focus-within:shadow-md focus-within:border-blue-300'}`}>
            <div className="pl-5 pr-2 py-3">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
            </div>
            
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleGenerate(); }}
              placeholder="Cloud Computing Architecture, Machine Learning Fundamentals..."
              disabled={generating}
              className="flex-1 py-4 px-3 bg-transparent text-gray-800 text-base focus:outline-none placeholder:text-gray-400"
            />
            
            <div className="pr-3">
              <button
                onClick={() => handleGenerate()}
                disabled={generating || !topic.trim()}
                className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white flex items-center justify-center hover:from-blue-600 hover:to-indigo-700 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
              >
                {generating ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowUp className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </div>

        {/* ─── Preset Cards ─── */}
        <div className="w-full max-w-3xl mx-auto mb-5 relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Presentation Type</span>
          </div>
          <div className="flex gap-2 flex-wrap">
            {PRESET_OPTIONS.map(p => (
              <button
                key={p.value}
                onClick={() => setPreset(p.value)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all border ${
                  preset === p.value
                    ? 'bg-blue-50 border-blue-200 text-blue-700 shadow-sm'
                    : 'bg-white border-gray-150 text-gray-600 hover:bg-gray-50 hover:border-gray-200'
                }`}
              >
                <span className="text-base">{p.icon}</span>
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* ─── Theme Picker ─── */}
        <div className="w-full max-w-3xl mx-auto mb-5 relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <Palette className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Theme</span>
          </div>
          <div className="flex gap-2 flex-wrap">
            {THEME_OPTIONS.map(t => (
              <button
                key={t.value}
                onClick={() => setThemeId(t.value)}
                title={t.desc}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium transition-all border ${
                  themeId === t.value
                    ? 'bg-white border-gray-300 shadow-sm ring-1 ring-gray-200'
                    : 'bg-white border-gray-100 text-gray-600 hover:border-gray-200'
                }`}
              >
                <div className="flex gap-0.5">
                  {t.colors.map((c, i) => (
                    <div key={i} className="w-3 h-3 rounded-full" style={{ backgroundColor: c }} />
                  ))}
                </div>
                <span className="text-gray-700">{t.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* ─── Quick Config Row ─── */}
        <div className="w-full max-w-3xl mx-auto flex flex-wrap gap-2 mb-4 relative z-10">
          
          {/* Audience Dropdown */}
          <div className="relative" onClick={(e) => e.stopPropagation()}>
            <button 
              onClick={() => { setShowAudienceDropdown(!showAudienceDropdown); setShowDepthDropdown(false); }}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-150 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition-all"
            >
              <Users className="w-4 h-4 text-blue-500" />
              {AUDIENCE_OPTIONS.find(a => a.value === audience)?.icon} {AUDIENCE_OPTIONS.find(a => a.value === audience)?.label}
              <ChevronDown className={`w-3 h-3 text-gray-400 transition-transform ${showAudienceDropdown ? 'rotate-180' : ''}`} />
            </button>
            {showAudienceDropdown && (
              <div className="absolute top-full mt-1 left-0 bg-white border border-gray-200 rounded-xl shadow-lg z-50 min-w-[200px] overflow-hidden">
                {AUDIENCE_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => { setAudience(opt.value); setShowAudienceDropdown(false); }}
                    className={`w-full flex items-center gap-2 px-4 py-2.5 text-sm text-left hover:bg-gray-50 transition-colors ${audience === opt.value ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-gray-700'}`}
                  >
                    <span>{opt.icon}</span> {opt.label}
                    {audience === opt.value && <CheckCircle2 className="w-4 h-4 ml-auto text-blue-500" />}
                  </button>
                ))}
              </div>
            )}
          </div>
          
          {/* Depth Dropdown */}
          <div className="relative" onClick={(e) => e.stopPropagation()}>
            <button 
              onClick={() => { setShowDepthDropdown(!showDepthDropdown); setShowAudienceDropdown(false); }}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-150 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition-all"
            >
              <Layers className="w-4 h-4 text-indigo-500" />
              {DEPTH_OPTIONS.find(d => d.value === depth)?.icon} {DEPTH_OPTIONS.find(d => d.value === depth)?.label}
              <ChevronDown className={`w-3 h-3 text-gray-400 transition-transform ${showDepthDropdown ? 'rotate-180' : ''}`} />
            </button>
            {showDepthDropdown && (
              <div className="absolute top-full mt-1 left-0 bg-white border border-gray-200 rounded-xl shadow-lg z-50 min-w-[220px] overflow-hidden">
                {DEPTH_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => { setDepth(opt.value); setShowDepthDropdown(false); }}
                    className={`w-full flex items-center gap-2 px-4 py-2.5 text-sm text-left hover:bg-gray-50 transition-colors ${depth === opt.value ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-gray-700'}`}
                  >
                    <span>{opt.icon}</span> {opt.label}
                    {depth === opt.value && <CheckCircle2 className="w-4 h-4 ml-auto text-indigo-500" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Visual Mode */}
          {VISUAL_OPTIONS.map(v => (
            <button
              key={v.value}
              onClick={() => setVisualMode(v.value)}
              title={v.desc}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-all border ${
                visualMode === v.value
                  ? 'bg-indigo-50 border-indigo-200 text-indigo-700'
                  : 'bg-white border-gray-100 text-gray-500 hover:bg-gray-50'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              {v.label}
            </button>
          ))}

          {/* Advanced toggle */}
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-100 rounded-xl text-sm font-medium text-gray-500 hover:bg-gray-50 transition-all"
          >
            <Settings2 className="w-3.5 h-3.5" />
            Advanced
            <ChevronDown className={`w-3 h-3 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
          </button>
        </div>

        {/* ─── Advanced Settings Drawer ─── */}
        {showAdvanced && (
          <div className="w-full max-w-3xl mx-auto mb-4 p-4 bg-white border border-gray-200 rounded-2xl shadow-sm relative z-10 animate-in slide-in-from-top-2 duration-200">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <button onClick={() => toggleFilter('rbt')} className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all border ${activeToggles.rbt ? 'bg-orange-50 border-orange-200 text-orange-700' : 'bg-gray-50 border-gray-150 text-gray-500'}`}>
                RBT / Bloom's
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${activeToggles.rbt ? 'bg-orange-600 text-white' : 'bg-gray-200 text-gray-500'}`}>
                  {activeToggles.rbt ? 'ON' : 'OFF'}
                </span>
              </button>
              <button onClick={() => toggleFilter('scenario')} className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all border ${activeToggles.scenario ? 'bg-blue-50 border-blue-200 text-blue-700' : 'bg-gray-50 border-gray-150 text-gray-500'}`}>
                Scenario Quiz
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${activeToggles.scenario ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'}`}>
                  {activeToggles.scenario ? 'ON' : 'OFF'}
                </span>
              </button>
              <button className="flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-50 border border-gray-150 rounded-xl text-sm font-medium text-gray-500">
                <Globe className="w-3.5 h-3.5" /> Language
                <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-gray-200 text-gray-500">EN</span>
              </button>
              <button className="flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-50 border border-gray-150 rounded-xl text-sm font-medium text-gray-500">
                <FileText className="w-3.5 h-3.5" /> Exercises
                <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-gray-200 text-gray-500">OFF</span>
              </button>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* GENERATION PROGRESS */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        <div className="w-full max-w-3xl mx-auto mt-6 relative z-10">
          {status === 'processing' && (
            <div className="p-8 bg-white rounded-2xl border border-gray-200 shadow-sm">
              {/* Stage Progress */}
              <div className="flex items-center justify-between mb-8">
                {GENERATION_STAGES.map((stage, i) => (
                  <div key={stage.key} className="flex items-center flex-1">
                    <div className="flex flex-col items-center flex-1">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-2 transition-all duration-500 ${
                        i < currentStage ? 'bg-green-100 text-green-600' :
                        i === currentStage ? 'bg-blue-100 text-blue-600 ring-2 ring-blue-200 animate-pulse' :
                        'bg-gray-100 text-gray-400'
                      }`}>
                        {i < currentStage ? (
                          <CheckCircle2 className="w-5 h-5" />
                        ) : i === currentStage ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          <span className="text-sm font-bold">{i + 1}</span>
                        )}
                      </div>
                      <span className={`text-xs font-medium text-center ${
                        i <= currentStage ? 'text-gray-700' : 'text-gray-400'
                      }`}>{stage.label}</span>
                    </div>
                    {i < GENERATION_STAGES.length - 1 && (
                      <div className={`w-12 h-0.5 mx-2 mb-6 transition-colors ${
                        i < currentStage ? 'bg-green-300' : 'bg-gray-200'
                      }`} />
                    )}
                  </div>
                ))}
              </div>

              <div className="text-center">
                <p className="text-sm text-gray-500">
                  This typically takes 30-60 seconds. Please don't close this tab.
                </p>
                <div className="flex items-center justify-center gap-3 mt-3 text-xs text-gray-400">
                  <span className="flex items-center gap-1"><Layers className="w-3 h-3" /> {depth === 'full' ? '10-16 slides' : '6-8 slides'}</span>
                  <span>|</span>
                  <span>{AUDIENCE_OPTIONS.find(a => a.value === audience)?.label} level</span>
                  <span>|</span>
                  <span>{PRESET_OPTIONS.find(p => p.value === preset)?.label} style</span>
                </div>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════ */}
          {/* SUCCESS RESULT */}
          {/* ═══════════════════════════════════════════════════════════════ */}
          {status === 'ready' && downloadUrl && (
            <div className="p-8 bg-white border border-gray-200 rounded-2xl shadow-sm">
              {/* Success header */}
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center">
                  <CheckCircle2 className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-800">Your presentation is ready!</h3>
                  <p className="text-sm text-gray-500">
                    {resultTitle || topic} · {slideCount} slides · {PRESET_OPTIONS.find(p => p.value === preset)?.label}
                  </p>
                </div>
              </div>

              {/* Info pills */}
              <div className="flex flex-wrap gap-2 mb-6">
                <span className="px-3 py-1 bg-blue-50 text-blue-700 text-xs font-semibold rounded-full">
                  {AUDIENCE_OPTIONS.find(a => a.value === audience)?.label} Level
                </span>
                <span className="px-3 py-1 bg-indigo-50 text-indigo-700 text-xs font-semibold rounded-full">
                  {depth === 'full' ? 'Full Depth' : 'Quick Overview'}
                </span>
                <span className="px-3 py-1 bg-gray-100 text-gray-600 text-xs font-semibold rounded-full">
                  {THEME_OPTIONS.find(t => t.value === themeId)?.label || 'AI Theme'} Theme
                </span>
                <span className="px-3 py-1 bg-green-50 text-green-700 text-xs font-semibold rounded-full">
                  16:9 Widescreen
                </span>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-3">
                <a
                  href={downloadUrl}
                  download
                  className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold rounded-xl shadow-sm transition-all hover:shadow-md"
                >
                  <Download className="w-5 h-5" /> Download .pptx
                </a>
                <button
                  onClick={() => { setStatus(null); setTopic(''); setDownloadUrl(null); }}
                  className="flex items-center gap-2 px-5 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-xl transition-colors"
                >
                  <RotateCcw className="w-4 h-4" /> New Deck
                </button>
              </div>
            </div>
          )}
          
          {/* ═══════════════════════════════════════════════════════════════ */}
          {/* ERROR STATE */}
          {/* ═══════════════════════════════════════════════════════════════ */}
          {status === 'failed' && (
            <div className="p-8 bg-white border border-red-200 rounded-2xl shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl bg-red-100 flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-red-500" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-800">Generation failed</h3>
                  {errorMessage && (
                    <p className="text-sm text-red-500 mt-1">{errorMessage}</p>
                  )}
                </div>
              </div>
              <button 
                onClick={() => { setStatus(null); setErrorMessage(null); }}
                className="px-5 py-2.5 bg-red-100 hover:bg-red-200 text-red-700 font-semibold rounded-xl text-sm transition-colors"
              >
                Try Again
              </button>
            </div>
          )}
        </div>

      </div>
      
      <UpgradeModal 
        isOpen={showUpgradeModal} 
        onClose={() => setShowUpgradeModal(false)} 
        message="Topic Decks are a Pro-exclusive feature." 
      />
    </AppLayout>
  );
};

export default TopicDeckPage;
