// ═══════════════════════════════════════════════════════════════
// AI Service — Direct Anthropic API via fetch (no SDK)
// ═══════════════════════════════════════════════════════════════

import { ANTHROPIC_API_URL, DEFAULT_MODEL } from '@/config/constants';
import { SYSTEM_PROMPT } from '@/config/systemPrompt';
import type { Message } from '@/types';

interface AnthropicMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface AnthropicResponse {
  id: string;
  content: { type: string; text: string }[];
  stop_reason: string;
  usage: { input_tokens: number; output_tokens: number };
}

export async function sendMessage(
  messages: Message[],
  apiKey: string,
  modelId: string = DEFAULT_MODEL,
  clinicalContext?: string,
): Promise<string> {
  if (!apiKey) throw new Error('API key is required. Go to Settings to enter your Anthropic API key.');

  const systemContent = clinicalContext
    ? `${SYSTEM_PROMPT}\n\n---\n\nCLINICAL FILE CONTEXT:\n${clinicalContext}`
    : SYSTEM_PROMPT;

  const apiMessages: AnthropicMessage[] = messages.map((m) => ({
    role: m.role,
    content: m.content,
  }));

  const res = await fetch(ANTHROPIC_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    },
    body: JSON.stringify({
      model: modelId,
      max_tokens: 4096,
      system: systemContent,
      messages: apiMessages,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    if (res.status === 401) throw new Error('Invalid API key. Check your key in Settings.');
    if (res.status === 429) throw new Error('Rate limit exceeded. Please wait a moment.');
    throw new Error(`API error (${res.status}): ${err}`);
  }

  const data: AnthropicResponse = await res.json();
  const textBlock = data.content.find((c) => c.type === 'text');
  return textBlock?.text ?? 'I apologize, but I was unable to generate a response. Please try again.';
}
