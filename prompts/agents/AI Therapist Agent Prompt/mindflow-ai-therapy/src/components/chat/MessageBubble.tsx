import type { Message } from '@/types';
import React from 'react';

export const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
  const isUser = message.role === 'user';
  const time = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}
    >
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-primary text-white rounded-br-md'
            : 'bg-white border border-neutral-200 text-neutral-800 rounded-bl-md shadow-sm'
        }`}
      >
        {!isUser && (
          <p className="text-xs font-medium text-primary mb-1">Dr. Alex Morgan</p>
        )}
        <div className="text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
        <p
          className={`text-[10px] mt-1 ${
            isUser ? 'text-white/60' : 'text-neutral-300'
          }`}
        >
          {time}
        </p>
      </div>
    </div>
  );
};
