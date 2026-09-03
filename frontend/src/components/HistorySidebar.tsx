import React from 'react';
import { Plus, Clock, ChevronRight, ChevronLeft, PanelLeftClose, PanelLeftOpen } from 'lucide-react';

interface HistoryItem {
  id: string;
  title: string;
  date: string;
}

interface HistorySidebarProps {
  title: string;
  items: HistoryItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  /** Whether the sidebar is collapsed to a slim toggle strip */
  collapsed?: boolean;
  /** Called when the user clicks the collapse/expand toggle */
  onToggle?: () => void;
}

export default function HistorySidebar({
  title,
  items,
  onSelect,
  selectedId,
  onNew,
  collapsed = false,
  onToggle,
}: HistorySidebarProps) {
  if (collapsed) {
    /* Slim strip — only shows the expand button and a "new" icon */
    return (
      <div className="hidden lg:flex w-12 shrink-0 flex-col items-center border-r border-[var(--border)] bg-[var(--bg-secondary)] py-3 gap-2">
        <button
          type="button"
          onClick={onToggle}
          aria-label={`Expand ${title} panel`}
          className="rounded-lg p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
        >
          <PanelLeftOpen className="h-5 w-5" aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={onNew}
          aria-label={`New ${title}`}
          className="rounded-lg p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
        >
          <Plus className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
    );
  }

  return (
    <div className="hidden lg:flex w-72 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--bg-secondary)] h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--bg-card)] px-4 py-3.5">
        <h2 className="font-display text-sm font-semibold text-[var(--text-primary)]">{title}</h2>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onNew}
            aria-label={`New ${title}`}
            className="rounded-lg p-1.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
          </button>
          {onToggle && (
            <button
              type="button"
              onClick={onToggle}
              aria-label={`Collapse ${title} panel`}
              className="rounded-lg p-1.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            >
              <PanelLeftClose className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {/* History list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => onSelect(item.id)}
            className={`w-full text-left p-3 rounded-xl flex items-start gap-3 transition-all ${
              selectedId === item.id
                ? 'bg-[var(--bg-card)] border border-[var(--border)] shadow-[var(--shadow-sm)]'
                : 'hover:bg-[var(--bg-hover)] border border-transparent'
            }`}
          >
            <Clock className={`w-4 h-4 mt-0.5 shrink-0 ${
              selectedId === item.id ? 'text-[var(--accent-green-text)]' : 'text-[var(--text-muted)]'
            }`} aria-hidden="true" />
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium truncate ${
                selectedId === item.id ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'
              }`}>
                {item.title || 'Untitled'}
              </p>
              <p className="text-[11px] text-[var(--text-muted)] mt-0.5 truncate font-medium uppercase tracking-wider">
                {new Date(item.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </p>
            </div>
            <ChevronRight className={`w-4 h-4 mt-0.5 shrink-0 transition-opacity ${
              selectedId === item.id ? 'opacity-100 text-[var(--text-primary)]' : 'opacity-0'
            }`} aria-hidden="true" />
          </button>
        ))}

        {items.length === 0 && (
          <div className="py-8 px-4 text-center text-sm text-[var(--text-muted)] border border-dashed border-[var(--border)] rounded-xl">
            No history yet
          </div>
        )}
      </div>
    </div>
  );
}
