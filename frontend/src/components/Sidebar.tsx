import React from 'react';
import { Upload, MessageSquare, FileText, Trash2, Settings, Sparkles } from 'lucide-react';
import { ChatSession, DocumentItem } from '../types';

interface SidebarProps {
  isUploading: boolean;
  uploadStatus: string;
  triggerFileSelect: () => void;
  chatSessions: ChatSession[];
  activeSessionId: string;
  setActiveSessionId: (id: string) => void;
  createNewSession: () => void;
  documents: DocumentItem[];
  activeFilters: string[];
  toggleFilter: (filename: string) => void;
  deleteDocument: (id: string, name: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isUploading,
  uploadStatus,
  triggerFileSelect,
  chatSessions,
  activeSessionId,
  setActiveSessionId,
  createNewSession,
  documents,
  activeFilters,
  toggleFilter,
  deleteDocument,
}) => {
  return (
    <aside className="w-80 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col h-full">
      {/* Upload widget */}
      <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex-shrink-0">
        <button
          onClick={triggerFileSelect}
          disabled={isUploading}
          className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold rounded-xl shadow-md flex items-center justify-center gap-2 transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:pointer-events-none"
        >
          {isUploading ? (
            <>
              <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>Uploading...</span>
            </>
          ) : (
            <>
              <Upload className="h-4.5 w-4.5" />
              <span>Ingest Document</span>
            </>
          )}
        </button>
        {isUploading && (
          <div className="mt-2.5 p-2 bg-slate-50 dark:bg-slate-950 rounded-lg border border-slate-100 dark:border-slate-800 text-center">
            <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 flex items-center justify-center gap-1.5">
              <Sparkles className="h-3 w-3 animate-pulse" />
              {uploadStatus}
            </p>
          </div>
        )}
      </div>

      {/* Lists */}
      <div className="flex-1 overflow-y-auto px-3 py-4 flex flex-col gap-6">
        {/* Chat Sessions list */}
        <div>
          <div className="flex items-center justify-between px-2 mb-2">
            <span className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Conversations</span>
            <button 
              onClick={createNewSession}
              className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950/40 px-2 py-1 rounded transition-all"
            >
              + New
            </button>
          </div>
          <div className="flex flex-col gap-1">
            {chatSessions.map((session) => (
              <button
                key={session.id}
                onClick={() => setActiveSessionId(session.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left text-sm font-medium transition-all ${
                  activeSessionId === session.id 
                    ? 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 font-bold' 
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/40'
                }`}
              >
                <MessageSquare className="h-4.5 w-4.5 flex-shrink-0" />
                <span className="truncate flex-1">{session.title}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Document Library list */}
        <div>
          <div className="px-2 mb-1 flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Document Index</span>
            <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 px-2 py-0.5 bg-slate-100 dark:bg-slate-800 rounded-full">
              {documents.length}
            </span>
          </div>
          <p className="text-[9px] text-slate-400 dark:text-slate-500 px-2 mb-2 font-medium">Select files to filter query context (or leave empty to search all)</p>
          
          <div className="flex flex-col gap-1.5">
            {documents.map((doc) => {
              const isSelected = activeFilters.includes(doc.name);
              return (
                <div 
                  key={doc.id}
                  onClick={() => toggleFilter(doc.name)}
                  className={`group flex items-center justify-between p-2.5 rounded-xl border transition-all cursor-pointer ${
                    isSelected 
                      ? 'border-blue-300 dark:border-blue-800 bg-blue-50/70 dark:bg-blue-950/30' 
                      : 'border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 hover:bg-slate-100/50 dark:hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate flex-1 mr-2">
                    <input 
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleFilter(doc.name)}
                      onClick={(e) => e.stopPropagation()}
                      className="h-3.5 w-3.5 rounded text-blue-600 focus:ring-blue-500 border-slate-300 dark:border-slate-700 dark:bg-slate-800 cursor-pointer"
                    />
                    <FileText className={`h-4 w-4 flex-shrink-0 ${isSelected ? 'text-blue-600' : 'text-blue-500'}`} />
                    <div className="truncate">
                      <p className={`text-xs font-bold truncate ${isSelected ? 'text-blue-900 dark:text-blue-300' : 'text-slate-700 dark:text-slate-300'}`}>{doc.name}</p>
                      <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500">{doc.chunksCount} vectors</p>
                    </div>
                  </div>
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteDocument(doc.id, doc.name);
                    }}
                    className="p-1 text-slate-300 dark:text-slate-655 hover:text-red-500 rounded hover:bg-white dark:hover:bg-slate-800 transition-all shadow-sm opacity-0 group-hover:opacity-100 flex-shrink-0"
                    title="Delete index mapping"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Sidebar Footer */}
      <div className="p-4 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-full bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-xs">
            AI
          </div>
          <div>
            <p className="text-xs font-bold text-slate-700 dark:text-slate-300">Developer Mode</p>
            <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500">Local Sandbox</p>
          </div>
        </div>
        <button 
          onClick={() => alert("DocuMind AI configurations are pre-defined using settings.py and the local .env setup.")}
          className="p-1.5 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg transition-all"
        >
          <Settings className="h-4.5 w-4.5" />
        </button>
      </div>
    </aside>
  );
};
