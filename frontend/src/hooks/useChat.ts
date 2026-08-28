import { useState, useRef, useEffect } from 'react';
import { Message, SourceCitation, ChatSession } from '../types';
import { supabase } from '../supabaseClient';
import { User } from '@supabase/supabase-js';
import { BACKEND_URL } from '../config';

const WELCOME_TEXT =
  'Hello! I am DocuMind AI. I have pre-indexed the book "Ikigai: The Japanese Secret to a Long and Happy Life". Ask me anything about finding your purpose, longevity, or flow!';

function createWelcomeSession(id: string): ChatSession {
  return {
    id,
    title: 'Ikigai Longevity & Purpose',
    messages: [{ id: `welcome-${id}`, role: 'assistant', text: WELCOME_TEXT }],
    sources: [],
    queryType: null
  };
}

export function useChat(user: User | null, activeFilters: string[]) {
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([createWelcomeSession('session-1')]);
  const [activeSessionId, setActiveSessionId] = useState<string>('session-1');
  const [inputValue, setInputValue] = useState('');

  // Streaming states
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamText, setCurrentStreamText] = useState('');
  const [retrievedSources, setRetrievedSources] = useState<SourceCitation[]>([]);
  const [currentQueryType, setCurrentQueryType] = useState<string | null>(null);

  const chatBottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Effects below key off the id rather than the user object: a token refresh hands back a
  // new object for the same person, and re-running them would abort an in-flight stream.
  const userId = user?.id ?? null;

  const activeSession = chatSessions.find(s => s.id === activeSessionId) || chatSessions[0];
  const messages = activeSession?.messages ?? [];

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentStreamText]);

  // Abort any in-flight stream when the hook unmounts, so the reader is not left open and
  // state updates are not attempted against an unmounted tree.
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  // Load chat sessions when the signed-in identity changes
  useEffect(() => {
    let cancelled = false;

    // A session belonging to the previous identity must not keep receiving tokens.
    abortRef.current?.abort();
    setIsStreaming(false);
    setCurrentStreamText('');

    if (user) {
      const loadUserSessions = async () => {
        try {
          const { data: sessions, error } = await supabase
            .from('chat_sessions')
            .select('*')
            .eq('user_id', user.id)
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

          if (cancelled) return;

          if (sessionsWithMessages.length > 0) {
            setChatSessions(sessionsWithMessages);
            setActiveSessionId(sessionsWithMessages[0].id);
            return;
          }

          // Create a default session for the logged-in user if none exists
          const defaultSession = createWelcomeSession(`session-${Date.now()}`);
          await persistSession(user.id, defaultSession);
          if (cancelled) return;
          setChatSessions([defaultSession]);
          setActiveSessionId(defaultSession.id);
        } catch (err) {
          console.error('Error loading chat sessions:', err);
        }
      };
      loadUserSessions();
    } else {
      // Load guest sessions from localStorage
      const savedSessions = localStorage.getItem('guestChatSessions');
      const savedActiveId = localStorage.getItem('guestActiveSessionId');
      let restored: ChatSession[] | null = null;

      if (savedSessions) {
        try {
          const parsed = JSON.parse(savedSessions);
          if (Array.isArray(parsed) && parsed.length > 0) restored = parsed;
        } catch (e) {
          console.error('Error loading guest sessions:', e);
        }
      }

      if (restored) {
        setChatSessions(restored);
        setActiveSessionId(
          savedActiveId && restored.some(s => s.id === savedActiveId) ? savedActiveId : restored[0].id
        );
      } else {
        setChatSessions([createWelcomeSession('session-1')]);
        setActiveSessionId('session-1');
      }
    }

    return () => {
      cancelled = true;
    };
  }, [userId]);

  // Persist guest sessions. Skipped while streaming so a long answer does not trigger a
  // localStorage write on every token.
  useEffect(() => {
    if (user || isStreaming) return;
    localStorage.setItem('guestChatSessions', JSON.stringify(chatSessions));
  }, [chatSessions, user, isStreaming]);

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

  const persistSession = async (userId: string, session: ChatSession) => {
    const { error: sessionError } = await supabase.from('chat_sessions').insert({
      id: session.id,
      user_id: userId,
      title: session.title,
      query_type: null
    });
    if (sessionError) throw sessionError;

    const { error: messageError } = await supabase.from('messages').insert({
      session_id: session.id,
      role: session.messages[0].role,
      text: session.messages[0].text
    });
    if (messageError) throw messageError;
  };

  const deleteSession = async (sessionId: string) => {
    const remaining = chatSessions.filter(s => s.id !== sessionId);

    if (user) {
      const { error } = await supabase.from('chat_sessions').delete().eq('id', sessionId);
      if (error) {
        console.error('Error deleting chat session:', error);
        return;
      }
    }

    if (remaining.length > 0) {
      setChatSessions(remaining);
      if (activeSessionId === sessionId) setActiveSessionId(remaining[0].id);
      return;
    }

    // Deleting the last session leaves the workspace with a fresh one.
    const defaultSession = createWelcomeSession(`session-${Date.now()}`);
    if (user) {
      try {
        await persistSession(user.id, defaultSession);
      } catch (err) {
        console.error('Error creating default session on deletion:', err);
      }
    }
    setChatSessions([defaultSession]);
    setActiveSessionId(defaultSession.id);
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
        await persistSession(user.id, newSession);
      } catch (err) {
        console.error('Error creating new session:', err);
        return;
      }
    }

    setChatSessions(prev => [newSession, ...prev]);
    setActiveSessionId(newSessionId);
    setRetrievedSources([]);
    setCurrentQueryType(null);
  };

  const appendMessage = (sessionId: string, message: Message) => {
    setChatSessions(prev => prev.map(s => (
      s.id === sessionId
        ? { ...s, messages: [...s.messages.filter(m => m.id !== message.id), message] }
        : s
    )));
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputValue.trim() || isStreaming) return;

    const queryText = inputValue.trim();
    const sessionId = activeSessionId;
    setInputValue('');
    setIsStreaming(true);
    setCurrentStreamText('');
    setRetrievedSources([]);
    setCurrentQueryType(null);

    const historyPayload = messages.map(m => ({ role: m.role, text: m.text }));

    const userMsg: Message = { id: `user-${Date.now()}`, role: 'user', text: queryText };
    appendMessage(sessionId, userMsg);

    if (user) {
      const { error } = await supabase.from('messages').insert({
        session_id: sessionId,
        role: 'user',
        text: queryText
      });
      if (error) console.error('Error inserting user message:', error);
    }

    const assistantMsgId = `assistant-${Date.now()}`;
    let accumulatedText = '';
    let completed = false;

    const controller = new AbortController();
    abortRef.current?.abort();
    abortRef.current = controller;

    try {
      const session = (await supabase.auth.getSession()).data.session;
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (session) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }

      const response = await fetch(`${BACKEND_URL}/api/query`, {
        method: 'POST',
        headers,
        signal: controller.signal,
        body: JSON.stringify({
          query: queryText,
          filters: activeFilters.length > 0 ? activeFilters : null,
          history: historyPayload
        })
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
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

          let eventName = '';
          let dataVal = '';

          for (const line of packet.split('\n')) {
            if (line.startsWith('event:')) {
              eventName = line.substring(6).trim();
            } else if (line.startsWith('data:')) {
              dataVal = line.substring(5).trim();
            }
          }

          if (!dataVal) continue;

          let payload: any;
          try {
            payload = JSON.parse(dataVal);
          } catch (err) {
            console.error('Error parsing SSE packet:', err);
            continue;
          }

          if (eventName === 'metadata') {
            setCurrentQueryType(payload.query_type);
            setChatSessions(prev => prev.map(s => (
              s.id === sessionId ? { ...s, queryType: payload.query_type } : s
            )));
          } else if (eventName === 'sources') {
            const sources = payload.sources || [];
            setRetrievedSources(sources);
            setChatSessions(prev => prev.map(s => (
              s.id === sessionId ? { ...s, sources } : s
            )));
          } else if (eventName === 'token') {
            accumulatedText += payload.text;
            setCurrentStreamText(accumulatedText);
            appendMessage(sessionId, { id: assistantMsgId, role: 'assistant', text: accumulatedText });
          } else if (eventName === 'complete') {
            completed = true;
          }
        }
      }

      if (!completed) {
        // The connection closed before the backend signalled completion, so the answer on
        // screen is partial. Say so instead of persisting it as a finished reply.
        throw new Error('The response stream ended unexpectedly.');
      }

      if (user && accumulatedText) {
        const { error } = await supabase.from('messages').insert({
          session_id: sessionId,
          role: 'assistant',
          text: accumulatedText
        });
        if (error) console.error('Error inserting assistant message:', error);
      }
    } catch (err: any) {
      if (err?.name === 'AbortError') {
        // Deliberate cancellation (sign-out, identity change, unmount) - no error to show,
        // but log it: a silent abort with no trace is very hard to diagnose from a bug report.
        console.debug('Chat stream aborted before completion.');
        return;
      }

      console.error(err);
      const detail = accumulatedText
        ? '\n\n*The response was interrupted before it finished.*'
        : `**Connection Error**: Could not reach the assistant at \`${BACKEND_URL}\`.\n\n*Details: ${err.message}*`;

      appendMessage(sessionId, {
        id: assistantMsgId,
        role: 'assistant',
        text: `${accumulatedText}${detail}`
      });
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      setIsStreaming(false);
      setCurrentStreamText('');
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
