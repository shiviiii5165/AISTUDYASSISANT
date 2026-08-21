import React, { useState, useEffect } from 'react';
import { ArrowUp, Clock, FileText, Globe, Sparkles, Filter, ChevronDown, CheckCircle2, Download, Loader2 } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';
import UpgradeModal from '../components/billing/UpgradeModal';

const TopicDeckPage: React.FC = () => {
  const { user: currentUser } = useAuthStore();
  const [topic, setTopic] = useState('');
  
  // Fake UI states for the toggles
  const [activeToggles, setActiveToggles] = useState<Record<string, boolean>>({
    rbt: true,
  });
  
  const [generating, setGenerating] = useState(false);
  const [deckId, setDeckId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  
  const isPro = true; // Plan requirement removed

  const toggleFilter = (key: string) => {
    setActiveToggles(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleGenerate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!isPro) {
      setShowUpgradeModal(true);
      return;
    }
    if (!topic.trim()) return;
    
    setGenerating(true);
    setDeckId(null);
    setDownloadUrl(null);
    setStatus('processing');
    
    try {
      const token = useAuthStore.getState().session?.access_token;
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/decks/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ topic, depth: 'full', audience: 'university' })
      });
      
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 403) {
          setShowUpgradeModal(true);
          setGenerating(false);
          return;
        }
        throw new Error(data.detail || 'Failed to start generation');
      }
      
      setDeckId(data.deck_id);
    } catch (err) {
      console.error(err);
      setStatus('failed');
      setGenerating(false);
    }
  };

  useEffect(() => {
    let intervalId: any;
    if (deckId && status === 'processing') {
      intervalId = setInterval(async () => {
        try {
          const token = useAuthStore.getState().session?.access_token;
          const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/decks/${deckId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          const data = await res.json();
          
          if (data.status === 'ready') {
            setStatus('ready');
            setDownloadUrl(data.download_url);
            setGenerating(false);
            clearInterval(intervalId);
          } else if (data.status === 'failed') {
            setStatus('failed');
            setGenerating(false);
            clearInterval(intervalId);
          }
        } catch (e) {
          console.error("Polling error", e);
        }
      }, 3000);
    }
    return () => clearInterval(intervalId);
  }, [deckId, status]);

  return (
    <AppLayout title="Topic Decks">
      <SEO title="Generate PPTX Decks" description="Generate complete PowerPoint presentations instantly with AI." />
      
      <div className="flex flex-col items-center justify-start min-h-[calc(100vh-64px)] pt-16 px-4 pb-12 bg-white relative overflow-hidden">
        
        {/* Animated Genie Container */}
        <div className="relative mb-8 animate-[bounce_3s_ease-in-out_infinite]">
          <div className="w-24 h-24 bg-blue-50 rounded-full flex items-center justify-center shadow-lg relative z-10 overflow-hidden border-4 border-white">
            <div className="text-5xl" style={{ transform: 'scale(1.2) translateY(5px)' }}>🧞‍♂️</div>
          </div>
          {/* Magic glow effect */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 bg-yellow-300 rounded-full blur-3xl opacity-30 z-0"></div>
        </div>

        {/* Top Badges */}
        <div className="flex items-center gap-3 mb-10">
          <div className="flex items-center gap-1.5 px-4 py-1.5 bg-white border border-gray-100 shadow-sm rounded-full text-xs font-semibold text-gray-700">
            <Sparkles className="w-3.5 h-3.5 text-yellow-500" />
            <span>4 free generations left</span>
          </div>
          <div className="flex items-center gap-1.5 px-4 py-1.5 bg-white border border-gray-100 shadow-sm rounded-full text-xs font-semibold text-gray-700">
            <Clock className="w-3.5 h-3.5 text-blue-500" />
            <span>1 total created</span>
          </div>
        </div>

        {/* Greeting */}
        <div className="text-center mb-10">
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-4">
            <span className="text-[#5D4037]">Good morning, </span>
            <span className="text-[#FFA000]">{currentUser?.full_name?.split(' ')[0] || 'User'}.</span>
          </h1>
          <p className="text-xl text-gray-700 font-medium">What would you like to teach today?</p>
        </div>

        {/* Search / Input Area */}
        <div className="w-full max-w-4xl mx-auto mb-6 relative z-20">
          <div className={`flex items-center bg-white rounded-full border border-gray-200 shadow-sm transition-all duration-300 overflow-hidden ${generating ? 'opacity-50' : 'hover:shadow-md hover:border-gray-300'}`}>
            <div className="pl-6 pr-3 py-3">
              <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
                <span className="text-gray-500 font-bold text-lg leading-none">+</span>
              </div>
            </div>
            
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleGenerate(); }}
              placeholder="Cloud Computing Architecture"
              disabled={generating}
              className="flex-1 py-5 px-2 bg-transparent text-gray-800 text-lg focus:outline-none placeholder:text-gray-400"
            />
            
            <div className="pr-4">
              <button
                onClick={() => handleGenerate()}
                disabled={generating || !topic.trim()}
                className="w-10 h-10 rounded-full bg-gray-300 text-white flex items-center justify-center hover:bg-gray-400 transition-colors disabled:opacity-50"
              >
                {generating ? <Loader2 className="w-5 h-5 animate-spin text-gray-600" /> : <ArrowUp className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </div>

        {/* Filters/Toggles mimicking the screenshot */}
        <div className="w-full max-w-4xl mx-auto flex flex-wrap justify-center gap-3">
          
          <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50">
            <Filter className="w-4 h-4 text-blue-500" />
            Level
            <ChevronDown className="w-3 h-3 text-gray-400" />
          </button>
          
          <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50">
            <Clock className="w-4 h-4 text-indigo-500" />
            Duration
            <ChevronDown className="w-3 h-3 text-gray-400" />
          </button>
          
          <button onClick={() => toggleFilter('scenario')} className={`flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium shadow-sm transition-colors ${activeToggles.scenario ? 'text-gray-900 ring-1 ring-gray-300' : 'text-gray-600'}`}>
            <Sparkles className="w-4 h-4 text-gray-400" />
            Scenario Quiz
            <span className={`text-[10px] px-1.5 py-0.5 rounded-sm font-bold ${activeToggles.scenario ? 'bg-black text-white' : 'bg-gray-200 text-gray-600'}`}>
              {activeToggles.scenario ? 'ON' : 'OFF'}
            </span>
          </button>

          <button onClick={() => toggleFilter('exercise')} className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-600 shadow-sm">
            <FileText className="w-4 h-4 text-gray-400" />
            Exercise (1 left)
            <span className="text-[10px] px-1.5 py-0.5 rounded-sm font-bold bg-gray-200 text-gray-600">OFF</span>
          </button>

          <button onClick={() => toggleFilter('visuals')} className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-600 shadow-sm">
            <div className="flex items-center gap-1">
              <span className="text-gray-400">▶</span> Visuals <span className="text-yellow-500">✦ Gold+</span>
            </div>
            <span className="text-[10px] px-1.5 py-0.5 rounded-sm font-bold bg-gray-200 text-gray-600">OFF</span>
          </button>
          
          {/* Row 2 */}
          <div className="w-full flex justify-center gap-3 mt-1">
            <button onClick={() => toggleFilter('trends')} className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-600 shadow-sm">
              <FileText className="w-4 h-4 text-gray-400" />
              Trends
              <span className="text-[10px] px-1.5 py-0.5 rounded-sm font-bold bg-gray-200 text-gray-600">OFF</span>
            </button>
            
            <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50">
              <Globe className="w-4 h-4 text-gray-400" />
              Language (1 left)
              <span className="text-[10px] px-1.5 py-0.5 rounded-sm font-bold bg-gray-200 text-gray-600">EN</span>
            </button>
          </div>
          
          {/* Row 3 */}
          <div className="w-full flex justify-center gap-3 mt-1">
            <button onClick={() => toggleFilter('rbt')} className={`flex items-center gap-2 px-5 py-2 rounded-full text-sm font-bold shadow-sm transition-all ${activeToggles.rbt ? 'bg-[#FFF3E0] border border-[#FFCC80] text-[#E65100]' : 'bg-white border border-gray-200 text-gray-600'}`}>
              RBT
              <span className={`text-[10px] px-1.5 py-0.5 rounded-sm ${activeToggles.rbt ? 'bg-gray-800 text-white' : 'bg-gray-200 text-gray-600'}`}>
                {activeToggles.rbt ? 'ON' : 'OFF'}
              </span>
            </button>
            
            <button className="flex items-center gap-2 px-4 py-2 bg-transparent border border-gray-100 rounded-full text-sm font-medium text-gray-500 hover:bg-gray-50">
              LO-PO Mapping
              <ChevronDown className="w-3 h-3 text-gray-300" />
            </button>
            
            <button className="flex items-center gap-2 px-4 py-2 bg-transparent border border-gray-100 rounded-full text-sm font-medium text-gray-500 hover:bg-gray-50">
              IKS Mapping
              <ChevronDown className="w-3 h-3 text-gray-300" />
            </button>
          </div>
          
        </div>

        {/* Results / Status Area */}
        <div className="w-full max-w-4xl mx-auto mt-12">
          {status === 'processing' && (
            <div className="p-6 bg-blue-50/50 rounded-xl flex flex-col items-center justify-center text-center animate-pulse border border-blue-100">
              <Loader2 className="w-10 h-10 text-blue-500 animate-spin mb-4" />
              <h3 className="font-bold text-gray-800">Crafting your presentation</h3>
              <p className="text-sm text-gray-500 mt-1">
                This takes about 20-40 seconds. I'm researching, writing slides, generating visuals, and styling the deck.
              </p>
            </div>
          )}

          {status === 'ready' && downloadUrl && (
            <div className="p-8 bg-green-50 border border-green-200 rounded-xl flex flex-col items-center justify-center text-center shadow-sm transform transition-all translate-y-0 opacity-100">
              <CheckCircle2 className="w-12 h-12 text-green-500 mb-4" />
              <h3 className="text-xl font-bold text-green-900 mb-2">Your deck is ready!</h3>
              <a
                href={downloadUrl}
                download
                className="mt-4 px-8 py-4 bg-[#5D4037] hover:bg-[#4E342E] text-white font-bold rounded-full flex items-center gap-2 transition-transform hover:scale-105 shadow-md"
              >
                <Download className="w-5 h-5" /> Download .pptx
              </a>
            </div>
          )}
          
          {status === 'failed' && (
            <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-center">
              <p className="text-red-700 font-bold">Failed to generate deck. Please try again or try a different topic.</p>
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
