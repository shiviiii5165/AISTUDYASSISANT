import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  GitBranch,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Lock,
  Circle,
  HelpCircle,
  ArrowRight,
  RefreshCw,
  Info,
  ChevronRight,
  Compass,
  AlertCircle,
  Layers,
  Sparkles
} from 'lucide-react';
import { masteryApi } from '../lib/masteryApi';
import type {
  SubjectGraphView,
  SkillNodeView,
  MasteryState,
  ReadinessState
} from '../types/mastery';
import { Card, Button, Badge, MetricCard } from '../components/ui';
import { pageTransition, staggerContainer, staggerItem } from '../lib/motion';

const SUBJECTS = [
  'Mathematics',
  'Physics',
  'Chemistry',
  'Biology',
  'Computer Science'
];

export const MasteryMapPage: React.FC = () => {
  const [selectedSubject, setSelectedSubject] = useState<string>('Mathematics');
  const [graphData, setGraphData] = useState<SubjectGraphView | null>(null);
  const [selectedNode, setSelectedNode] = useState<SkillNodeView | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGraph = async (subject: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await masteryApi.getSubjectGraph(subject);
      setGraphData(data);
      if (data.nodes.length > 0 && !selectedNode) {
        setSelectedNode(data.nodes[0]);
      } else if (selectedNode) {
        // Refresh selected node state
        const refreshed = data.nodes.find((n) => n.skill_id === selectedNode.skill_id);
        if (refreshed) setSelectedNode(refreshed);
      }
    } catch (err: any) {
      console.error('Failed to load mastery graph:', err);
      setError('Could not load knowledge graph for this subject. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph(selectedSubject);
  }, [selectedSubject]);

  // Compute summary stats
  const nodes = graphData?.nodes || [];
  const secureCount = nodes.filter((n) => n.mastery_state === 'SECURE').length;
  const developingCount = nodes.filter((n) => n.mastery_state === 'DEVELOPING').length;
  const repairCount = nodes.filter((n) => n.mastery_state === 'NEEDS_REPAIR').length;
  const blockedCount = nodes.filter((n) => n.readiness_state === 'BLOCKED_BY_PREREQUISITE').length;
  const notAssessedCount = nodes.filter((n) => n.mastery_state === 'NOT_ASSESSED').length;

  const getMasteryBadge = (state: MasteryState) => {
    switch (state) {
      case 'SECURE':
        return (
          <Badge tone="green" dot>
            Secure
          </Badge>
        );
      case 'DEVELOPING':
        return (
          <Badge tone="sky" dot>
            Developing
          </Badge>
        );
      case 'FRAGILE':
        return (
          <Badge tone="yellow" dot>
            Fragile Retention
          </Badge>
        );
      case 'NEEDS_REPAIR':
        return (
          <Badge tone="red" dot>
            Needs Repair
          </Badge>
        );
      default:
        return (
          <Badge tone="neutral" dot>
            Not Assessed
          </Badge>
        );
    }
  };

  const getReadinessBadge = (readiness: ReadinessState) => {
    switch (readiness) {
      case 'BLOCKED_BY_PREREQUISITE':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--accent-red-text)]">
            <Lock className="w-3.5 h-3.5" /> Prerequisite Blocked
          </span>
        );
      case 'READY':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--accent-green-text)]">
            <CheckCircle2 className="w-3.5 h-3.5" /> Ready for Learning
          </span>
        );
      case 'PARTIALLY_READY':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--accent-yellow-text)]">
            <AlertTriangle className="w-3.5 h-3.5" /> Prerequisites Developing
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-[var(--text-muted)]">
            <HelpCircle className="w-3.5 h-3.5" /> Needs Evidence
          </span>
        );
    }
  };

  return (
    <motion.div
      variants={pageTransition}
      initial="initial"
      animate="animate"
      exit="exit"
      className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8 font-sans"
    >
      {/* ── HEADER ── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-[var(--border)]">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Badge tone="teal" dot>
              Mastery Intelligence Engine
            </Badge>
            <span className="text-xs text-[var(--text-muted)]">Prerequisite Topology</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] tracking-tight">
            Knowledge Mastery Map
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Explainable prerequisite tracking and concept mastery. Evaluates conceptual state, not student worth.
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => fetchGraph(selectedSubject)}
          disabled={loading}
          className="flex items-center gap-2 self-start md:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Graph</span>
        </Button>
      </div>

      {/* ── SUBJECT TABS ── */}
      <div className="flex overflow-x-auto gap-2 pb-2 scrollbar-none">
        {SUBJECTS.map((subj) => (
          <button
            key={subj}
            onClick={() => setSelectedSubject(subj)}
            className={`px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold whitespace-nowrap transition shadow-xs ${
              selectedSubject === subj
                ? 'bg-[var(--brand-primary)] text-white shadow-sm ring-2 ring-[var(--brand-soft)]'
                : 'bg-white border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'
            }`}
          >
            {subj}
          </button>
        ))}
      </div>

      {/* ── SUMMARY STATS BAR ── */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
        <MetricCard
          label="Secure"
          value={secureCount}
          subtitle="Verified independent"
          tone="green"
          icon={<CheckCircle2 className="w-5 h-5" />}
        />
        <MetricCard
          label="Developing"
          value={developingCount}
          subtitle="Progressing actively"
          tone="sky"
          icon={<Clock className="w-5 h-5" />}
        />
        <MetricCard
          label="Needs Repair"
          value={repairCount}
          subtitle="Foundational gaps"
          tone="red"
          icon={<AlertCircle className="w-5 h-5" />}
        />
        <MetricCard
          label="Blocked Concepts"
          value={blockedCount}
          subtitle="Prerequisites unmet"
          tone="yellow"
          icon={<Lock className="w-5 h-5" />}
        />
        <MetricCard
          label="Not Assessed"
          value={notAssessedCount}
          subtitle="Awaiting evidence"
          tone="neutral"
          icon={<Circle className="w-5 h-5" />}
        />
      </div>

      {/* ── RECOMMENDATIONS BANNER ── */}
      {graphData?.recommendations && graphData.recommendations.length > 0 && (
        <Card variant="elevated" className="card-3d p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Badge tone="purple" dot>
              AI Pedagogical Recommendations
            </Badge>
            <span className="text-xs text-[var(--text-muted)]">Next Step Guidance</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-1">
            {graphData.recommendations.slice(0, 2).map((rec, i) => (
              <div
                key={i}
                onClick={() => {
                  const node = nodes.find((n) => n.skill_id === rec.skill_id);
                  if (node) setSelectedNode(node);
                }}
                className="cursor-pointer p-4 bg-white rounded-xl border border-[var(--border)] hover:border-[var(--brand-primary)]/50 hover:bg-[var(--bg-hover)] transition shadow-xs space-y-1.5"
              >
                <div className="flex items-center justify-between text-xs">
                  <Badge tone={rec.priority === 1 ? 'red' : 'blue'}>
                    {rec.priority === 1 ? 'Priority Repair' : 'Recommended Next'}
                  </Badge>
                  <span className="text-[var(--text-muted)] font-mono text-[11px]">{rec.skill_id}</span>
                </div>
                <div className="font-semibold text-[var(--text-primary)] text-sm">
                  {rec.skill_name}
                </div>
                <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                  {rec.reason}
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* ── MAIN CONTENT: DUAL COLUMN (GRAPH / LIST + EXPLAINABILITY DRAWER) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Conceptual Progression List/Chain */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">
              {selectedSubject} Concept Progression Chain
            </h2>
            <span className="text-xs text-[var(--text-muted)] font-medium">
              {nodes.length} concepts mapped
            </span>
          </div>

          {loading ? (
            <Card variant="default" className="p-12 text-center text-[var(--text-muted)]">
              <RefreshCw className="w-7 h-7 animate-spin mx-auto mb-3 text-[var(--brand-primary)]" />
              <p className="text-sm font-medium text-[var(--text-secondary)]">Loading prerequisite topology...</p>
            </Card>
          ) : nodes.length === 0 ? (
            <Card variant="default" className="p-12 text-center text-[var(--text-muted)]">
              <Layers className="w-8 h-8 mx-auto mb-2 text-[var(--text-disabled)]" />
              <p className="text-sm font-medium text-[var(--text-secondary)]">No skills defined for {selectedSubject}.</p>
            </Card>
          ) : (
            <div className="space-y-2.5">
              {nodes.map((node) => {
                const isSelected = selectedNode?.skill_id === node.skill_id;
                return (
                  <motion.div
                    key={node.skill_id}
                    onClick={() => setSelectedNode(node)}
                    whileHover={{ y: -1 }}
                    className={`cursor-pointer p-4 rounded-xl border transition-all flex items-center justify-between gap-4 shadow-xs ${
                      isSelected
                        ? 'border-[var(--brand-primary)] bg-[var(--brand-light)] ring-1 ring-[var(--brand-soft)] shadow-sm'
                        : 'border-[var(--border)] bg-white hover:border-[var(--brand-primary)]/40 hover:bg-[var(--bg-hover)]'
                    }`}
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-mono font-medium text-[var(--text-muted)]">
                          {node.skill_code}
                        </span>
                        <span className="text-xs text-[var(--text-disabled)]">•</span>
                        <span className="text-xs text-[var(--text-secondary)] capitalize font-medium">
                          {node.grade_band}
                        </span>
                        {node.topic && (
                          <>
                            <span className="text-xs text-[var(--text-disabled)]">•</span>
                            <span className="text-xs text-[var(--text-muted)]">
                              {node.topic}
                            </span>
                          </>
                        )}
                      </div>
                      <div className="font-semibold text-[var(--text-primary)] text-sm truncate">
                        {node.skill_name}
                      </div>
                      <div className="pt-0.5">{getReadinessBadge(node.readiness_state)}</div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <div>{getMasteryBadge(node.mastery_state)}</div>
                      <ChevronRight
                        className={`w-4 h-4 text-[var(--text-muted)] transition-transform ${
                          isSelected ? 'transform translate-x-0.5 text-[var(--brand-primary)]' : ''
                        }`}
                      />
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Explainability & Prerequisite Detail Drawer */}
        <div className="lg:col-span-1">
          {selectedNode ? (
            <Card variant="elevated" className="card-3d sticky top-6 p-5 sm:p-6 space-y-4">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-[var(--brand-primary)] uppercase tracking-wider font-semibold">
                    {selectedNode.skill_code}
                  </span>
                  <Badge tone="neutral" size="xs">
                    {selectedNode.grade_band}
                  </Badge>
                </div>
                <h3 className="text-base sm:text-lg font-bold text-[var(--text-primary)] mt-1.5 leading-snug">
                  {selectedNode.skill_name}
                </h3>
                {selectedNode.description && (
                  <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                    {selectedNode.description}
                  </p>
                )}
              </div>

              <div className="pt-3 border-t border-[var(--border)] space-y-2.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[var(--text-muted)] font-medium">Mastery State</span>
                  <div>{getMasteryBadge(selectedNode.mastery_state)}</div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[var(--text-muted)] font-medium">Readiness</span>
                  <div>{getReadinessBadge(selectedNode.readiness_state)}</div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[var(--text-muted)] font-medium">Freshness</span>
                  <span className="text-xs font-semibold text-[var(--text-secondary)]">
                    {selectedNode.review_status === 'FRESH'
                      ? 'Recently Validated'
                      : selectedNode.review_status === 'REVIEW_SOON'
                      ? 'Review Recommended'
                      : 'Reassessment Due'}
                  </span>
                </div>
              </div>

              {/* Explainability Section */}
              <div className="p-3.5 bg-[var(--bg-subtle)] rounded-xl border border-[var(--border)] space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-[var(--text-primary)]">
                  <Info className="w-3.5 h-3.5 text-[var(--brand-primary)]" />
                  <span>Why This State?</span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                  {selectedNode.why}
                </p>
              </div>

              {/* Next Pedagogical Action */}
              <div className="p-3.5 bg-[var(--brand-light)] rounded-xl border border-[var(--brand-soft)] space-y-1">
                <div className="text-xs font-semibold text-[var(--brand-primary)]">
                  Recommended Action
                </div>
                <p className="text-xs text-[var(--text-primary)] leading-relaxed font-medium">
                  {selectedNode.next_action}
                </p>
              </div>

              {/* Prerequisites Chain */}
              <div className="pt-3 border-t border-[var(--border)] space-y-2">
                <div className="text-xs font-bold text-[var(--text-primary)] uppercase tracking-wider">
                  Required Prerequisites
                </div>
                {selectedNode.prerequisites.length === 0 ? (
                  <div className="text-xs text-[var(--text-muted)]">None (Foundational concept)</div>
                ) : (
                  <div className="space-y-1.5">
                    {selectedNode.prerequisites.map((pid) => {
                      const pNode = nodes.find((n) => n.skill_id === pid);
                      const isBlocking = selectedNode.blocking_prerequisites.includes(pid);
                      return (
                        <div
                          key={pid}
                          onClick={() => {
                            if (pNode) setSelectedNode(pNode);
                          }}
                          className={`p-2.5 rounded-xl text-xs flex items-center justify-between cursor-pointer border transition shadow-xs ${
                            isBlocking
                              ? 'border-[#FCE6BD] bg-[var(--accent-yellow-light)] text-[var(--accent-yellow-text)] font-medium'
                              : 'border-[var(--border)] bg-white hover:bg-[var(--bg-hover)] text-[var(--text-primary)]'
                          }`}
                        >
                          <span className="font-semibold truncate pr-2">
                            {pNode?.skill_name || pid}
                          </span>
                          {pNode && getMasteryBadge(pNode.mastery_state)}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Unblocks Dependent Skills */}
              <div className="pt-3 border-t border-[var(--border)] space-y-2">
                <div className="text-xs font-bold text-[var(--text-primary)] uppercase tracking-wider">
                  Unlocks Dependent Topics
                </div>
                {selectedNode.dependents.length === 0 ? (
                  <div className="text-xs text-[var(--text-muted)]">None (Advanced terminal concept)</div>
                ) : (
                  <div className="space-y-1.5">
                    {selectedNode.dependents.map((did) => {
                      const dNode = nodes.find((n) => n.skill_id === did);
                      return (
                        <div
                          key={did}
                          onClick={() => {
                            if (dNode) setSelectedNode(dNode);
                          }}
                          className="p-2.5 rounded-xl text-xs flex items-center justify-between cursor-pointer border border-[var(--border)] bg-white hover:bg-[var(--bg-hover)] text-[var(--text-primary)] transition shadow-xs"
                        >
                          <span className="font-semibold truncate pr-2">
                            {dNode?.skill_name || did}
                          </span>
                          {dNode && getMasteryBadge(dNode.mastery_state)}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Repair Path (if blocked) */}
              {graphData?.repair_paths && graphData.repair_paths[selectedNode.skill_id] && (
                <div className="pt-3 border-t border-[var(--border)] space-y-2">
                  <div className="text-xs font-semibold text-[var(--accent-red-text)] flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Prerequisite Repair Sequence</span>
                  </div>
                  <div className="text-xs text-[var(--text-muted)]">
                    Recommended starting repair:
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    {graphData.repair_paths[selectedNode.skill_id].map((rId, idx) => {
                      const rNode = nodes.find((n) => n.skill_id === rId);
                      return (
                        <React.Fragment key={rId}>
                          <button
                            onClick={() => {
                              if (rNode) setSelectedNode(rNode);
                            }}
                            className="px-2.5 py-1 rounded-lg bg-[var(--accent-yellow-light)] text-[var(--accent-yellow-text)] border border-[#FCE6BD] text-xs font-medium hover:bg-[var(--accent-yellow-soft)] transition"
                          >
                            {rNode?.skill_name || rId}
                          </button>
                          {idx < graphData.repair_paths[selectedNode.skill_id].length - 1 && (
                            <ArrowRight className="w-3 h-3 text-[var(--text-muted)]" />
                          )}
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>
              )}
            </Card>
          ) : (
            <Card variant="default" className="p-8 text-center text-[var(--text-muted)] text-xs">
              <Compass className="w-8 h-8 mx-auto mb-2 text-[var(--text-disabled)]" />
              Select any concept in the curriculum chain to view explainable evidence and prerequisite relationships.
            </Card>
          )}
        </div>
      </div>
    </motion.div>
  );
};
