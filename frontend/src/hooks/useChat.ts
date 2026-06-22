import { useState, useRef, useEffect } from 'react';
import { Message, SourceCitation, ChatSession } from '../types';
import { supabase } from '../supabaseClient';
import { User } from '@supabase/supabase-js';

const BACKEND_URL = (import.meta as any).env.VITE_BACKEND_URL || 
  ((import.meta as any).env.DEV ? 'http://localhost:8000' : 'https://agentic-rag-fullstack-1.onrender.com');

export function useChat(user: User | null, activeFilters: string[]) {
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
  
  // Streaming states
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamText, setCurrentStreamText] = useState('');
  const [retrievedSources, setRetrievedSources] = useState<SourceCitation[]>([]);
  const [currentQueryType, setCurrentQueryType] = useState<string | null>(null);

  const chatBottomRef = useRef<HTMLDivElement>(null);

  const activeSession = chatSessions.find(s => s.id === activeSessionId) || chatSessions[0];
  const messages = activeSession.messages;

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentStreamText]);

  // Load chat sessions when user changes
  useEffect(() => {
    if (user) {
      const loadUserSessions = async () => {
        try {
          const { data: sessions, error } = await supabase
            .from('chat_sessions')
            .select('*')
            .order('created_at', { ascending: false });

          if (error) throw error;

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

          if (sessionsWithMessages.length > 0) {
            setChatSessions(sessionsWithMessages);
            setActiveSessionId(sessionsWithMessages[0].id);
          } else {
            // Create a default session for the logged-in user if none exists
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
              user_id: user.id,
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
          console.error('Error loading chat sessions:', err);
        }
      };
      loadUserSessions();
    } else {
      // Load guest sessions from localStorage
      const savedSessions = localStorage.getItem('guestChatSessions');
      const savedActiveId = localStorage.getItem('guestActiveSessionId');
      if (savedSessions) {
        try {
          const parsed = JSON.parse(savedSessions);
          if (parsed && parsed.length > 0) {
            setChatSessions(parsed);
            if (savedActiveId && parsed.some((s: any) => s.id === savedActiveId)) {
              setActiveSessionId(savedActiveId);
            } else {
              setActiveSessionId(parsed[0].id);
            }
          }
        } catch (e) {
          console.error('Error loading guest sessions:', e);
        }
      } else {
        // Reset to default guest session
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
      }
    }
  }, [user]);

  // Persist guest sessions changes
  useEffect(() => {
    if (!user) {
      localStorage.setItem('guestChatSessions', JSON.stringify(chatSessions));
    }
  }, [chatSessions, user]);

  useEffect(() => {
    if (!user) {
      localStorage.setItem('guestActiveSessionId', activeSessionId);
    }
  }, [activeSessionId, user]);

  // Sync sources & query type panel when active session changes
  useEffect(() => {
    if (activeSession) {
      setRetrievedSources(activeSession.sources || []);
      setCurrentQueryType(activeSession.queryType || null);
    }
  }, [activeSessionId, activeSession]);

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

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputValue.trim() || isStreaming) return;

    const queryText = inputValue;
    setInputValue('');
    setIsStreaming(true);
    setCurrentStreamText('');
    setRetrievedSources([]);
    setCurrentQueryType(null);

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

    setChatSessions(prev => prev.map(s => {
      if (s.id === activeSessionId) {
        return { ...s, messages: updatedMessages };
      }
      return s;
    }));

    const assistantMsgId = `assistant-${Date.now()}`;
    let accumulatedText = '';

    try {
      const session = (await supabase.auth.getSession()).data.session;
      const headers: any = { 'Content-Type': 'application/json' };
      if (session) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }

      const historyPayload = messages.map(m => ({
        role: m.role,
        text: m.text
      }));

      const response = await fetch(`${BACKEND_URL}/api/query`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ 
          query: queryText,
          filters: activeFilters.length > 0 ? activeFilters : null,
          history: historyPayload
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

  return {
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
  };
}
