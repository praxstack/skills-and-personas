import { StorageService } from '@/services/storage.service';
import { useClinicalFileStore } from '@/stores/clinicalFileStore';
import { useUIStore } from '@/stores/uiStore';
import React from 'react';

export const SettingsView: React.FC = () => {
  const { settings, updateSettings } = useUIStore();
  const resetClinical = useClinicalFileStore((s) => s.reset);
  const [showKey, setShowKey] = React.useState(false);
  const [importStatus, setImportStatus] = React.useState<string | null>(null);
  const fileRef = React.useRef<HTMLInputElement>(null);

  const handleExport = () => {
    const data = StorageService.exportAll();
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mindflow-backup-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const success = StorageService.importData(reader.result as string);
      setImportStatus(success ? '✅ Data imported! Refresh the page to apply.' : '❌ Import failed — invalid file.');
    };
    reader.readAsText(file);
  };

  const handleClearAll = () => {
    if (window.confirm('⚠️ This will permanently delete ALL your data. Export first! Are you sure?')) {
      StorageService.clearAll();
      resetClinical();
      window.location.reload();
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-8">
      <h1 className="text-2xl font-semibold text-neutral-800">Settings</h1>

      {/* API Key */}
      <section className="bg-white border border-neutral-200 rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-neutral-800 mb-1">🔑 Anthropic API Key</h2>
        <p className="text-xs text-neutral-400 mb-4">
          Your key is stored locally and only sent directly to Anthropic's API.
        </p>
        <div className="flex gap-2">
          <input
            type={showKey ? 'text' : 'password'}
            value={settings.apiKey}
            onChange={(e) => updateSettings({ apiKey: e.target.value })}
            placeholder="sk-ant-..."
            className="flex-1 border border-neutral-300 rounded-xl px-4 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button
            onClick={() => setShowKey(!showKey)}
            className="px-3 py-2.5 border border-neutral-300 rounded-xl text-sm hover:bg-neutral-50"
          >
            {showKey ? '🙈' : '👁️'}
          </button>
        </div>
      </section>

      {/* Model */}
      <section className="bg-white border border-neutral-200 rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-neutral-800 mb-1">🤖 AI Model</h2>
        <select
          value={settings.modelId}
          onChange={(e) => updateSettings({ modelId: e.target.value })}
          className="w-full border border-neutral-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
        >
          <option value="claude-sonnet-4-20250514">Claude Sonnet 4</option>
          <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
          <option value="claude-3-haiku-20240307">Claude 3 Haiku (fast)</option>
        </select>
      </section>

      {/* Data Management */}
      <section className="bg-white border border-neutral-200 rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-neutral-800 mb-4">💾 Data Management</h2>
        <div className="space-y-3">
          <button
            onClick={handleExport}
            className="w-full py-2.5 border border-primary text-primary rounded-xl text-sm font-medium hover:bg-primary/5 transition-colors"
          >
            📤 Export All Data (JSON)
          </button>
          <div>
            <button
              onClick={() => fileRef.current?.click()}
              className="w-full py-2.5 border border-neutral-300 rounded-xl text-sm hover:bg-neutral-50 transition-colors"
            >
              📥 Import Data from Backup
            </button>
            <input ref={fileRef} type="file" accept=".json" onChange={handleImport} className="hidden" />
            {importStatus && (
              <p className="text-xs mt-2 text-center">{importStatus}</p>
            )}
          </div>
          <button
            onClick={handleClearAll}
            className="w-full py-2.5 border border-red-300 text-red-600 rounded-xl text-sm font-medium hover:bg-red-50 transition-colors"
          >
            🗑️ Clear All Data
          </button>
        </div>
      </section>

      {/* About */}
      <section className="bg-white border border-neutral-200 rounded-2xl p-6 text-center">
        <p className="text-sm text-neutral-500">
          <strong>MindFlow</strong> v1.0 · AI Therapy Assistant
        </p>
        <p className="text-xs text-neutral-300 mt-1">
          Not a substitute for professional care. In crisis, call 988 or 911.
        </p>
      </section>
    </div>
  );
};
