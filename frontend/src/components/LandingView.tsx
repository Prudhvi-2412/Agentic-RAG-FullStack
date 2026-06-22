import React from 'react';
import { Upload, Sparkles, Database, Search, BookOpen, ArrowRight } from 'lucide-react';

interface LandingViewProps {
  setCurrentView: (view: 'landing' | 'dashboard') => void;
  triggerFileSelect: () => void;
  handleDrag: (e: React.DragEvent) => void;
  handleDrop: (e: React.DragEvent) => void;
  isUploading: boolean;
  uploadStatus: string;
  dragActive: boolean;
}

export const LandingView: React.FC<LandingViewProps> = ({
  setCurrentView,
  triggerFileSelect,
  handleDrag,
  handleDrop,
  isUploading,
  uploadStatus,
  dragActive,
}) => {
  return (
    <div className="flex-1 overflow-y-auto py-12 px-6">
      <div className="max-w-5xl mx-auto flex flex-col items-center">
        
        {/* Hero */}
        <div className="text-center mt-6 mb-12">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 dark:bg-blue-950/45 text-blue-600 dark:text-blue-400 text-xs font-bold mb-6 border border-blue-100 dark:border-blue-900/50 shadow-sm shadow-blue-50 dark:shadow-none">
            <Sparkles className="h-3.5 w-3.5" />
            Intent-Based Agentic Routing System Active
          </div>
          <h2 className="text-5xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100 leading-tight">
            Chat With Your Documents <br />
            <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">Intelligently</span>
          </h2>
          <p className="mt-4 text-lg text-slate-500 dark:text-slate-400 max-w-2xl mx-auto font-medium">
            Upload PDF, Word, or Markdown files and query them with layout-aware visual grounding (transcribing tables, charts, and diagrams), powered by Google Gemini 2.5 and Pinecone.
          </p>
          <div className="mt-8 flex gap-4 justify-center">
            <button 
              onClick={() => setCurrentView('dashboard')}
              className="px-6 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold rounded-xl shadow-lg shadow-blue-200 dark:shadow-none flex items-center gap-2 transition-all hover:-translate-y-0.5"
            >
              Open Workspace Console
              <ArrowRight className="h-4.5 w-4.5" />
            </button>
            <button 
              onClick={triggerFileSelect}
              className="px-6 py-3.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold rounded-xl flex items-center gap-2 shadow-sm transition-all hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <Upload className="h-4 w-4 text-slate-400" />
              Upload Document
            </button>
          </div>
        </div>

        {/* Drag-drop Sandbox Area */}
        <div 
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={triggerFileSelect}
          className={`w-full max-w-3xl rounded-2xl border-2 border-dashed p-10 flex flex-col items-center justify-center transition-all cursor-pointer bg-white dark:bg-slate-900 ${
            dragActive 
              ? 'border-blue-500 dark:border-blue-400 bg-blue-50/55 dark:bg-blue-950/30 scale-[1.01]' 
              : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
          }`}
        >
          
          {isUploading ? (
            <div className="flex flex-col items-center">
              <div className="h-12 w-12 rounded-xl bg-blue-50 dark:bg-blue-950/45 flex items-center justify-center text-blue-600 dark:text-blue-400 pulse-primary mb-4">
                <Upload className="h-6 w-6" />
              </div>
              <h4 className="text-lg font-bold text-slate-800 dark:text-slate-200">{uploadStatus}</h4>
              <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">Please keep this window open</p>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center">
              <div className="h-14 w-14 rounded-2xl bg-blue-50 dark:bg-blue-950/45 flex items-center justify-center text-blue-600 dark:text-blue-400 mb-4 shadow-sm border border-blue-100 dark:border-blue-900/50">
                <Upload className="h-6 w-6" />
              </div>
              <h4 className="text-lg font-bold text-slate-800 dark:text-slate-200">Drag & Drop documents here</h4>
              <p className="text-sm text-slate-400 dark:text-slate-500 mt-1 max-w-sm font-medium">
                Supports PDF (with visual OCR for tables and diagrams), DOCX, TXT, or MD. Max 10MB per file.
              </p>
              <span className="mt-4 text-xs font-semibold text-blue-600 dark:text-blue-400 px-3 py-1 bg-blue-50 dark:bg-blue-950/45 rounded-full border border-blue-100 dark:border-blue-900/50 hover:bg-blue-100/50 dark:hover:bg-blue-900/60 transition-all">
                Browse Files
              </span>
            </div>
          )}
        </div>

        {/* Features section */}
        <div className="mt-20 w-full">
          <div className="text-center mb-10">
            <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100">SaaS Feature Integrations</h3>
            <p className="text-sm text-slate-400 dark:text-slate-500 font-medium">Under the hood of the DocuMind RAG engine</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-all">
              <div className="h-10 w-10 rounded-lg bg-blue-50 dark:bg-blue-950/45 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-4 font-bold">
                <Sparkles className="h-5 w-5" />
              </div>
              <h4 className="font-bold text-slate-800 dark:text-slate-200 mb-2">Intelligent Router</h4>
              <p className="text-xs text-slate-400 dark:text-slate-505 leading-relaxed">
                Zero-shot Gemini classification routes generic chats away from vector search, saving Pinecone query loads.
              </p>
            </div>
            <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-all">
              <div className="h-10 w-10 rounded-lg bg-indigo-50 dark:bg-indigo-950/45 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-4 font-bold">
                <Database className="h-5 w-5" />
              </div>
              <h4 className="font-bold text-slate-800 dark:text-slate-200 mb-2">Pinecone Serverless</h4>
              <p className="text-xs text-slate-400 dark:text-slate-505 leading-relaxed">
                Indexes high-density 768-dimensional text embeddings in namespaces, allowing rapid cosine search matchings.
              </p>
            </div>
            <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-all">
              <div className="h-10 w-10 rounded-lg bg-cyan-50 dark:bg-cyan-950/45 text-cyan-600 dark:text-cyan-400 flex items-center justify-center mb-4 font-bold">
                <Search className="h-5 w-5" />
              </div>
              <h4 className="font-bold text-slate-800 dark:text-slate-200 mb-2">Source Citations</h4>
              <p className="text-xs text-slate-400 dark:text-slate-505 leading-relaxed">
                Every statement retrieved has exact filename tracking and page-level mappings rendered in detail.
              </p>
            </div>
            <div className="p-6 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-all">
              <div className="h-10 w-10 rounded-lg bg-purple-50 dark:bg-purple-950/45 text-purple-600 dark:text-purple-400 flex items-center justify-center mb-4 font-bold">
                <BookOpen className="h-5 w-5" />
              </div>
              <h4 className="font-bold text-slate-800 dark:text-slate-200 mb-2">Multimodal OCR Ingestion</h4>
              <p className="text-xs text-slate-400 dark:text-slate-550 leading-relaxed">
                Converts PDF pages into images to transcribe complex tables into markdown and capture visual chart context using Gemini Vision.
              </p>
            </div>
          </div>
        </div>

        {/* Next-Gen vs Standard LLM Section */}
        <div className="mt-24 w-full pt-16 border-t border-slate-200 dark:border-slate-800/80">
          <div className="text-center mb-12">
            <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Next-Generation Document Intelligence</h3>
            <p className="text-sm text-slate-400 dark:text-slate-500 font-medium max-w-lg mx-auto mt-2">
              Why an optimized custom RAG pipeline outperforms basic document copy-pasting or standard LLM file uploads.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 bg-gradient-to-b from-white to-slate-50/50 dark:from-slate-900 dark:to-slate-950/50 rounded-2xl border border-slate-250 dark:border-slate-800 shadow-sm hover:border-slate-300 dark:hover:border-slate-700 transition-all group">
              <h4 className="font-bold text-slate-800 dark:text-slate-250 mb-2 text-base group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                Parallel Visual Ingestion
              </h4>
              <p className="text-xs text-slate-400 dark:text-slate-500 leading-relaxed">
                Instead of slow sequential readers, DocuMind uses concurrent multi-threaded visual OCR pipelines (up to 8 pages processed in parallel). Page layouts, tables, and charts are transcribed into structured Markdown instantly.
              </p>
            </div>

            <div className="p-6 bg-gradient-to-b from-white to-slate-50/50 dark:from-slate-900 dark:to-slate-950/50 rounded-2xl border border-slate-250 dark:border-slate-800 shadow-sm hover:border-slate-300 dark:hover:border-slate-700 transition-all group">
              <h4 className="font-bold text-slate-800 dark:text-slate-250 mb-2 text-base group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                Hybrid Dense-Sparse RAG
              </h4>
              <p className="text-xs text-slate-400 dark:text-slate-500 leading-relaxed">
                We combine 768-dimensional dense vector embeddings with a local BM25 keyword matching engine. This captures both conceptual intent and exact keyword matches, ranking them with a Gemini-powered Cross-Encoder reranker.
              </p>
            </div>

            <div className="p-6 bg-gradient-to-b from-white to-slate-50/50 dark:from-slate-900 dark:to-slate-950/50 rounded-2xl border border-slate-250 dark:border-slate-800 shadow-sm hover:border-slate-300 dark:hover:border-slate-700 transition-all group">
              <h4 className="font-bold text-slate-800 dark:text-slate-250 mb-2 text-base group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                Interactive Citation Mapping
              </h4>
              <p className="text-xs text-slate-400 dark:text-slate-500 leading-relaxed">
                Every sentence is grounded with physical page numbers. Clicking inline citations (e.g. [1], [2]) in the chat smoothly scrolls the Citations panel and triggers a glowing pulse overlay to highlight the raw source chunk.
              </p>
            </div>

            <div className="p-6 bg-gradient-to-b from-white to-slate-50/50 dark:from-slate-900 dark:to-slate-950/50 rounded-2xl border border-slate-250 dark:border-slate-800 shadow-sm hover:border-slate-300 dark:hover:border-slate-700 transition-all group md:col-span-1">
              <h4 className="font-bold text-slate-800 dark:text-slate-250 mb-2 text-base group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                History-Aware Condensation
              </h4>
              <p className="text-xs text-slate-400 dark:text-slate-500 leading-relaxed">
                DocuMind keeps track of prior conversational turns. Follow-up queries are automatically condensed into standalone questions using Gemini before searching, ensuring full contextual continuity throughout long chat sessions.
              </p>
            </div>

            <div className="p-6 bg-gradient-to-b from-white to-slate-50/50 dark:from-slate-900 dark:to-slate-950/50 rounded-2xl border border-slate-250 dark:border-slate-800 shadow-sm hover:border-slate-300 dark:hover:border-slate-700 transition-all group md:col-span-2">
              <h4 className="font-bold text-slate-800 dark:text-slate-250 mb-2 text-base group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                JWT-Isolated Multi-Tenancy
              </h4>
              <p className="text-xs text-slate-400 dark:text-slate-500 leading-relaxed">
                Unlike public LLMs that share data, DocuMind enforces strict data isolation. Requests are secured with stateless Supabase JWT tokens, restricting Pinecone upserts and vector queries exclusively to your user ID.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
