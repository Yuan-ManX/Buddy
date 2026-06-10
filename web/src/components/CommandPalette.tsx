import React, { useState, useEffect, useRef, useCallback } from 'react';

interface CommandAction {
  id: string;
  label: string;
  description: string;
  category: string;
  action: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  actions: CommandAction[];
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose, actions }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const filtered = query.trim()
    ? actions.filter(
        (a) =>
          a.label.toLowerCase().includes(query.toLowerCase()) ||
          a.description.toLowerCase().includes(query.toLowerCase()) ||
          a.category.toLowerCase().includes(query.toLowerCase())
      )
    : actions;

  // Group filtered results by category
  const grouped: Record<string, CommandAction[]> = {};
  filtered.forEach((a) => {
    if (!grouped[a.category]) grouped[a.category] = [];
    grouped[a.category].push(a);
  });

  // Reset on open
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Keyboard navigation
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (listRef.current) {
      const selected = listRef.current.querySelector('.command-item.selected');
      selected?.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((i) => Math.max(i - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (filtered[selectedIndex]) {
            filtered[selectedIndex].action();
            onClose();
          }
          break;
        case 'Escape':
          onClose();
          break;
      }
    },
    [filtered, selectedIndex, onClose]
  );

  if (!isOpen) return null;

  return (
    <div className="command-overlay" onClick={onClose}>
      <div className="command-palette" onClick={(e) => e.stopPropagation()}>
        <div className="command-input-wrapper">
          <span className="command-search-icon">⌘</span>
          <input
            ref={inputRef}
            className="command-input"
            type="text"
            placeholder="Type a command or search..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <span className="command-hint">esc</span>
        </div>
        <div className="command-results" ref={listRef}>
          {Object.entries(grouped).map(([category, items]) => (
            <div key={category} className="command-group">
              <div className="command-group-label">{category}</div>
              {items.map((item, idx) => {
                const globalIdx = filtered.indexOf(item);
                return (
                  <div
                    key={item.id}
                    className={`command-item ${globalIdx === selectedIndex ? 'selected' : ''}`}
                    onClick={() => {
                      item.action();
                      onClose();
                    }}
                    onMouseEnter={() => setSelectedIndex(globalIdx)}
                  >
                    <span className="command-item-label">{item.label}</span>
                    <span className="command-item-desc">{item.description}</span>
                  </div>
                );
              })}
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="command-empty">No matching commands found.</div>
          )}
        </div>
      </div>
    </div>
  );
};