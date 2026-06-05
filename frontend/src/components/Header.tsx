import React from 'react';
import { Home, Database, Sparkles, ExternalLink } from 'lucide-react';

interface HeaderProps {
  currentView: 'landing' | 'dashboard';
  setCurrentView: (view: 'landing' | 'dashboard') => void;
}

export const Header: React.FC<HeaderProps> = ({ currentView, setCurrentView }) => {
  return (
    <header className="glass-surface sticky top-0 z-30 px-6 py-4 flex items-center justify-between border-b border-slate-200 bg-white/80 backdrop-blur-md">
      <div className="flex items-center gap-3 cursor-pointer" onClick={() => setCurrentView('landing')}>
        <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-200">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">DocuMind AI</h1>
          <p className="text-xs text-slate-400 font-medium">Chat With Your Documents Intelligently</p>
        </div>
      </div>

      <nav className="flex items-center gap-4">
        <button 
          onClick={() => setCurrentView('landing')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
            currentView === 'landing' 
              ? 'bg-blue-50 text-blue-600 font-bold' 
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Home className="h-4 w-4" />
          Home
        </button>
        <button 
          onClick={() => setCurrentView('dashboard')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
            currentView === 'dashboard' 
              ? 'bg-blue-50 text-blue-600 font-bold' 
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Database className="h-4 w-4" />
          Workspace
        </button>
        <a 
          href="https://github.com" 
          target="_blank" 
          rel="noreferrer"
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-slate-600 pl-2 border-l border-slate-200"
        >
          v1.0.0
          <ExternalLink className="h-3 w-3" />
        </a>
      </nav>
    </header>
  );
};
