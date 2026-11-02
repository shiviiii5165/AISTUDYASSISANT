import React, { useState, useEffect } from 'react';
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
  ShieldCheck,
  AlertCircle,
  Compass
} from 'lucide-react';
import { masteryApi } from '../lib/masteryApi';
import type {
  SubjectGraphView,
  SkillNodeView,
  LearningRecommendation,
  MasteryState,
  ReadinessState,
  ReviewStatus
} from '../types/mastery';

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
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5" /> Secure
          </span>
        );
      case 'DEVELOPING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-100 text-sky-800 dark:bg-sky-950/60 dark:text-sky-300 border border-sky-300 dark:border-sky-800">
            <Clock className="w-3.5 h-3.5" /> Developing
          </span>
        );
      case 'FRAGILE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
            <AlertTriangle className="w-3.5 h-3.5" /> Fragile Retention
          </span>
        );
      case 'NEEDS_REPAIR':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-300 dark:border-rose-800">
            <AlertCircle className="w-3.5 h-3.5" /> Needs Repair
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
            <Circle className="w-3.5 h-3.5" /> Not Assessed
          </span>
        );
    }
  };

  const getReadinessBadge = (readiness: ReadinessState) => {
    switch (readiness) {
      case 'BLOCKED_BY_PREREQUISITE':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-600 dark:text-rose-400">
            <Lock className="w-3.5 h-3.5" /> Prerequisite Blocked
          </span>
        );
      case 'READY':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" /> Ready for Learning
          </span>
        );
      case 'PARTIALLY_READY':
        return (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400">
            <AlertTriangle className="w-3.5 h-3.5" /> Prerequisites Developing
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 dark:text-slate-400">
            <HelpCircle className="w-3.5 h-3.5" /> Needs Prerequisite Evidence
          </span>
        );
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* ── HEADER ── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 font-semibold text-sm tracking-wide uppercase">
            <GitBranch className="w-4 h-4" />
            <span>Mastery & Prerequisite Knowledge Graph</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
            Mastery Map
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-0.5">
            Explainable prerequisite tracking and concept mastery. Labels learning state, not student ability.
          </p>
        </div>

        <button
          onClick={() => fetchGraph(selectedSubject)}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Graph
        </button>
      </div>

      {/* ── SUBJECT TABS ── */}
      <div className="flex overflow-x-auto gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
        {SUBJECTS.map((subj) => (
          <button
            key={subj}
            onClick={() => setSelectedSubject(subj)}
            className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition ${
              selectedSubject === subj
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            {subj}
          </button>
        ))}
      </div>

      {/* ── SUMMARY STATS BAR ── */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">Secure</div>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{secureCount}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Verified independent</div>
        </div>
        <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">Developing</div>
          <div className="text-2xl font-bold text-sky-600 dark:text-sky-400 mt-1">{developingCount}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Progressing</div>
        </div>
        <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">Needs Repair</div>
          <div className="text-2xl font-bold text-rose-600 dark:text-rose-400 mt-1">{repairCount}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Foundational gaps</div>
        </div>
        <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">Blocked Concepts</div>
          <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">{blockedCount}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Prerequisite unmet</div>
        </div>
        <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">Not Assessed</div>
          <div className="text-2xl font-bold text-slate-600 dark:text-slate-400 mt-1">{notAssessedCount}</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Awaiting evidence</div>
        </div>
      </div>

      {/* ── RECOMMENDATIONS BANNER ── */}
      {graphData?.recommendations && graphData.recommendations.length > 0 && (
        <div className="rounded-xl p-4 bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-900/50 space-y-3">
          <div className="flex items-center gap-2 text-indigo-900 dark:text-indigo-200 font-semibold text-sm">
            <Compass className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            <span>Recommended Learning Sequence</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {graphData.recommendations.slice(0, 2).map((rec, i) => (
              <div
                key={i}
                onClick={() => {
                  const node = nodes.find((n) => n.skill_id === rec.skill_id);
                  if (node) setSelectedNode(node);
                }}
                className="cursor-pointer p-3 bg-white dark:bg-slate-900 rounded-lg border border-indigo-100 dark:border-indigo-950 shadow-sm hover:border-indigo-300 dark:hover:border-indigo-800 transition"
              >
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span
                    className={
                      rec.priority === 1
                        ? 'text-rose-600 dark:text-rose-400'
                        : 'text-indigo-600 dark:text-indigo-400'
                    }
                  >
                    {rec.priority === 1 ? 'Priority Repair' : 'Next Concept'}
                  </span>
                  <span className="text-slate-400 font-normal">{rec.skill_id}</span>
                </div>
                <div className="font-medium text-slate-900 dark:text-slate-100 text-sm mt-1">
                  {rec.skill_name}
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 leading-relaxed">
                  {rec.reason}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── MAIN CONTENT: DUAL COLUMN (GRAPH / LIST + EXPLAINABILITY DRAWER) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Conceptual Progression List/Chain */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
              {selectedSubject} Concept Curriculum Chain
            </h2>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {nodes.length} concepts mapped
            </span>
          </div>

          {loading ? (
            <div className="p-12 text-center text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
              Loading prerequisite topology...
            </div>
          ) : nodes.length === 0 ? (
            <div className="p-12 text-center text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800">
              No skills defined for {selectedSubject}.
            </div>
          ) : (
            <div className="space-y-2.5">
              {nodes.map((node) => {
                const isSelected = selectedNode?.skill_id === node.skill_id;
                return (
                  <div
                    key={node.skill_id}
                    onClick={() => setSelectedNode(node)}
                    className={`cursor-pointer p-4 rounded-xl border transition flex items-center justify-between gap-4 ${
                      isSelected
                        ? 'border-indigo-500 bg-indigo-50/40 dark:bg-indigo-950/30 dark:border-indigo-500 shadow-sm'
                        : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                    }`}
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-mono font-medium text-slate-400 dark:text-slate-500">
                          {node.skill_code}
                        </span>
                        <span className="text-xs text-slate-400">•</span>
                        <span className="text-xs text-slate-500 dark:text-slate-400 capitalize">
                          {node.grade_band}
                        </span>
                        {node.topic && (
                          <>
                            <span className="text-xs text-slate-400">•</span>
                            <span className="text-xs text-slate-500 dark:text-slate-400">
                              {node.topic}
                            </span>
                          </>
                        )}
                      </div>
                      <div className="font-semibold text-slate-900 dark:text-slate-100 text-sm truncate">
                        {node.skill_name}
                      </div>
                      <div className="pt-0.5">{getReadinessBadge(node.readiness_state)}</div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <div>{getMasteryBadge(node.mastery_state)}</div>
                      <ChevronRight
                        className={`w-4 h-4 text-slate-400 transition-transform ${
                          isSelected ? 'transform translate-x-0.5 text-indigo-500' : ''
                        }`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Explainability & Prerequisite Detail Drawer */}
        <div className="lg:col-span-1">
          {selectedNode ? (
            <div className="sticky top-6 p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4 shadow-sm">
              <div>
                <div className="text-xs font-mono text-indigo-600 dark:text-indigo-400 uppercase tracking-wider font-semibold">
                  {selectedNode.skill_code}
                </div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white mt-1">
                  {selectedNode.skill_name}
                </h3>
                {selectedNode.description && (
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 leading-relaxed">
                    {selectedNode.description}
                  </p>
                )}
              </div>

              <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 dark:text-slate-400">Mastery State</span>
                  <div>{getMasteryBadge(selectedNode.mastery_state)}</div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 dark:text-slate-400">Readiness</span>
                  <div>{getReadinessBadge(selectedNode.readiness_state)}</div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 dark:text-slate-400">Freshness</span>
                  <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                    {selectedNode.review_status === 'FRESH'
                      ? 'Recently Validated'
                      : selectedNode.review_status === 'REVIEW_SOON'
                      ? 'Review Recommended'
                      : 'Reassessment Due'}
                  </span>
                </div>
              </div>

              {/* Explainability Section (§29) */}
              <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-200/80 dark:border-slate-800 space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
                  <Info className="w-3.5 h-3.5 text-indigo-500" />
                  <span>Why This State?</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  {selectedNode.why}
                </p>
              </div>

              {/* Next Pedagogical Action */}
              <div className="p-3 bg-indigo-50/50 dark:bg-indigo-950/20 rounded-lg border border-indigo-100 dark:border-indigo-950 space-y-1">
                <div className="text-xs font-semibold text-indigo-900 dark:text-indigo-300">
                  Recommended Action
                </div>
                <p className="text-xs text-indigo-800 dark:text-indigo-400 leading-relaxed">
                  {selectedNode.next_action}
                </p>
              </div>

              {/* Prerequisites Chain */}
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-2">
                <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Required Prerequisites
                </div>
                {selectedNode.prerequisites.length === 0 ? (
                  <div className="text-xs text-slate-500">None (Foundational concept)</div>
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
                          className={`p-2 rounded text-xs flex items-center justify-between cursor-pointer border ${
                            isBlocking
                              ? 'border-rose-300 bg-rose-50/50 dark:bg-rose-950/20 dark:border-rose-900 text-rose-700 dark:text-rose-300'
                              : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'
                          }`}
                        >
                          <span className="font-medium truncate">
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
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-2">
                <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Unlocks Dependent Topics
                </div>
                {selectedNode.dependents.length === 0 ? (
                  <div className="text-xs text-slate-500">None (Advanced terminal concept)</div>
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
                          className="p-2 rounded text-xs flex items-center justify-between cursor-pointer border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800"
                        >
                          <span className="font-medium truncate">
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
                <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-1.5">
                  <div className="text-xs font-semibold text-rose-600 dark:text-rose-400 flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Prerequisite Repair Path</span>
                  </div>
                  <div className="text-xs text-slate-600 dark:text-slate-400">
                    Recommended starting sequence:
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
                            className="px-2 py-1 rounded bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900 text-xs font-medium hover:bg-rose-100 transition"
                          >
                            {rNode?.skill_name || rId}
                          </button>
                          {idx < graphData.repair_paths[selectedNode.skill_id].length - 1 && (
                            <ArrowRight className="w-3 h-3 text-slate-400" />
                          )}
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-slate-400 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 text-xs">
              Select any concept in the curriculum chain to view explainable evidence and prerequisite relationships.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
