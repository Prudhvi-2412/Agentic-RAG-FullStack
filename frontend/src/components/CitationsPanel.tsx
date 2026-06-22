import React from 'react';
import { BookMarked, Sparkles, CheckCircle2 } from 'lucide-react';
import { SourceCitation } from '../types';

interface CitationsPanelProps {
  currentQueryType: string | null;
  retrievedSources: SourceCitation[];
  isStreaming: boolean;
}

export const CitationsPanel: React.FC<CitationsPanelProps> = ({
  currentQueryType,
  retrievedSources,
  isStreaming,
}) => {
  return (
    <aside className="w-80 border-l border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col h-full overflow-hidden">
      
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex-shrink-0">
        <h3 className="font-bold text-slate-800 dark:text-slate-200 text-sm flex items-center gap-2">
          <BookMarked className="h-4.5 w-4.5 text-blue-600 dark:text-blue-400" />
          Sources & Citations
        </h3>
        <p className="text-[10px] text-slate-400 dark:text-slate-500 font-medium mt-0.5">Retrieved chunks matching query</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        
        {/* Case 1: No query sent yet or general chat */}
        {(!currentQueryType || currentQueryType === 'GENERAL_CHAT') && retrievedSources.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center px-4 py-20">
            <div className="h-12 w-12 rounded-full bg-indigo-50 dark:bg-indigo-950/45 border border-indigo-100 dark:border-indigo-900/50 flex items-center justify-center text-indigo-500 dark:text-indigo-400 mb-3 animate-pulse">
              <Sparkles className="h-5.5 w-5.5" />
            </div>
            {currentQueryType === 'GENERAL_CHAT' ? (
              <>
                <h4 className="text-xs font-bold text-indigo-700 dark:text-indigo-400">Routed: GENERAL_CHAT</h4>
                <p className="text-[10px] text-slate-400 dark:text-slate-500 leading-relaxed mt-2.5">
                  Gemini answered this query directly. Vector lookup was bypassed to optimize latency and database query calls.
                </p>
              </>
            ) : (
              <>
                <h4 className="text-xs font-bold text-slate-500 dark:text-slate-400">Awaiting Query</h4>
                <p className="text-[10px] text-slate-400 dark:text-slate-500 leading-relaxed mt-2">
                  Ask a document-focused question, and retrieved chunks from Pinecone will appear here.
                </p>
              </>
            )}
          </div>
        )}

        {/* Case 2: Document query citations */}
        {currentQueryType === 'DOCUMENT_QUERY' && retrievedSources.length > 0 && (
          <div className="flex flex-col gap-3">
            <div className="p-2.5 bg-blue-50 dark:bg-blue-950/45 border border-blue-100 dark:border-blue-900/50 rounded-lg flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <span className="text-[10px] font-bold text-blue-700 dark:text-blue-400 uppercase tracking-wide">Grounded Attributions Ready</span>
            </div>

            {retrievedSources.map((source) => (
              <div 
                key={source.chunk_id}
                id={`citation-${source.chunk_id}`}
                className="p-3 bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-200 dark:border-slate-850 flex flex-col gap-2 hover:border-blue-400 dark:hover:border-blue-800 transition-all duration-500 shadow-sm ring-offset-2 dark:ring-offset-slate-900"
              >
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-850 pb-1.5">
                  <span className="text-[10px] font-bold text-blue-600 dark:text-blue-400 max-w-[140px] truncate" title={source.filename}>
                    {source.filename}
                  </span>
                  <span className="text-[9px] font-bold px-1.5 py-0.5 bg-slate-200/80 dark:bg-slate-800 rounded-full text-slate-500 dark:text-slate-400">
                    Page {source.page_number || 'N/A'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-slate-350 leading-relaxed italic bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-100 dark:border-slate-800 max-h-36 overflow-y-auto">
                  "{source.context}"
                </p>
                <div className="flex items-center justify-between text-[9px] text-slate-400 dark:text-slate-500 mt-0.5 font-bold">
                  <span>Relevance index</span>
                  <span className="text-emerald-600 dark:text-emerald-550">{(source.relevance_score * 100).toFixed(1)}% match</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Case 3: Document query returned no source */}
        {currentQueryType === 'DOCUMENT_QUERY' && retrievedSources.length === 0 && isStreaming && (
          <div className="flex flex-col gap-2">
            <div className="h-20 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-100 dark:border-slate-800 animate-pulse p-3 flex flex-col gap-2">
              <div className="h-3.5 bg-slate-200 dark:bg-slate-800 rounded w-1/2"></div>
              <div className="h-10 bg-slate-200 dark:bg-slate-800 rounded"></div>
            </div>
            <div className="h-20 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-100 dark:border-slate-800 animate-pulse p-3 flex flex-col gap-2">
              <div className="h-3.5 bg-slate-200 dark:bg-slate-800 rounded w-1/3"></div>
              <div className="h-10 bg-slate-200 dark:bg-slate-800 rounded"></div>
            </div>
          </div>
        )}

      </div>

    </aside>
  );
};
