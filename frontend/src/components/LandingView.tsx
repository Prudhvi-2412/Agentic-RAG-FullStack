import React from 'react';
import { Upload, Sparkles, Database, Search, BookOpen, ArrowRight } from 'lucide-react';

interface LandingViewProps {
  setCurrentView: (view: 'landing' | 'dashboard') => void;
  triggerFileSelect: () => void;
  handleDrag: (e: React.DragEvent) => void;
  handleDrop: (e: React.DragEvent) => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  isUploading: boolean;
  uploadStatus: string;
  dragActive: boolean;
}

export const LandingView: React.FC<LandingViewProps> = ({
  setCurrentView,
  triggerFileSelect,
  handleDrag,
  handleDrop,
  fileInputRef,
  handleFileChange,
  isUploading,
  uploadStatus,
  dragActive,
}) => {
  return (
    <div className="flex-1 overflow-y-auto py-12 px-6">
      <div className="max-w-5xl mx-auto flex flex-col items-center">
        
        {/* Hero */}
        <div className="text-center mt-6 mb-12">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 text-blue-600 text-xs font-bold mb-6 border border-blue-100 shadow-sm shadow-blue-50">
            <Sparkles className="h-3.5 w-3.5" />
            Intent-Based Agentic Routing System Active
          </div>
          <h2 className="text-5xl font-extrabold tracking-tight text-slate-900 leading-tight">
            Chat With Your Documents <br />
            <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">Intelligently</span>
          </h2>
          <p className="mt-4 text-lg text-slate-500 max-w-2xl mx-auto font-medium">
            Upload PDF, Word, or Markdown files and query them with layout-aware visual grounding (transcribing tables, charts, and diagrams), powered by Google Gemini 2.5 and Pinecone.
          </p>
          <div className="mt-8 flex gap-4 justify-center">
            <button 
              onClick={() => setCurrentView('dashboard')}
              className="px-6 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold rounded-xl shadow-lg shadow-blue-200 flex items-center gap-2 transition-all hover:-translate-y-0.5"
            >
              Open Workspace Console
              <ArrowRight className="h-4.5 w-4.5" />
            </button>
            <button 
              onClick={triggerFileSelect}
              className="px-6 py-3.5 bg-white border border-slate-200 hover:border-slate-300 text-slate-700 font-semibold rounded-xl flex items-center gap-2 shadow-sm transition-all hover:bg-slate-50"
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
          className={`w-full max-w-3xl rounded-2xl border-2 border-dashed p-10 flex flex-col items-center justify-center transition-all cursor-pointer bg-white ${
            dragActive 
              ? 'border-blue-500 bg-blue-50/50 scale-[1.01]' 
              : 'border-slate-200 hover:border-slate-300'
          }`}
        >
          <input 
            type="file" 
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden" 
            accept=".pdf,.docx,.txt,.md"
          />
          
          {isUploading ? (
            <div className="flex flex-col items-center">
              <div className="h-12 w-12 rounded-xl bg-blue-50 flex items-center justify-center text-blue-600 pulse-primary mb-4">
                <Upload className="h-6 w-6" />
              </div>
              <h4 className="text-lg font-bold text-slate-800">{uploadStatus}</h4>
              <p className="text-sm text-slate-400 mt-1">Please keep this window open</p>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center">
              <div className="h-14 w-14 rounded-2xl bg-blue-50 flex items-center justify-center text-blue-600 mb-4 shadow-sm border border-blue-100">
                <Upload className="h-6 w-6" />
              </div>
              <h4 className="text-lg font-bold text-slate-800">Drag & Drop documents here</h4>
              <p className="text-sm text-slate-400 mt-1 max-w-sm">
                Supports PDF (with visual OCR for tables and diagrams), DOCX, TXT, or MD. Max 10MB per file.
              </p>
              <span className="mt-4 text-xs font-semibold text-blue-600 px-3 py-1 bg-blue-50 rounded-full border border-blue-100 hover:bg-blue-100/50 transition-all">
                Browse Files
              </span>
            </div>
          )}
        </div>

        {/* Features section */}
        <div className="mt-20 w-full">
          <div className="text-center mb-10">
            <h3 className="text-2xl font-bold text-slate-900">SaaS Feature Integrations</h3>
            <p className="text-sm text-slate-400 font-medium">Under the hood of the DocuMind RAG engine</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-all">
              <div className="h-10 w-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-4 font-bold">
                <Sparkles className="h-5 w-5" />
              </div>
              <h4 className="font-bold text-slate-800 mb-2">Intelligent Router</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Zero-shot Gemini classification routes generic chats away from vector search, saving Pinecone query loads.
              </p>
            </div>
            <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-all">
              <div className="h-10 w-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4 font-bold">
                <Database className="h-5 w-5" />
              </div>
              <h4 className="font-bold text-slate-800 mb-2">Pinecone Serverless</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Indexes high-density 768-dimensional text embeddings in namespaces, allowing rapid cosine search matchings.
              </p>
            </div>
            <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-all">
              <div className="h-10 w-10 rounded-lg bg-cyan-50 text-cyan-600 flex items-center justify-center mb-4 font-bold">
                <Search className="h-5 w-5" />
              </div>
              <h4 className="font-bold text-slate-800 mb-2">Source Citations</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Every statement retrieved has exact filename tracking and page-level mappings rendered in detail.
              </p>
            </div>
            <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-all">
              <div className="h-10 w-10 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center mb-4 font-bold">
                <BookOpen className="h-5 w-5" />
              </div>
              <h4 className="font-bold text-slate-800 mb-2">Multimodal OCR Ingestion</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Converts PDF pages into images to transcribe complex tables into markdown and capture visual chart context using Gemini Vision.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
