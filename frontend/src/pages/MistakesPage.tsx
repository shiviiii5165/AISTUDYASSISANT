import React, { useState, useEffect } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Sparkles,
  HelpCircle,
  ArrowRight,
  RefreshCw,
  Info,
  ChevronRight,
  BookOpen,
  Compass,
  GraduationCap,
  X,
  History,
  ShieldCheck,
  Search,
  Filter
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/AppLayout';
import { mistakesApi } from '../lib/mistakesApi';
import type {
  MistakePattern,
  MistakeEvent,
  PatternDetailResponse,
  RepairRecommendation,
  ErrorType,
  PatternStatus
} from '../types/mistakes';

type ActiveTab = 'attention' | 'active' | 'repaired' | 'history';

export const MistakesPage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<ActiveTab>('attention');
  const [patterns, setPatterns] = useState<MistakePattern[]>([]);
  const [events, setEvents] = useState<MistakeEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Detail Modal State
  const [selectedPatternId, setSelectedPatternId] = useState<string | null>(null);
  const [patternDetail, setPatternDetail] = useState<PatternDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);

  // Age-Appropriate Perspective Toggle (Junior vs Analytical Senior)
  const [simplifiedTone, setSimplifiedTone] = useState<boolean>(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedSubject, setSelectedSubject] = useState<string>('ALL');

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [patternsRes, eventsRes] = await Promise.all([
        mistakesApi.getPatterns(),
        mistakesApi.getRecentMistakes(50)
      ]);
      setPatterns(patternsRes);
      setEvents(eventsRes);
    } catch (err: any) {
      console.error('Failed to load Mistake DNA:', err);
      setError('Unable to load mistake intelligence data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const openDetail = async (patternId: string) => {
    setSelectedPatternId(patternId);
    setDetailLoading(true);
    try {
      const detail = await mistakesApi.getPatternDetail(patternId);
      setPatternDetail(detail);
    } catch (err) {
      console.error('Failed to fetch pattern detail:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setSelectedPatternId(null);
    setPatternDetail(null);
  };

  const handleReviewWithTutor = (skillId: string, skillName: string) => {
    navigate(`/teach?skill=${encodeURIComponent(skillId)}&mode=TUTOR`);
  };

  // Filtered lists
  const filteredPatterns = patterns.filter((p) => {
    const matchesSearch =
      p.skill_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.error_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.error_subtype && p.error_subtype.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesSubject = selectedSubject === 'ALL' || p.subject === selectedSubject;
    return matchesSearch && matchesSubject;
  });

  const needsAttention = filteredPatterns.filter(
    (p) =>
      (p.pattern_status === 'PERSISTENT' || p.pattern_status === 'RECURRING') &&
      p.repair_status !== 'REPAIRED'
  );

  const activePatterns = filteredPatterns.filter(
    (p) => p.pattern_status === 'ISOLATED' && p.repair_status !== 'REPAIRED'
  );

  const recentlyRepaired = filteredPatterns.filter(
    (p) => p.repair_status === 'REPAIRED' || p.pattern_status === 'REPAIRED'
  );

  const formatErrorTypeLabel = (type: ErrorType): string => {
    return type.replace(/_/g, ' ');
  };

  const getStatusBadge = (status: PatternStatus, repairStatus: string) => {
    if (repairStatus === 'REPAIRED' || status === 'REPAIRED') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Repaired
        </span>
      );
    }
    if (repairStatus === 'REASSESSMENT_NEEDED') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
          <AlertCircle className="w-3.5 h-3.5" />
          Reassessment Due
        </span>
      );
    }
    if (status === 'PERSISTENT') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
          <RefreshCw className="w-3.5 h-3.5" />
          Persistent Pattern
        </span>
      );
    }
    if (status === 'RECURRING') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
          <Clock className="w-3.5 h-3.5" />
          Recurring
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20">
        Isolated Slip
      </span>
    );
  };

  return (
    <AppLayout title="Mistake Intelligence">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Header Banner */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-900/40 via-slate-900/60 to-slate-950/80 p-8 border border-indigo-500/20 backdrop-blur-md shadow-xl">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2 max-w-2xl">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                Persistent Learning Intelligence
              </div>
              <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
                Mistake DNA
              </h1>
              <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
                {simplifiedTone
                  ? "Every mistake is a stepping stone. Here is what we've noticed so you can practice the exact step that matters!"
                  : 'Systematic intelligence on learning error mechanisms. Tracks isolated slips, recurring patterns, prerequisite linkages, and verified repair milestones.'}
              </p>
            </div>

            {/* Tone Toggle & Refresh */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <button
                onClick={() => setSimplifiedTone(!simplifiedTone)}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold transition-all border border-slate-700 bg-slate-800/80 text-slate-200 hover:bg-slate-700/80 flex items-center gap-2"
                title="Toggle between junior friendly and analytical tone"
              >
                <GraduationCap className="w-4 h-4 text-indigo-400" />
                {simplifiedTone ? 'Junior Tone Active' : 'Analytical View'}
              </button>

              <button
                onClick={fetchData}
                disabled={loading}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold transition-all border border-slate-700 bg-slate-800/80 text-slate-200 hover:bg-slate-700/80 flex items-center gap-2"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                Sync Intelligence
              </button>
            </div>
          </div>
        </div>

        {/* Search & Subject Bar */}
        <div className="flex flex-col sm:flex-row gap-4 items-center justify-between bg-slate-900/40 p-4 rounded-xl border border-slate-800/80">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search skill, error type..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950/60 border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex gap-2 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
            {['ALL', 'Mathematics', 'Physics', 'Chemistry', 'Biology', 'Computer Science'].map(
              (subj) => (
                <button
                  key={subj}
                  onClick={() => setSelectedSubject(subj)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                    selectedSubject === subj
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-800/60 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                  }`}
                >
                  {subj}
                </button>
              )
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-slate-800">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('attention')}
              className={`py-4 px-1 border-b-2 font-semibold text-sm transition-all flex items-center gap-2 ${
                activeTab === 'attention'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <AlertCircle className="w-4 h-4 text-indigo-400" />
              Needs Attention ({needsAttention.length})
            </button>

            <button
              onClick={() => setActiveTab('active')}
              className={`py-4 px-1 border-b-2 font-semibold text-sm transition-all flex items-center gap-2 ${
                activeTab === 'active'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Clock className="w-4 h-4 text-blue-400" />
              Active Patterns ({activePatterns.length})
            </button>

            <button
              onClick={() => setActiveTab('repaired')}
              className={`py-4 px-1 border-b-2 font-semibold text-sm transition-all flex items-center gap-2 ${
                activeTab === 'repaired'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Recently Repaired ({recentlyRepaired.length})
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`py-4 px-1 border-b-2 font-semibold text-sm transition-all flex items-center gap-2 ${
                activeTab === 'history'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <History className="w-4 h-4 text-slate-400" />
              Complete History ({events.length})
            </button>
          </nav>
        </div>

        {/* Loading / Error States */}
        {loading && (
          <div className="text-center py-16 space-y-3">
            <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
            <p className="text-slate-400 text-sm">Analyzing mistake intelligence...</p>
          </div>
        )}

        {error && !loading && (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm">
            {error}
          </div>
        )}

        {/* Tab 1: Needs Attention */}
        {!loading && !error && activeTab === 'attention' && (
          <div className="space-y-4">
            {needsAttention.length === 0 ? (
              <div className="text-center py-16 bg-slate-900/20 rounded-2xl border border-slate-800 p-8 space-y-3">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
                <h3 className="text-lg font-bold text-slate-200">No Recurring Mistakes Needing Attention</h3>
                <p className="text-slate-400 text-sm max-w-md mx-auto">
                  You do not currently have repeated learning error patterns. Any past slips are isolated or already repaired!
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {needsAttention.map((pat) => (
                  <div
                    key={pat.id}
                    className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-indigo-500/40 transition-all space-y-4 shadow-lg backdrop-blur-sm"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <span className="text-xs font-mono font-medium text-indigo-400 tracking-wider uppercase">
                          {pat.skill_id}
                        </span>
                        <h3 className="text-lg font-bold text-white capitalize">
                          {formatErrorTypeLabel(pat.error_type)}
                        </h3>
                        {pat.error_subtype && (
                          <span className="text-xs text-slate-400 font-medium">
                            Subtype: {pat.error_subtype.replace(/_/g, ' ')}
                          </span>
                        )}
                      </div>
                      {getStatusBadge(pat.pattern_status, pat.repair_status)}
                    </div>

                    <div className="text-xs text-slate-400 flex items-center gap-3">
                      <span>Seen {pat.occurrence_count} times</span>
                      <span>•</span>
                      <span>Last: {new Date(pat.last_seen_at).toLocaleDateString()}</span>
                    </div>

                    {pat.prerequisite_signal && (
                      <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start gap-2">
                        <Info className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                        <div>{pat.prerequisite_signal}</div>
                      </div>
                    )}

                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-slate-300 text-xs space-y-1">
                      <div className="text-slate-400 font-semibold">Recommended Repair:</div>
                      <div>{pat.recommended_repair_action}</div>
                    </div>

                    <div className="flex items-center justify-between pt-2">
                      <button
                        onClick={() => openDetail(pat.id)}
                        className="text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
                      >
                        Explain Pattern →
                      </button>

                      <button
                        onClick={() => handleReviewWithTutor(pat.skill_id, pat.skill_id)}
                        className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-all flex items-center gap-2 shadow-md shadow-indigo-600/20"
                      >
                        <GraduationCap className="w-3.5 h-3.5" />
                        Review with Tutor
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Active Patterns (Isolated) */}
        {!loading && !error && activeTab === 'active' && (
          <div className="space-y-4">
            {activePatterns.length === 0 ? (
              <div className="text-center py-16 bg-slate-900/20 rounded-2xl border border-slate-800 p-8 space-y-3">
                <CheckCircle2 className="w-12 h-12 text-slate-500 mx-auto" />
                <h3 className="text-lg font-bold text-slate-200">No Isolated Errors</h3>
                <p className="text-slate-400 text-sm">All recent checks are clean or categorized.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {activePatterns.map((pat) => (
                  <div
                    key={pat.id}
                    className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80 hover:border-slate-700 transition-all space-y-4"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <span className="text-xs font-mono font-medium text-slate-400 tracking-wider">
                          {pat.skill_id}
                        </span>
                        <h3 className="text-base font-bold text-white capitalize">
                          {formatErrorTypeLabel(pat.error_type)}
                        </h3>
                      </div>
                      {getStatusBadge(pat.pattern_status, pat.repair_status)}
                    </div>

                    <p className="text-xs text-slate-400">
                      Single isolated slip detected on {new Date(pat.first_seen_at).toLocaleDateString()}.
                    </p>

                    <div className="flex items-center justify-between pt-2">
                      <button
                        onClick={() => openDetail(pat.id)}
                        className="text-xs font-semibold text-slate-400 hover:text-slate-200"
                      >
                        Details →
                      </button>

                      <button
                        onClick={() => handleReviewWithTutor(pat.skill_id, pat.skill_id)}
                        className="px-3.5 py-1.5 rounded-lg text-xs font-medium border border-slate-700 hover:bg-slate-800 text-slate-200 transition-all"
                      >
                        Practice with Tutor
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Recently Repaired */}
        {!loading && !error && activeTab === 'repaired' && (
          <div className="space-y-4">
            {recentlyRepaired.length === 0 ? (
              <div className="text-center py-16 bg-slate-900/20 rounded-2xl border border-slate-800 p-8 space-y-3">
                <Clock className="w-12 h-12 text-slate-500 mx-auto" />
                <h3 className="text-lg font-bold text-slate-200">No Repaired Patterns Yet</h3>
                <p className="text-slate-400 text-sm max-w-md mx-auto">
                  When you successfully pass independent checks on previously challenging topics, verified repair milestones will appear here!
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {recentlyRepaired.map((pat) => (
                  <div
                    key={pat.id}
                    className="p-6 rounded-2xl bg-emerald-950/20 border border-emerald-500/20 space-y-4"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <span className="text-xs font-mono font-medium text-emerald-400">
                          {pat.skill_id}
                        </span>
                        <h3 className="text-lg font-bold text-white capitalize">
                          {formatErrorTypeLabel(pat.error_type)}
                        </h3>
                      </div>
                      {getStatusBadge(pat.pattern_status, pat.repair_status)}
                    </div>

                    <div className="text-xs text-slate-300">
                      Occurred {pat.occurrence_count} time{pat.occurrence_count !== 1 ? 's' : ''} previously, then successfully repaired via verified independent check.
                    </div>

                    <div className="text-xs text-emerald-400 font-medium">
                      ✓ Historical repair memory preserved for future revision.
                    </div>

                    <button
                      onClick={() => openDetail(pat.id)}
                      className="text-xs font-semibold text-emerald-400 hover:underline"
                    >
                      View Repair Evidence →
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Complete Event History Ledger */}
        {!loading && !error && activeTab === 'history' && (
          <div className="space-y-4">
            <div className="bg-slate-900/60 rounded-2xl border border-slate-800 overflow-hidden shadow-lg">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-300">
                  <thead className="bg-slate-950/80 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="px-6 py-4">Detected At</th>
                      <th className="px-6 py-4">Skill</th>
                      <th className="px-6 py-4">Error Taxonomy</th>
                      <th className="px-6 py-4">Source</th>
                      <th className="px-6 py-4">Assistance</th>
                      <th className="px-6 py-4">Summary</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {events.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-slate-500 text-sm">
                          No detected error events recorded yet.
                        </td>
                      </tr>
                    ) : (
                      events.map((ev) => (
                        <tr key={ev.id} className="hover:bg-slate-800/30 transition-colors">
                          <td className="px-6 py-4 whitespace-nowrap text-xs text-slate-400 font-mono">
                            {new Date(ev.detected_at).toLocaleDateString()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap font-medium text-slate-200">
                            {ev.skill_id || 'General'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="px-2 py-0.5 rounded text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                              {formatErrorTypeLabel(ev.primary_error_type)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-xs text-slate-400">
                            {ev.source_type}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-xs text-slate-400">
                            {ev.assistance_level}
                          </td>
                          <td className="px-6 py-4 text-xs text-slate-300 max-w-xs truncate">
                            {ev.error_summary || ev.question_reference || 'N/A'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Explainability Detail Modal */}
        {selectedPatternId && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in">
            <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 sm:p-8 space-y-6 max-h-[90vh] overflow-y-auto">
              <button
                onClick={closeDetail}
                className="absolute top-6 right-6 p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>

              {detailLoading || !patternDetail ? (
                <div className="text-center py-12 space-y-3">
                  <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin mx-auto" />
                  <p className="text-slate-400 text-sm">Loading pattern diagnosis...</p>
                </div>
              ) : (
                <>
                  <div className="space-y-1">
                    <span className="text-xs font-mono font-medium text-indigo-400 uppercase">
                      {patternDetail.pattern.skill_id}
                    </span>
                    <h2 className="text-2xl font-bold text-white capitalize">
                      {formatErrorTypeLabel(patternDetail.pattern.error_type)}
                    </h2>
                    <p className="text-slate-400 text-xs">
                      Topic: {patternDetail.skill_name}
                    </p>
                  </div>

                  {/* Explainability Box */}
                  <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                    <div className="text-xs font-semibold text-indigo-400 flex items-center gap-1.5">
                      <Info className="w-4 h-4" />
                      Why This Pattern Exists (§37 Explainability):
                    </div>
                    <p className="text-sm text-slate-300 leading-relaxed">
                      {patternDetail.explainability}
                    </p>
                  </div>

                  {/* Prerequisite Signal */}
                  {patternDetail.pattern.prerequisite_signal && (
                    <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs space-y-1">
                      <div className="font-semibold text-amber-400">Prerequisite Relation:</div>
                      <div>{patternDetail.pattern.prerequisite_signal}</div>
                    </div>
                  )}

                  {/* Repair Action */}
                  <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/30 space-y-2">
                    <div className="text-xs font-semibold text-indigo-300">
                      Recommended Pedagogical Action:
                    </div>
                    <p className="text-sm text-slate-200">
                      {patternDetail.recommended_repair.recommended_repair_action}
                    </p>
                  </div>

                  {/* Repair History Ledger */}
                  {patternDetail.repair_history.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-slate-400">
                        Repair Evidence Ledger ({patternDetail.repair_history.length}):
                      </div>
                      <div className="space-y-2">
                        {patternDetail.repair_history.map((rh) => (
                          <div
                            key={rh.id}
                            className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-500/20 text-xs text-slate-300 flex items-center justify-between"
                          >
                            <div>
                              <div className="font-semibold text-emerald-400">{rh.repair_action}</div>
                              <div className="text-slate-400">Source: {rh.evidence_source} • {rh.assistance_level}</div>
                            </div>
                            <div className="text-slate-500 font-mono text-[10px]">
                              {new Date(rh.verified_at).toLocaleDateString()}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                    <button
                      onClick={closeDetail}
                      className="px-4 py-2 rounded-xl text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
                    >
                      Close
                    </button>

                    <button
                      onClick={() => {
                        closeDetail();
                        handleReviewWithTutor(patternDetail.pattern.skill_id, patternDetail.skill_name);
                      }}
                      className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-all flex items-center gap-2 shadow-lg shadow-indigo-600/30"
                    >
                      <GraduationCap className="w-4 h-4" />
                      Review with Socratic Tutor
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default MistakesPage;
