import React from 'react';
import { Plus, Clock, ChevronRight } from 'lucide-react';

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
}

export default function HistorySidebar({ title, items, onSelect, selectedId, onNew }: HistorySidebarProps) {
  return (
    <div className="hidden lg:flex w-72 border-r border-[var(--border)] bg-[var(--bg-secondary)] flex-col h-full overflow-hidden shrink-0">
      <div className="p-4 border-b border-[var(--border)] flex items-center justify-between bg-[var(--bg-card)]">
        <h2 className="font-display font-semibold text-[var(--text-primary)]">{title}</h2>
        <button 
          onClick={onNew} 
          className="p-1.5 rounded-lg text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] transition-colors"
          title="Create New"
        >
          <Plus className="w-5 h-5" />
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => onSelect(item.id)}
            className={`w-full text-left p-3 rounded-xl flex items-start gap-3 transition-all ${
              selectedId === item.id 
                ? 'bg-[var(--bg-card)] border border-[var(--border)] shadow-sm' 
                : 'hover:bg-[var(--bg-hover)] border border-transparent'
            }`}
          >
            <Clock className={`w-4 h-4 mt-0.5 shrink-0 ${
              selectedId === item.id ? 'text-[var(--accent-green-text)]' : 'text-[var(--text-muted)]'
            }`} />
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium truncate ${
                selectedId === item.id ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'
              }`}>
                {item.title || 'Untitled'}
              </p>
              <p className="text-[11px] text-[var(--text-muted)] mt-1 truncate font-medium uppercase tracking-wider">
                {new Date(item.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </p>
            </div>
            <ChevronRight className={`w-4 h-4 mt-0.5 shrink-0 transition-opacity ${
              selectedId === item.id ? 'opacity-100 text-[var(--text-primary)]' : 'opacity-0'
            }`} />
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
