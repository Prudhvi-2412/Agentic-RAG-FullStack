import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Header } from './components/Header';
import { LandingView } from './components/LandingView';
import { Sidebar } from './components/Sidebar';
import { ChatPanel } from './components/ChatPanel';
import { CitationsPanel } from './components/CitationsPanel';
import { DocumentItem, Message, SourceCitation, ChatSession } from './types';
import { supabase } from './supabaseClient';
import { AuthModal } from './components/AuthModal';
import { User } from '@supabase/supabase-js';

const BACKEND_URL = (import.meta as any).env.VITE_BACKEND_URL || ((import.meta as any).env.DEV ? 'http://localhost:8000' : 'https://agentic-rag-fullstack-1.onrender.com');

export default function App() {
  // Navigation & View States
  const [currentView, setCurrentView] = useState<'landing' | 'dashboard'>('landing');
  
  // Supabase User & Auth States
  const [user, setUser] = useState<User | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  
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
  
  // Ikigai pre-indexed demo document — always available for guest/new users
  const IKIGAI_DEMO_DOC: DocumentItem = {
    id: 'ikigai-default-doc-id',
    name: 'Ikigai.pdf',
    chunksCount: 847,
    status: 'indexed',
    timestamp: 'Pre-indexed Demo'
  };

  // Document List State — Ikigai demo shown by default for guests; replaced by user docs on login
  const [documents, setDocuments] = useState<DocumentItem[]>([IKIGAI_DEMO_DOC]);
  
  // Chat States
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([
    {
      id: 'session-1',
      title: 'Ikigai Longevity & Purpose',
      messages: [
        {
          id: 'welcome-msg',
          role: 'assistant',
          text: 'Hello! I am DocuMind AI. I have pre-indexed the book "Ikigai: The Japanese Secret to a Long and Happy Life". Ask me anything about finding your purpose, longevity, or flow!'
        }
      ],
      sources: [],
      queryType: null
    }
  ]);
  const [activeSessionId, setActiveSessionId] = useState<string>('session-1');
  const [inputValue, setInputValue] = useState('');
  
  // Ingestion Status States
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [dragActive, setDragActive] = useState(false);
  
  // Streaming Generation States
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamText, setCurrentStreamText] = useState('');
  const [retrievedSources, setRetrievedSources] = useState<SourceCitation[]>([]);
  const [currentQueryType, setCurrentQueryType] = useState<string | null>(null);
  const [activeFilters, setActiveFilters] = useState<string[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const toggleFilter = (filename: string) => {
    setActiveFilters(prev => 
      prev.includes(filename) 
        ? prev.filter(f => f !== filename) 
        : [...prev, filename]
    );
  };

  // Active Session helper
  const activeSession = chatSessions.find(s => s.id === activeSessionId) || chatSessions[0];
  const messages = activeSession.messages;

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentStreamText]);

  // Load User Data from Supabase
  const loadUserData = async (userId: string) => {
    try {
      // 1. Fetch documents
      const { data: docs, error: docsError } = await supabase
        .from('documents')
        .select('*')
        .order('created_at', { ascending: false });

      if (docsError) throw docsError;

      // 2. Fetch sessions
      const { data: sessions, error: sessionsError } = await supabase
        .from('chat_sessions')
        .select('*')
        .order('created_at', { ascending: false });

      if (sessionsError) throw sessionsError;

      // 3. Fetch messages for each session
      const sessionsWithMessages = await Promise.all(
        (sessions || []).map(async (session) => {
          const { data: msgs, error: msgsError } = await supabase
            .from('messages')
            .select('*')
            .eq('session_id', session.id)
            .order('created_at', { ascending: true });

          if (msgsError) throw msgsError;

          return {
            id: session.id,
            title: session.title,
            messages: (msgs || []).map(m => ({
              id: m.id,
              role: m.role as 'user' | 'assistant',
              text: m.text
            })),
            sources: [],
            queryType: session.query_type || null
          };
        })
      );

      const mappedDocs = (docs || []).map(d => ({
        id: d.id,
        name: d.name,
        chunksCount: d.chunks_count,
        status: d.status,
        timestamp: new Date(d.created_at).toLocaleDateString()
      }));

      setDocuments(mappedDocs);
      
      if (sessionsWithMessages.length > 0) {
        setChatSessions(sessionsWithMessages);
        setActiveSessionId(sessionsWithMessages[0].id);
      } else {
        const defaultSessionId = `session-${Date.now()}`;
        const defaultSession = {
          id: defaultSessionId,
          title: 'Ikigai Longevity & Purpose',
          messages: [
            {
              id: 'welcome-msg',
              role: 'assistant' as const,
              text: 'Hello! I am DocuMind AI. I have pre-indexed the book "Ikigai: The Japanese Secret to a Long and Happy Life". Ask me anything about finding your purpose, longevity, or flow!'
            }
          ],
          sources: [],
          queryType: null
        };
        
        await supabase.from('chat_sessions').insert({
          id: defaultSessionId,
          user_id: userId,
          title: defaultSession.title,
          query_type: null
        });

        await supabase.from('messages').insert({
          session_id: defaultSessionId,
          role: 'assistant',
          text: defaultSession.messages[0].text
        });

        setChatSessions([defaultSession]);
        setActiveSessionId(defaultSessionId);
      }

    } catch (err) {
      console.error('Error loading user data from Supabase:', err);
    }
  };

  const clearUserData = () => {
    // Restore Ikigai demo doc for guests on logout
    setDocuments([IKIGAI_DEMO_DOC]);
    setChatSessions([
      {
        id: 'session-1',
        title: 'Ikigai Longevity & Purpose',
        messages: [
          {
            id: 'welcome-msg',
            role: 'assistant',
            text: 'Hello! I am DocuMind AI. I have pre-indexed the book "Ikigai: The Japanese Secret to a Long and Happy Life". Ask me anything about finding your purpose, longevity, or flow!'
          }
        ],
        sources: [],
        queryType: null
      }
    ]);
    setActiveSessionId('session-1');
  };

  // Auth synchronization listener
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        loadUserData(session.user.id);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        loadUserData(session.user.id);
      } else {
        clearUserData();
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  // Drag and Drop Ingestion Handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await uploadFile(e.target.files[0]);
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  // Upload Pipeline Request
  const uploadFile = async (file: File) => {
    setIsUploading(true);
    setUploadStatus('Validating...');
    
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !['pdf', 'docx', 'txt', 'md', 'markdown'].includes(ext)) {
      setUploadStatus('Unsupported file format.');
      setTimeout(() => setIsUploading(false), 2000);
      return;
    }

    setUploadStatus('Parsing & Chunking...');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${BACKEND_URL}/api/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const data = response.data;
      setUploadStatus('Creating Embeddings & Upserting...');

      const newDoc: DocumentItem = {
        id: data.document_id,
        name: data.filename,
        chunksCount: data.chunks_created,
        status: data.status,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setDocuments(prev => [newDoc, ...prev]);
      if (user) {
        await supabase.from('documents').insert({
          id: data.document_id,
          user_id: user.id,
          name: data.filename,
          chunks_count: data.chunks_created,
          status: data.status
        });
      }
      setUploadStatus('Ingested & Indexed!');
      
      // Auto transition to workspace
      setTimeout(() => {
        setIsUploading(false);
        setUploadStatus('');
        setCurrentView('dashboard');
      }, 1500);

    } catch (error: any) {
      console.error(error);
      const errMsg = error.response?.data?.detail || error.message || 'Server error';
      setUploadStatus(`Error: ${errMsg}`);
      setTimeout(() => {
        setIsUploading(false);
        setUploadStatus('');
      }, 4000);
    }
  };

  // Delete Document Handler — permanently removes from Pinecone + Supabase/localStorage
  // The Ikigai demo doc (ikigai-default-doc-id) is a shared pre-indexed book; removing it from
  // the UI is fine but we never wipe its Pinecone vectors so new users always find it queryable.
  const deleteDocument = async (id: string, name: string) => {
    const IS_DEMO_DOC = id === 'ikigai-default-doc-id';

    // 1. Immediately remove from UI
    setDocuments(prev => prev.filter(doc => doc.id !== id));
    setActiveFilters(prev => prev.filter(f => f !== name));

    // 2. For real user-uploaded docs: delete vectors from Pinecone permanently
    if (!IS_DEMO_DOC) {
      try {
        await fetch(`http://localhost:8000/api/documents/${id}`, { method: 'DELETE' });
      } catch (err) {
        console.error('Error deleting document vectors from Pinecone:', err);
      }

      // 3. Persist deletion — Supabase for logged-in users, localStorage for guests
      if (user) {
        try {
          await supabase.from('documents').delete().eq('id', id);
        } catch (err) {
          console.error('Error deleting document from Supabase:', err);
        }
      } else {
        const deleted: string[] = JSON.parse(localStorage.getItem('deletedDocIds') || '[]');
        if (!deleted.includes(id)) {
          deleted.push(id);
          localStorage.setItem('deletedDocIds', JSON.stringify(deleted));
        }
      }
    }
    // Demo doc removal is UI-only — Pinecone vectors stay intact for other users
  };

  // Delete Chat Session Handler
  const deleteSession = async (sessionId: string) => {
    let nextActiveId = activeSessionId;
    if (activeSessionId === sessionId) {
      const remaining = chatSessions.filter(s => s.id !== sessionId);
      if (remaining.length > 0) {
        nextActiveId = remaining[0].id;
      } else {
        const defaultSessionId = `session-${Date.now()}`;
        const defaultSession = {
          id: defaultSessionId,
          title: 'Ikigai Longevity & Purpose',
          messages: [
            {
              id: 'welcome-msg',
              role: 'assistant' as const,
              text: 'Hello! I am DocuMind AI. I have pre-indexed the book "Ikigai: The Japanese Secret to a Long and Happy Life". Ask me anything about finding your purpose, longevity, or flow!'
            }
          ],
          sources: [],
          queryType: null
        };

        if (user) {
          try {
            await supabase.from('chat_sessions').insert({
              id: defaultSessionId,
              user_id: user.id,
              title: defaultSession.title,
              query_type: null
            });

            await supabase.from('messages').insert({
              session_id: defaultSessionId,
              role: 'assistant',
              text: defaultSession.messages[0].text
            });
          } catch (err) {
            console.error('Error creating default session on deletion:', err);
          }
        }

        setChatSessions([defaultSession]);
        setActiveSessionId(defaultSessionId);
        return;
      }
    }

    if (user) {
      try {
        await supabase.from('chat_sessions').delete().eq('id', sessionId);
      } catch (err) {
        console.error('Error deleting chat session from Supabase:', err);
      }
    }

    setChatSessions(prev => prev.filter(s => s.id !== sessionId));
    setActiveSessionId(nextActiveId);
  };

  // Create new chat session
  const createNewSession = async () => {
    const newSessionId = `session-${Date.now()}`;
    const newSession: ChatSession = {
      id: newSessionId,
      title: `Query Session ${chatSessions.length + 1}`,
      messages: [
        {
          id: `welcome-${newSessionId}`,
          role: 'assistant',
          text: 'New session started. Ask general questions or query your documents.'
        }
      ],
      sources: [],
      queryType: null
    };

    if (user) {
      try {
        await supabase.from('chat_sessions').insert({
          id: newSessionId,
          user_id: user.id,
          title: newSession.title,
          query_type: null
        });

        await supabase.from('messages').insert({
          session_id: newSessionId,
          role: 'assistant',
          text: newSession.messages[0].text
        });
      } catch (err) {
        console.error('Error creating new session:', err);
      }
    }

    setChatSessions(prev => [newSession, ...prev]);
    setActiveSessionId(newSessionId);
    setRetrievedSources([]);
    setCurrentQueryType(null);
  };

  // Send query & parse POST SSE response
  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputValue.trim() || isStreaming) return;

    const queryText = inputValue;
    setInputValue('');
    setIsStreaming(true);
    setCurrentStreamText('');
    setRetrievedSources([]);
    setCurrentQueryType(null);

    // Append user message
    const userMsg: Message = { id: `user-${Date.now()}`, role: 'user', text: queryText };
    const updatedMessages = [...messages, userMsg];
    
    if (user) {
      try {
        await supabase.from('messages').insert({
          session_id: activeSessionId,
          role: 'user',
          text: queryText
        });
      } catch (err) {
        console.error('Error inserting user message:', err);
      }
    }

    // Update local session messages
    setChatSessions(prev => prev.map(s => {
      if (s.id === activeSessionId) {
        return { ...s, messages: updatedMessages };
      }
      return s;
    }));

    const assistantMsgId = `assistant-${Date.now()}`;
    let accumulatedText = '';

    try {
      const response = await fetch(`${BACKEND_URL}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: queryText,
          filters: activeFilters.length > 0 ? activeFilters : null
        })
      });

      if (!response.ok) {
        throw new Error(`Connection error: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Readable stream not supported.');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const packets = buffer.split('\n\n');
        buffer = packets.pop() || '';

        for (const packet of packets) {
          if (!packet.trim()) continue;

          const lines = packet.split('\n');
          let eventName = '';
          let dataVal = '';

          for (const line of lines) {
            if (line.startsWith('event:')) {
              eventName = line.substring(6).trim();
            } else if (line.startsWith('data:')) {
              dataVal = line.substring(5).trim();
            }
          }

          if (dataVal) {
            try {
              const payload = JSON.parse(dataVal);
              
              if (eventName === 'metadata') {
                setCurrentQueryType(payload.query_type);
                setChatSessions(prev => prev.map(s => {
                  if (s.id === activeSessionId) {
                    return { ...s, queryType: payload.query_type };
                  }
                  return s;
                }));
              } else if (eventName === 'sources') {
                setRetrievedSources(payload.sources || []);
                setChatSessions(prev => prev.map(s => {
                  if (s.id === activeSessionId) {
                    return { ...s, sources: payload.sources || [] };
                  }
                  return s;
                }));
              } else if (eventName === 'token') {
                accumulatedText += payload.text;
                setCurrentStreamText(accumulatedText);
                
                setChatSessions(prev => prev.map(s => {
                  if (s.id === activeSessionId) {
                    const filtered = s.messages.filter(m => m.id !== assistantMsgId);
                    return {
                      ...s,
                      messages: [...filtered, { id: assistantMsgId, role: 'assistant', text: accumulatedText }]
                    };
                  }
                  return s;
                }));
              } else if (eventName === 'complete') {
                setIsStreaming(false);
                if (user) {
                  try {
                    await supabase.from('messages').insert({
                      session_id: activeSessionId,
                      role: 'assistant',
                      text: accumulatedText
                    });
                  } catch (err) {
                    console.error('Error inserting assistant message:', err);
                  }
                }
              }
            } catch (err) {
              console.error('Error parsing SSE packet:', err);
            }
          }
        }
      }

    } catch (err: any) {
      console.error(err);
      setIsStreaming(false);
      const errorMsg: Message = {
        id: assistantMsgId,
        role: 'assistant',
        text: `**Connection Error**: Failed to stream response from backend. Ensure your FastAPI server is running on \`${BACKEND_URL}\`.\n\n*Details: ${err.message}*`
      };
      setChatSessions(prev => prev.map(s => {
        if (s.id === activeSessionId) {
          return { ...s, messages: [...s.messages, errorMsg] };
        }
        return s;
      }));
    }
  };

  // Load session sources to side panel when switching sessions
  useEffect(() => {
    if (activeSession) {
      setRetrievedSources(activeSession.sources || []);
      setCurrentQueryType(activeSession.queryType || null);
    }
  }, [activeSessionId]);

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
