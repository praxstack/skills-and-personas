import { sendMessage } from '@/services/ai.service';
import { useClinicalFileStore } from '@/stores/clinicalFileStore';
import { useSessionStore } from '@/stores/sessionStore';
import { useUIStore } from '@/stores/uiStore';
import React from 'react';
import { MessageBubble } from './MessageBubble';

export const ChatView: React.FC = () => {
  const { currentSession, startSession, addMessage, setLoading, setError, isLoading, error } =
    useSessionStore();
  const { settings } = useUIStore();
  const clinicalFile = useClinicalFileStore((s) => s.clinicalFile);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const [input, setInput] = React.useState('');

  // Auto-start session if none active
  React.useEffect(() => {
    if (!currentSession) startSession();
  }, [currentSession, startSession]);

  // Auto-scroll to bottom
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentSession?.messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    setInput('');
    addMessage('user', text);
    setLoading(true);
    setError(null);

    try {
      // Build clinical context summary for the AI
      let clinicalContext: string | undefined;
      if (clinicalFile) {
        const parts: string[] = [];
        parts.push(`Client: ${clinicalFile.profile.name}`);
        parts.push(`Intake: ${clinicalFile.intakeApproach}`);
        if (clinicalFile.presentingProblems.length) {
          parts.push(`Problems: ${clinicalFile.presentingProblems.join(', ')}`);
        }
        if (clinicalFile.screeningHistory.length) {
          const latest = clinicalFile.screeningHistory[clinicalFile.screeningHistory.length - 1];
          parts.push(`Latest ${latest.type}: ${latest.totalScore} (${latest.severity})`);
        }
        clinicalContext = parts.join('\n');
      }

      // Get *all* messages from current session (including the one we just added)
      const allMessages = [
        ...(currentSession?.messages ?? []),
        { id: '', role: 'user' as const, content: text, timestamp: Date.now() },
      ];

      const reply = await sendMessage(allMessages, settings.apiKey, settings.modelId, clinicalContext);
      addMessage('assistant', reply);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {(!currentSession || currentSession.messages.length === 0) && (
          <div className="text-center py-20">
            <span className="text-5xl mb-4 block">🧠</span>
            <h2 className="text-2xl font-semibold text-neutral-700 mb-2">
              Welcome to MindFlow
            </h2>
            <p className="text-neutral-400 max-w-md mx-auto leading-relaxed">
              I'm Dr. Alex Morgan, a clinical psychologist specializing in depression,
              ADHD, anxiety, and executive function challenges. Type a message to begin.
            </p>
          </div>
        )}

        {currentSession?.messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="flex items-center gap-2 px-4">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-primary rounded-full animate-pulse" />
              <span className="w-2 h-2 bg-primary rounded-full animate-pulse delay-150" />
              <span className="w-2 h-2 bg-primary rounded-full animate-pulse delay-300" />
            </div>
            <span className="text-sm text-neutral-400">Dr. Morgan is typing…</span>
          </div>
        )}

        {error && (
          <div className="mx-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            ⚠️ {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-neutral-200 bg-white p-4">
        <div className="max-w-3xl mx-auto flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message…"
            rows={1}
            className="flex-1 resize-none border border-neutral-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="px-5 py-3 bg-primary text-white rounded-xl font-medium text-sm hover:bg-primary-dark disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
        {!settings.apiKey && (
          <p className="text-center text-xs text-amber-600 mt-2">
            ⚠️ No API key set.{' '}
            <button
              onClick={() => useUIStore.getState().setView('settings')}
              className="underline hover:text-amber-700"
            >
              Go to Settings
            </button>{' '}
            to add your Anthropic API key.
          </p>
        )}
      </div>
    </div>
  );
};
