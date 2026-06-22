import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { LandingView } from './components/LandingView';
import { Sidebar } from './components/Sidebar';
import { ChatPanel } from './components/ChatPanel';
import { CitationsPanel } from './components/CitationsPanel';
import { AuthModal } from './components/AuthModal';
import { useAuth } from './hooks/useAuth';
import { useDocuments } from './hooks/useDocuments';
import { useChat } from './hooks/useChat';

export default function App() {
  // Navigation & View States
  const [currentView, setCurrentView] = useState<'landing' | 'dashboard'>('landing');

  // Theme State
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('darkMode');
    if (saved !== null) {
      return saved === 'true';
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('darkMode', String(darkMode));
  }, [darkMode]);

  // Hook-based State Management
  const { user, isAuthModalOpen, setIsAuthModalOpen, handleLogout } = useAuth();
  
  const {
    documents,
    isUploading,
    uploadStatus,
    dragActive,
    activeFilters,
    fileInputRef,
    toggleFilter,
    handleDrag,
    handleDrop,
    handleFileChange,
    triggerFileSelect,
    deleteDocument
  } = useDocuments(user, () => setCurrentView('dashboard'));

  const {
    chatSessions,
    activeSessionId,
    setActiveSessionId,
    inputValue,
    setInputValue,
    isStreaming,
    currentStreamText,
    retrievedSources,
    currentQueryType,
    chatBottomRef,
    deleteSession,
    createNewSession,
    handleSendMessage,
    activeSession
  } = useChat(user, activeFilters);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col font-sans text-slate-800 dark:text-slate-100 h-screen overflow-hidden">
      {/* Hidden file input for document ingestion */}
      <input 
        type="file" 
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden" 
        accept=".pdf,.docx,.txt,.md"
      />

      {/* Header bar */}
      <Header 
        currentView={currentView} 
        setCurrentView={setCurrentView} 
        darkMode={darkMode} 
        setDarkMode={setDarkMode} 
        user={user}
        onAuthClick={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
      />

      {/* Authentication Modal */}
      <AuthModal 
        isOpen={isAuthModalOpen} 
        onClose={() => setIsAuthModalOpen(false)} 
        onAuthSuccess={() => {}}
      />

      {/* Main content body */}
      <main className="flex-1 flex overflow-hidden">
        
        {/* VIEW 1: LANDING PAGE */}
        {currentView === 'landing' && (
          <LandingView 
            setCurrentView={setCurrentView}
            triggerFileSelect={triggerFileSelect}
            handleDrag={handleDrag}
            handleDrop={handleDrop}
            isUploading={isUploading}
            uploadStatus={uploadStatus}
            dragActive={dragActive}
          />
        )}

        {/* VIEW 2: WORKSPACE DASHBOARD */}
        {currentView === 'dashboard' && (
          <div className="flex-1 flex overflow-hidden h-full">
            
            {/* Left Sidebar - Documents & Uploads */}
            <Sidebar 
              isUploading={isUploading}
              uploadStatus={uploadStatus}
              triggerFileSelect={triggerFileSelect}
              chatSessions={chatSessions}
              activeSessionId={activeSessionId}
              setActiveSessionId={setActiveSessionId}
              createNewSession={createNewSession}
              documents={documents}
              activeFilters={activeFilters}
              toggleFilter={toggleFilter}
              deleteDocument={deleteDocument}
              deleteSession={deleteSession}
            />

            {/* Center Chat Panel */}
            <ChatPanel 
              activeSession={activeSession}
              currentQueryType={currentQueryType}
              isStreaming={isStreaming}
              isUploading={isUploading}
              currentStreamText={currentStreamText}
              inputValue={inputValue}
              setInputValue={setInputValue}
              handleSendMessage={handleSendMessage}
              chatBottomRef={chatBottomRef}
            />

            {/* Right Panel - Grounded citations */}
            <CitationsPanel 
              currentQueryType={currentQueryType}
              retrievedSources={retrievedSources}
              isStreaming={isStreaming}
            />

          </div>
        )}

      </main>
    </div>
  );
}
