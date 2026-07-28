import React, { useState, KeyboardEvent } from 'react';
import { Mic, Send } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
  keyboardShortcuts?: boolean;
  enableDictation?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled, keyboardShortcuts = true, enableDictation = true }) => {
  const [input, setInput] = useState('');
  const [isDictating, setIsDictating] = useState(false);

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (keyboardShortcuts && e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startDictation = () => {
    const SpeechRecognition = (window as typeof window & { SpeechRecognition?: new () => any; webkitSpeechRecognition?: new () => any }).SpeechRecognition
      || (window as typeof window & { webkitSpeechRecognition?: new () => any }).webkitSpeechRecognition;
    if (!SpeechRecognition || disabled) {
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = document.documentElement.lang === 'hi' ? 'hi-IN' : 'en-IN';
    recognition.interimResults = false;
    recognition.onstart = () => setIsDictating(true);
    recognition.onend = () => setIsDictating(false);
    recognition.onerror = () => setIsDictating(false);
    recognition.onresult = (event: any) => setInput((current) => `${current}${current ? ' ' : ''}${event.results[0][0].transcript}`);
    recognition.start();
  };

  return (
    <div className="p-4 bg-surface/80 backdrop-blur-sm border-t border-outline-variant/30">
      <div className="max-w-4xl mx-auto relative flex items-center">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything..."
          disabled={disabled}
          className={`w-full resize-none rounded-2xl bg-surface-container-low px-4 py-3 ${enableDictation ? 'pr-20' : 'pr-12'} text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-1 focus:ring-primary/50 disabled:opacity-50`}
          rows={1}
          style={{ minHeight: '52px', maxHeight: '200px' }}
        />
        {enableDictation ? <button type="button" onClick={startDictation} disabled={disabled} aria-label="Start voice dictation" className={`absolute right-11 p-2 rounded-full transition-colors ${isDictating ? 'bg-primary/15 text-primary' : 'text-on-surface-variant hover:bg-primary/10 hover:text-primary'} disabled:opacity-50`}><Mic size={18} /></button> : null}
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className="absolute right-2 p-2 rounded-full text-primary hover:bg-primary/10 disabled:opacity-50 disabled:hover:bg-transparent transition-colors"
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  );
};
