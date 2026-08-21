import React, { useState } from 'react';
import { PlayCircle, Clock, Globe, Filter, Sparkles } from 'lucide-react';
import AppLayout from '../components/AppLayout';
import SEO from '../components/SEO';
import { useAuthStore } from '../store/useAuthStore';
import UpgradeModal from '../components/billing/UpgradeModal';

const VideoGeneratorPage: React.FC = () => {
  const { user: currentUser } = useAuthStore();
  const [topic, setTopic] = useState('');
  
  // Fake UI states for the toggles
  const [activeToggles, setActiveToggles] = useState<Record<string, boolean>>({
    rbt: true,
  });
  
  const [generating, setGenerating] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  
  const isPro = true;

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
    // Placeholder for actual video generation logic
    setTimeout(() => {
      alert("Video generation is coming soon! This is a placeholder for GyanVideo AI.");
      setGenerating(false);
    }, 2000);
  };

  return (
    <AppLayout title="Video Generator">
      <SEO title="Generate Video Lessons" description="Turn any topic into an AI teacher-led video lesson." />
      
      <div className="flex flex-col items-center justify-start min-h-[calc(100vh-64px)] pt-16 px-4 pb-12 bg-white relative overflow-hidden">
        
        {/* Animated Icon Container */}
        <div className="relative mb-8 animate-[bounce_3s_ease-in-out_infinite]">
          <div className="w-24 h-24 bg-purple-50 rounded-full flex items-center justify-center shadow-lg relative z-10 overflow-hidden border-4 border-white">
            <PlayCircle className="w-12 h-12 text-purple-600" />
          </div>
          {/* Magic glow effect */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 bg-purple-300 rounded-full blur-3xl opacity-30 z-0"></div>
        </div>

        {/* Top Badges */}
        <div className="flex items-center gap-3 mb-10">
          <div className="flex items-center gap-1.5 px-4 py-1.5 bg-white border border-gray-100 shadow-sm rounded-full text-xs font-semibold text-gray-700">
            <Sparkles className="w-3.5 h-3.5 text-purple-500" />
            <span>GyanVideo AI Preview</span>
          </div>
        </div>

        {/* Greeting */}
        <div className="text-center mb-10">
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-4">
            <span className="text-purple-900">Good morning, </span>
            <span className="text-purple-600">{currentUser?.full_name?.split(' ')[0] || 'User'}.</span>
          </h1>
          <p className="text-xl text-gray-700 font-medium">What would you like to teach today?</p>
        </div>

        {/* Search / Input Area */}
        <div className="w-full max-w-4xl mx-auto mb-6 relative z-20">
          <div className={`flex items-center bg-white rounded-full border border-gray-200 shadow-sm transition-all duration-300 overflow-hidden ${generating ? 'opacity-50' : 'hover:shadow-md hover:border-gray-300'}`}>
            <div className="pl-6 pr-3 py-3">
              <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center">
                <PlayCircle className="w-4 h-4 text-purple-600" />
              </div>
            </div>
            
            <form onSubmit={handleGenerate} className="flex-1 flex items-center">
              <input
                type="text"
                placeholder="Explain Newton's Laws of Motion..."
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                disabled={generating}
                className="w-full py-4 px-2 text-lg outline-none bg-transparent placeholder:text-gray-400 font-medium text-gray-800"
              />
              <button 
                type="submit"
                disabled={generating || !topic.trim()}
                className="mr-3 ml-2 p-3 bg-gray-100 text-gray-400 rounded-full hover:bg-purple-600 hover:text-white transition-colors disabled:opacity-50 disabled:hover:bg-gray-100 disabled:hover:text-gray-400"
              >
                {generating ? <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" /> : <PlayCircle className="w-5 h-5" />}
              </button>
            </form>
          </div>
        </div>

        {/* Configuration Toggles */}
        <div className="flex flex-wrap items-center justify-center gap-3 max-w-3xl mx-auto mb-16 relative z-20">
          
          <div className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-700 hover:border-gray-300 cursor-pointer shadow-sm">
            <Filter className="w-4 h-4 text-gray-400" />
            Class 10
          </div>
          
          <div className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-700 hover:border-gray-300 cursor-pointer shadow-sm">
            <Clock className="w-4 h-4 text-gray-400" />
            5 min
          </div>

          <div className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-700 hover:border-gray-300 cursor-pointer shadow-sm">
            <Globe className="w-4 h-4 text-gray-400" />
            Hinglish
          </div>
        </div>

      </div>

      <UpgradeModal 
        isOpen={showUpgradeModal} 
        onClose={() => setShowUpgradeModal(false)} 
        triggerFeature="Video Generation" 
      />
    </AppLayout>
  );
};

export default VideoGeneratorPage;
