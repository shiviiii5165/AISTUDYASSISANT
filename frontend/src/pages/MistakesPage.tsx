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
  Filter,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import AppLayout from '../components/AppLayout';
import { mistakesApi } from '../lib/mistakesApi';
import type {
  MistakePattern,
  MistakeEvent,
  PatternDetailResponse,
  RepairRecommendation,
  ErrorType,
  PatternStatus,
} from '../types/mistakes';
import { Button, Card, Badge, EmptyState } from '../components/ui';
import { cardHover, staggerContainer, staggerItem } from '../lib/motion';

type ActiveTab = 'attention' | 'active' | 'repaired' | 'history';

export const MistakesPage: React.FC = () => {
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();
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
        mistakesApi.getRecentMistakes(50),
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

  const handleReviewWithTutor = (skillId: string, _skillName: string) => {
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
        <Badge tone="green" icon={<CheckCircle2 className="w-3.5 h-3.5" />}>
          Repaired
        </Badge>
      );
    }
    if (repairStatus === 'REASSESSMENT_NEEDED') {
      return (
        <Badge tone="yellow" icon={<AlertCircle className="w-3.5 h-3.5" />}>
          Reassessment Due
        </Badge>
      );
    }
    if (status === 'PERSISTENT') {
      return (
        <Badge tone="red" icon={<AlertCircle className="w-3.5 h-3.5" />}>
          Persistent Pattern
        </Badge>
      );
    }
    if (status === 'RECURRING') {
      return (
        <Badge tone="blue" icon={<Clock className="w-3.5 h-3.5" />}>
          Recurring
        </Badge>
      );
    }
    return (
      <Badge tone="neutral">
        Isolated Slip
      </Badge>
    );
  };

  return (
    <AppLayout title="Mistake Intelligence">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 bg-[var(--bg-primary)]">
        {/* Header Hero Banner: Premium White Elevated 3D Card */}
        <Card variant="elevated" className="p-8 sm:p-10 relative overflow-hidden border border-[var(--border)]">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-3 max-w-2xl">
              <div className="flex items-center gap-2">
                <Badge tone="purple" icon={<Sparkles className="w-3.5 h-3.5 text-[var(--accent-purple)]" />}>
                  Persistent Learning Intelligence
                </Badge>
              </div>
              <h1 className="text-3xl sm:text-4xl font-extrabold font-display tracking-tight text-[var(--text-primary)]">
                Mistake DNA
              </h1>
              <p className="text-[var(--text-secondary)] text-sm sm:text-base leading-relaxed">
                {simplifiedTone
                  ? "Every mistake is a stepping stone. Here is what we've noticed so you can practice the exact step that matters!"
                  : 'Systematic intelligence on learning error mechanisms. Tracks isolated slips, recurring patterns, prerequisite linkages, and verified repair milestones.'}
              </p>
            </div>

            {/* Tone Toggle & Sync Action */}
            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="secondary"
                size="sm"
                icon={<GraduationCap className="w-4 h-4 text-[var(--accent-purple)]" />}
                onClick={() => setSimplifiedTone(!simplifiedTone)}
                title="Toggle between junior friendly and analytical tone"
              >
                {simplifiedTone ? 'Junior Tone Active' : 'Analytical View'}
              </Button>

              <Button
                variant="secondary"
                size="sm"
                icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
                disabled={loading}
                onClick={fetchData}
              >
                Sync Intelligence
              </Button>
            </div>
          </div>
        </Card>

        {/* Search & Subject Bar: Clean White Elevated Strip */}
        <div className="flex flex-col sm:flex-row gap-4 items-center justify-between bg-white p-4 rounded-2xl border border-[var(--border)] shadow-xs">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              type="text"
              placeholder="Search skill, error taxonomy..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[var(--bg-subtle)] border border-[var(--border)] rounded-xl pl-10 pr-4 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--brand-primary)] focus:bg-white transition-colors"
            />
          </div>

          <div className="flex gap-2 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
            {['ALL', 'Mathematics', 'Physics', 'Chemistry', 'Biology', 'Computer Science'].map(
              (subj) => {
                const isSelected = selectedSubject === subj;
                return (
                  <button
                    key={subj}
                    onClick={() => setSelectedSubject(subj)}
                    className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all duration-150 cursor-pointer ${
                      isSelected
                        ? 'bg-[var(--brand-primary)] text-white shadow-xs'
                        : 'bg-white text-[var(--text-secondary)] border border-[var(--border)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'
                    }`}
                  >
                    {subj}
                  </button>
                );
              }
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-[var(--border)]">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('attention')}
              className={`py-3.5 px-1 border-b-2 font-semibold text-sm transition-all flex items-center gap-2 cursor-pointer ${
                activeTab === 'attention'
                  ? 'border-[var(--brand-primary)] text-[var(--brand-primary)]'
                  : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)]'
              }`}
            >
              <AlertCircle className="w-4 h-4" />
              Needs Attention ({needsAttention.length})
            </button>

            <button
              onClick={() => setActiveTab('active')}
              className={`py-3.5 px-1 border-b-2 font-semibold text-sm transition-all flex items-center gap-2 cursor-pointer ${
                activeTab === 'active'
                  ? 'border-[var(--brand-primary)] text-[var(--brand-primary)]'
                  : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)]'
              }`}
            >
              <Clock className="w-4 h-4" />
              Isolated Slips ({activePatterns.length})
            </button>

            <button
              onClick={() => setActiveTab('repaired')}
              className={`py-3.5 px-1 border-b-2 font-semibold text-sm transition-all flex items-center gap-2 cursor-pointer ${
                activeTab === 'repaired'
                  ? 'border-[var(--brand-primary)] text-[var(--brand-primary)]'
                  : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)]'
              }`}
            >
              <CheckCircle2 className="w-4 h-4" />
              Recently Repaired ({recentlyRepaired.length})
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`py-3.5 px-1 border-b-2 font-semibold text-sm transition-all flex items-center gap-2 cursor-pointer ${
                activeTab === 'history'
                  ? 'border-[var(--brand-primary)] text-[var(--brand-primary)]'
                  : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)]'
              }`}
            >
              <History className="w-4 h-4" />
              Event Ledger ({events.length})
            </button>
          </nav>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-[var(--accent-yellow-bg)] border border-[var(--accent-yellow-border)] text-[var(--accent-yellow-text)] text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Tab 1: Needs Attention */}
        {!loading && !error && activeTab === 'attention' && (
          <div className="space-y-4">
            {needsAttention.length === 0 ? (
              <EmptyState
                icon={<CheckCircle2 className="w-7 h-7 text-[var(--accent-green)]" />}
                title="No Recurring Mistakes Needing Attention"
                description="You do not currently have repeated learning error patterns. Any past slips are isolated or already repaired!"
                tone="green"
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {needsAttention.map((pat) => (
                  <Card
                    key={pat.id}
                    variant="elevated"
                    className="p-6 space-y-4 hover:border-[var(--accent-purple-border)] transition-all"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <span className="text-xs font-mono font-bold text-[var(--accent-purple-text)] tracking-wider uppercase">
                          {pat.skill_id}
                        </span>
                        <h3 className="text-lg font-bold font-display text-[var(--text-primary)] capitalize">
                          {formatErrorTypeLabel(pat.error_type)}
                        </h3>
                        {pat.error_subtype && (
                          <span className="text-xs text-[var(--text-muted)] font-medium">
                            Subtype: {pat.error_subtype.replace(/_/g, ' ')}
                          </span>
                        )}
                      </div>
                      {getStatusBadge(pat.pattern_status, pat.repair_status)}
                    </div>

                    <div className="text-xs text-[var(--text-muted)] flex items-center gap-3">
                      <span>Seen {pat.occurrence_count} times</span>
                      <span>•</span>
                      <span>Last: {new Date(pat.last_seen_at).toLocaleDateString()}</span>
                    </div>

                    {pat.prerequisite_signal && (
                      <div className="p-3.5 rounded-xl bg-[var(--accent-yellow-bg)] border border-[var(--accent-yellow-border)] text-[var(--accent-yellow-text)] text-xs flex items-start gap-2.5">
                        <Info className="w-4 h-4 shrink-0 mt-0.5 text-[var(--accent-yellow)]" />
                        <div className="leading-relaxed">{pat.prerequisite_signal}</div>
                      </div>
                    )}

                    <div className="p-3.5 rounded-xl bg-[var(--bg-subtle)] border border-[var(--border)] text-[var(--text-secondary)] text-xs space-y-1">
                      <div className="text-[var(--text-primary)] font-semibold">Recommended Repair:</div>
                      <div className="leading-relaxed">{pat.recommended_repair_action}</div>
                    </div>

                    <div className="flex items-center justify-between pt-2">
                      <button
                        onClick={() => openDetail(pat.id)}
                        className="text-xs font-semibold text-[var(--brand-primary)] hover:text-[var(--brand-primary-hover)] transition-colors cursor-pointer"
                      >
                        Explain Pattern →
                      </button>

                      <Button
                        variant="ai"
                        size="sm"
                        icon={<GraduationCap className="w-4 h-4" />}
                        onClick={() => handleReviewWithTutor(pat.skill_id, pat.skill_id)}
                      >
                        Review with Tutor
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Isolated Slips */}
        {!loading && !error && activeTab === 'active' && (
          <div className="space-y-4">
            {activePatterns.length === 0 ? (
              <EmptyState
                icon={<CheckCircle2 className="w-7 h-7 text-[var(--accent-sky)]" />}
                title="No Isolated Errors"
                description="All recent checks are clean or categorized into persistent patterns."
                tone="sky"
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {activePatterns.map((pat) => (
                  <Card
                    key={pat.id}
                    variant="elevated"
                    className="p-6 space-y-4"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <span className="text-xs font-mono font-medium text-[var(--text-muted)] tracking-wider">
                          {pat.skill_id}
                        </span>
                        <h3 className="text-base font-bold font-display text-[var(--text-primary)] capitalize">
                          {formatErrorTypeLabel(pat.error_type)}
                        </h3>
                      </div>
                      {getStatusBadge(pat.pattern_status, pat.repair_status)}
                    </div>

                    <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                      Single isolated slip detected on {new Date(pat.first_seen_at).toLocaleDateString()}.
                    </p>

                    <div className="flex items-center justify-between pt-2">
                      <button
                        onClick={() => openDetail(pat.id)}
                        className="text-xs font-semibold text-[var(--brand-primary)] hover:text-[var(--brand-primary-hover)] cursor-pointer"
                      >
                        Details →
                      </button>

                      <Button
                        variant="secondary"
                        size="xs"
                        onClick={() => handleReviewWithTutor(pat.skill_id, pat.skill_id)}
                      >
                        Practice with Tutor
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Recently Repaired */}
        {!loading && !error && activeTab === 'repaired' && (
          <div className="space-y-4">
            {recentlyRepaired.length === 0 ? (
              <EmptyState
                icon={<Clock className="w-7 h-7 text-[var(--accent-green)]" />}
                title="No Repaired Patterns Yet"
                description="When you successfully pass independent checks on previously challenging topics, verified repair milestones will appear here!"
                tone="green"
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {recentlyRepaired.map((pat) => (
                  <Card
                    key={pat.id}
                    variant="elevated"
                    className="p-6 space-y-4 border-l-4 border-l-[var(--accent-green)]"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <span className="text-xs font-mono font-medium text-[var(--accent-green-text)]">
                          {pat.skill_id}
                        </span>
                        <h3 className="text-lg font-bold font-display text-[var(--text-primary)] capitalize">
                          {formatErrorTypeLabel(pat.error_type)}
                        </h3>
                      </div>
                      {getStatusBadge(pat.pattern_status, pat.repair_status)}
                    </div>

                    <div className="text-xs text-[var(--text-secondary)] leading-relaxed">
                      Occurred {pat.occurrence_count} time{pat.occurrence_count !== 1 ? 's' : ''} previously, then successfully repaired via verified independent check.
                    </div>

                    <div className="text-xs text-[var(--accent-green-text)] font-semibold flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[var(--accent-green)]" />
                      Historical repair memory preserved for future revision.
                    </div>

                    <button
                      onClick={() => openDetail(pat.id)}
                      className="text-xs font-semibold text-[var(--accent-green-text)] hover:underline cursor-pointer"
                    >
                      View Repair Evidence →
                    </button>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Complete Event History Ledger */}
        {!loading && !error && activeTab === 'history' && (
          <div className="space-y-4">
            <Card variant="elevated" className="overflow-hidden p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-[var(--text-secondary)]">
                  <thead className="bg-[var(--bg-subtle)] text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider border-b border-[var(--border)]">
                    <tr>
                      <th className="px-6 py-4">Detected At</th>
                      <th className="px-6 py-4">Skill</th>
                      <th className="px-6 py-4">Error Taxonomy</th>
                      <th className="px-6 py-4">Source</th>
                      <th className="px-6 py-4">Assistance</th>
                      <th className="px-6 py-4">Summary</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {events.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-10 text-center text-[var(--text-muted)] text-sm">
                          No detected error events recorded yet.
                        </td>
                      </tr>
                    ) : (
                      events.map((ev) => (
                        <tr key={ev.id} className="hover:bg-[var(--bg-hover)] transition-colors">
                          <td className="px-6 py-4 whitespace-nowrap text-xs text-[var(--text-muted)] font-mono">
                            {new Date(ev.detected_at).toLocaleDateString()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap font-medium text-[var(--text-primary)]">
                            {ev.skill_id || 'General'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <Badge tone="purple">
                              {formatErrorTypeLabel(ev.primary_error_type)}
                            </Badge>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-xs text-[var(--text-muted)]">
                            {ev.source_type}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-xs text-[var(--text-muted)]">
                            {ev.assistance_level}
                          </td>
                          <td className="px-6 py-4 text-xs text-[var(--text-secondary)] max-w-xs truncate">
                            {ev.error_summary || ev.question_reference || 'N/A'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}

        {/* Explainability Detail Modal */}
        {selectedPatternId && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/30 backdrop-blur-sm animate-in fade-in">
            <div className="relative w-full max-w-2xl bg-white border border-[var(--border)] rounded-2xl shadow-xl p-6 sm:p-8 space-y-6 max-h-[90vh] overflow-y-auto">
              <button
                onClick={closeDetail}
                className="absolute top-6 right-6 p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>

              {detailLoading || !patternDetail ? (
                <div className="text-center py-12 space-y-3">
                  <RefreshCw className="w-6 h-6 text-[var(--accent-purple)] animate-spin mx-auto" />
                  <p className="text-[var(--text-muted)] text-sm">Loading pattern diagnosis...</p>
                </div>
              ) : (
                <>
                  <div className="space-y-1">
                    <span className="text-xs font-mono font-bold text-[var(--accent-purple-text)] uppercase">
                      {patternDetail.pattern.skill_id}
                    </span>
                    <h2 className="text-2xl font-bold font-display text-[var(--text-primary)] capitalize">
                      {formatErrorTypeLabel(patternDetail.pattern.error_type)}
                    </h2>
                    <p className="text-[var(--text-muted)] text-xs">
                      Topic: {patternDetail.skill_name}
                    </p>
                  </div>

                  {/* Explainability Box */}
                  <div className="p-4 rounded-xl bg-[var(--bg-subtle)] border border-[var(--border)] space-y-2">
                    <div className="text-xs font-semibold text-[var(--accent-purple-text)] flex items-center gap-1.5">
                      <Info className="w-4 h-4" />
                      Why This Pattern Exists (§37 Explainability):
                    </div>
                    <p className="text-sm text-[var(--text-primary)] leading-relaxed">
                      {patternDetail.explainability}
                    </p>
                  </div>

                  {/* Prerequisite Signal */}
                  {patternDetail.pattern.prerequisite_signal && (
                    <div className="p-4 rounded-xl bg-[var(--accent-yellow-bg)] border border-[var(--accent-yellow-border)] text-[var(--accent-yellow-text)] text-xs space-y-1">
                      <div className="font-semibold text-[var(--accent-yellow-text)]">Prerequisite Relation:</div>
                      <div className="leading-relaxed">{patternDetail.pattern.prerequisite_signal}</div>
                    </div>
                  )}

                  {/* Repair Action */}
                  <div className="p-4 rounded-xl bg-[var(--accent-purple-bg)] border border-[var(--accent-purple-border)] space-y-2">
                    <div className="text-xs font-semibold text-[var(--accent-purple-text)]">
                      Recommended Pedagogical Action:
                    </div>
                    <p className="text-sm text-[var(--text-primary)] leading-relaxed">
                      {patternDetail.recommended_repair.recommended_repair_action}
                    </p>
                  </div>

                  {/* Repair History Ledger */}
                  {patternDetail.repair_history.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-[var(--text-muted)]">
                        Repair Evidence Ledger ({patternDetail.repair_history.length}):
                      </div>
                      <div className="space-y-2">
                        {patternDetail.repair_history.map((rh) => (
                          <div
                            key={rh.id}
                            className="p-3 rounded-lg bg-[var(--accent-green-bg)] border border-[var(--accent-green-border)] text-xs text-[var(--accent-green-text)] flex items-center justify-between"
                          >
                            <div>
                              <div className="font-semibold">{rh.repair_action}</div>
                              <div className="text-[var(--text-muted)]">Source: {rh.evidence_source} • {rh.assistance_level}</div>
                            </div>
                            <div className="text-[var(--text-muted)] font-mono text-[10px]">
                              {new Date(rh.verified_at).toLocaleDateString()}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-end gap-3 pt-4 border-t border-[var(--border)]">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={closeDetail}
                    >
                      Close
                    </Button>

                    <Button
                      variant="ai"
                      size="sm"
                      icon={<GraduationCap className="w-4 h-4" />}
                      onClick={() => {
                        closeDetail();
                        handleReviewWithTutor(patternDetail.pattern.skill_id, patternDetail.skill_name);
                      }}
                    >
                      Review with Socratic Tutor
                    </Button>
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
