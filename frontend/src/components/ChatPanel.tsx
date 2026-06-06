import React from 'react';
import { Sparkles, Send, Info } from 'lucide-react';
import { ChatSession } from '../types';

interface ChatPanelProps {
  activeSession: ChatSession;
  currentQueryType: string | null;
  isStreaming: boolean;
  isUploading: boolean;
  currentStreamText: string;
  inputValue: string;
  setInputValue: (value: string) => void;
  handleSendMessage: (e?: React.FormEvent) => void;
  chatBottomRef: React.RefObject<any>;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  activeSession,
  currentQueryType,
  isStreaming,
  isUploading,
  currentStreamText,
  inputValue,
  setInputValue,
  handleSendMessage,
  chatBottomRef,
}) => {
  const messages = activeSession.messages;
  
  return (
    <section className="flex-1 flex flex-col bg-slate-50 dark:bg-slate-950 h-full overflow-hidden">
      
      {/* Chat Header */}
      <div className="px-6 py-3 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-between flex-shrink-0">
        <div>
          <h3 className="font-bold text-slate-800 dark:text-slate-200 text-sm">{activeSession.title}</h3>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500">Gemini Ingress Client Connected</span>
          </div>
        </div>

        {/* Routing Status indicator */}
        {currentQueryType && (
          <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
            currentQueryType === 'DOCUMENT_QUERY'
              ? 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border-blue-100 dark:border-blue-900/50'
              : 'bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 border-indigo-100 dark:border-indigo-900/50'
          }`}>
            <Sparkles className="h-3.5 w-3.5" />
            <span>Route: {currentQueryType}</span>
          </div>
        )}
      </div>

      {/* Conversational Bubbles Area */}
      <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-6">
        {messages.map((msg) => (
          <div 
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-xl rounded-2xl px-5 py-3.5 shadow-sm text-sm border ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white border-blue-600 rounded-tr-none'
                : 'bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 border-slate-200 dark:border-slate-800 rounded-tl-none leading-relaxed'
            }`}>
              {msg.role === 'assistant' ? (
                /* Text layout supporting basic formatting styles */
                <div className="prose prose-sm max-w-none dark:prose-invert text-slate-800 dark:text-slate-200">
                  {msg.text.split('\n').map((paragraph, index) => {
                    if (paragraph.startsWith('- ') || paragraph.startsWith('* ')) {
                      return <li key={index} className="ml-4 list-disc mt-1">{paragraph.substring(2)}</li>;
                    }
                    if (paragraph.startsWith('### ')) {
                      return <h4 key={index} className="text-base font-bold text-slate-900 dark:text-slate-100 mt-3 mb-1">{paragraph.substring(4)}</h4>;
                    }
                    if (paragraph.startsWith('**') && paragraph.endsWith('**')) {
                      return <p key={index} className="font-bold text-slate-800 dark:text-slate-200 mt-2">{paragraph.replace(/\*\*/g, '')}</p>;
                    }
                    return <p key={index} className="mt-2">{paragraph}</p>;
                  })}
                </div>
              ) : (
                <p>{msg.text}</p>
              )}
            </div>
          </div>
        ))}

        {/* Live stream text chunk overlay rendering */}
        {isStreaming && currentStreamText && !messages.find(m => m.text === currentStreamText) && (
          <div className="flex justify-start">
            <div className="max-w-xl rounded-2xl px-5 py-3.5 shadow-sm text-sm border bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 border-slate-200 dark:border-slate-800 rounded-tl-none leading-relaxed">
              <div className="prose prose-sm max-w-none dark:prose-invert text-slate-800 dark:text-slate-200">
                {currentStreamText.split('\n').map((paragraph, index) => {
                  if (paragraph.startsWith('- ') || paragraph.startsWith('* ')) {
                    return <li key={index} className="ml-4 list-disc mt-1">{paragraph.substring(2)}</li>;
                  }
                  return <p key={index} className="mt-2">{paragraph}</p>;
                })}
              </div>
              <span className="inline-block h-3 w-1.5 bg-blue-500 animate-pulse ml-0.5 align-middle"></span>
            </div>
          </div>
        )}

        {/* Thinking/Loading skeleton loader */}
        {isStreaming && !currentStreamText && (
          <div className="flex justify-start">
            <div className="max-w-xs rounded-2xl px-5 py-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-tl-none shadow-sm flex flex-col gap-2">
              <div className="flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500 font-bold mb-1">
                <Sparkles className="h-3.5 w-3.5 text-blue-500 animate-spin" />
                Classifying and routing query...
              </div>
              <div className="h-3 bg-slate-100 dark:bg-slate-800 rounded animate-pulse w-48"></div>
              <div className="h-3 bg-slate-100 dark:bg-slate-800 rounded animate-pulse w-32"></div>
            </div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Floating Input Toolbar */}
      <div className="p-4 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 flex-shrink-0">
        <form onSubmit={handleSendMessage} className="relative flex items-center">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={
              isUploading 
                ? "Indexing in progress..." 
                : "Ask a question about meditations, machine learning, or general topics..."
            }
            disabled={isStreaming || isUploading}
            className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl py-3.5 pl-4 pr-12 text-sm text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 dark:focus:ring-blue-900/30 transition-all font-medium disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isStreaming || isUploading}
            className="absolute right-3 p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-all disabled:opacity-40 disabled:bg-slate-300 disabled:pointer-events-none"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
        <div className="flex items-center justify-between mt-2.5 px-1.5">
          <div className="flex items-center gap-1 text-[10px] font-semibold text-slate-400 dark:text-slate-500">
            <Info className="h-3.5 w-3.5" />
            <span>Gemini Agent routes query to avoid redundant Vector lookups.</span>
          </div>
          <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500">Press Enter to send</span>
        </div>
      </div>
    </section>
  );
};
