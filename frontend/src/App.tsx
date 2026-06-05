import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Header } from './components/Header';
import { LandingView } from './components/LandingView';
import { Sidebar } from './components/Sidebar';
import { ChatPanel } from './components/ChatPanel';
import { CitationsPanel } from './components/CitationsPanel';
import { DocumentItem, Message, SourceCitation, ChatSession } from './types';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://agentic-rag-fullstack-1.onrender.com');

export default function App() {
  // Navigation & View States
  const [currentView, setCurrentView] = useState<'landing' | 'dashboard'>('landing');
  
  // Document List State
  const [documents, setDocuments] = useState<DocumentItem[]>([
    {
      id: 'marcus-meditations-demo',
      name: 'meidtations.pdf',
      chunksCount: 1558,
      status: 'indexed',
      timestamp: 'Demo File'
    }
  ]);
  
  // Chat States
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([
    {
      id: 'session-1',
      title: 'Marcus Aurelius Stoicism',
      messages: [
        {
          id: 'welcome-msg',
          role: 'assistant',
          text: 'Hello! I am DocuMind AI. Upload your documents in the sidebar, and I will help you extract insights. I am currently connected to Pinecone and the Gemini API.'
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

  // Delete Document Handler
  const deleteDocument = (id: string, name: string) => {
    setDocuments(prev => prev.filter(doc => doc.id !== id));
    setActiveFilters(prev => prev.filter(f => f !== name));
    alert(`"${name}" vector indexes deleted from Pinecone environment cache.`);
  };

  // Create new chat session
  const createNewSession = () => {
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
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-800 h-screen overflow-hidden">
      {/* Header bar */}
      <Header currentView={currentView} setCurrentView={setCurrentView} />

      {/* Main content body */}
      <main className="flex-1 flex overflow-hidden">
        
        {/* VIEW 1: LANDING PAGE */}
        {currentView === 'landing' && (
          <LandingView 
            setCurrentView={setCurrentView}
            triggerFileSelect={triggerFileSelect}
            handleDrag={handleDrag}
            handleDrop={handleDrop}
            fileInputRef={fileInputRef}
            handleFileChange={handleFileChange}
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
