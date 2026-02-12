import { CRISIS_RESOURCES } from '@/config/constants';
import React from 'react';

export const CrisisBanner: React.FC = () => {
  const [expanded, setExpanded] = React.useState(false);

  return (
    <div className="bg-red-50 border-b border-red-200">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2 flex items-center justify-between text-sm text-red-700 hover:bg-red-100 transition-colors"
      >
        <span className="flex items-center gap-2">
          <span>🆘</span>
          <span className="font-medium">In crisis? Help is available 24/7</span>
        </span>
        <span className="text-xs">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <div className="px-4 pb-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
          {CRISIS_RESOURCES.map((r) => (
            <div
              key={r.name}
              className="flex items-center gap-2 bg-white rounded-lg px-3 py-2 border border-red-100"
            >
              <span className="text-red-500 text-lg">📞</span>
              <div>
                <p className="text-sm font-medium text-neutral-800">{r.name}</p>
                <p className="text-xs text-red-600 font-mono">{r.number}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
