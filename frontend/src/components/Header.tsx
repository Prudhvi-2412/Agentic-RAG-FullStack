import React from 'react';
import { Home, Database, Sparkles, ExternalLink, Sun, Moon } from 'lucide-react';
import { User } from '@supabase/supabase-js';

interface HeaderProps {
  currentView: 'landing' | 'dashboard';
  setCurrentView: (view: 'landing' | 'dashboard') => void;
  darkMode: boolean;
  setDarkMode: (darkMode: boolean) => void;
  user: User | null;
  onAuthClick: () => void;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({ 
  currentView, 
  setCurrentView, 
  darkMode, 
  setDarkMode,
  user,
  onAuthClick,
  onLogout
}) => {
  return (
    <header className="glass-surface sticky top-0 z-30 px-6 py-4 flex items-center justify-between border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md">
      <div className="flex items-center gap-3 cursor-pointer" onClick={() => setCurrentView('landing')}>
        <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-200 dark:shadow-none">
          <Sparkles className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">DocuMind AI</h1>
          <p className="text-xs text-slate-400 dark:text-slate-500 font-medium">Chat With Your Documents Intelligently</p>
        </div>
      </div>

      <nav className="flex items-center gap-4">
        <button 
          onClick={() => setCurrentView('landing')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
            currentView === 'landing' 
              ? 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 font-bold' 
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Home className="h-4 w-4" />
          Home
        </button>
        <button 
          onClick={() => setCurrentView('dashboard')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
            currentView === 'dashboard' 
              ? 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 font-bold' 
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Database className="h-4 w-4" />
          Workspace
        </button>
        
        {user ? (
          <div className="flex items-center gap-2.5 pl-2 border-l border-slate-200 dark:border-slate-800">
            <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center text-blue-600 dark:text-blue-400 font-bold text-sm">
              {user.email?.charAt(0).toUpperCase()}
            </div>
            <span className="hidden md:inline text-sm font-medium text-slate-600 dark:text-slate-300 max-w-[150px] truncate" title={user.email}>
              {user.email}
            </span>
            <button 
              onClick={onLogout}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-850 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-bold rounded-lg transition-all"
            >
              Logout
            </button>
          </div>
        ) : (
          <button 
            onClick={onAuthClick}
            className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-sm font-bold rounded-lg shadow-sm transition-all hover:-translate-y-0.5"
          >
            Sign In
          </button>
        )}

        <button
          onClick={() => setDarkMode(!darkMode)}
          className="p-2 rounded-lg text-slate-450 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-350 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all flex items-center justify-center border border-transparent hover:border-slate-200 dark:hover:border-slate-700"
          title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {darkMode ? <Sun className="h-4.5 w-4.5 text-amber-500 fill-amber-550" /> : <Moon className="h-4.5 w-4.5 text-slate-500 fill-slate-100" />}
        </button>

        <a 
          href="https://github.com" 
          target="_blank" 
          rel="noreferrer"
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-400 pl-2 border-l border-slate-200 dark:border-slate-800"
        >
          v1.0.0
          <ExternalLink className="h-3 w-3" />
        </a>
      </nav>
    </header>
  );
};
