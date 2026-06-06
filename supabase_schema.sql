-- Supabase Database Schema for DocuMind AI

-- 1. Create Documents Table
CREATE TABLE public.documents (
  id TEXT PRIMARY KEY, -- Stores the document_id (UUID or custom string)
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  name TEXT NOT NULL,
  chunks_count INTEGER NOT NULL,
  status TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 2. Create Chat Sessions Table
CREATE TABLE public.chat_sessions (
  id TEXT PRIMARY KEY, -- Unique session ID
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  title TEXT NOT NULL,
  query_type TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 3. Create Messages Table
CREATE TABLE public.messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT REFERENCES public.chat_sessions(id) ON DELETE CASCADE NOT NULL,
  role TEXT NOT NULL, -- 'user' or 'assistant'
  text TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 4. Enable Row Level Security (RLS) on all tables
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- 5. Row Level Security Policies

-- Documents Policies
CREATE POLICY "Allow users to read their own documents"
  ON public.documents FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Allow users to insert their own documents"
  ON public.documents FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Allow users to delete their own documents"
  ON public.documents FOR DELETE
  USING (auth.uid() = user_id);

-- Chat Sessions Policies
CREATE POLICY "Allow users to read their own sessions"
  ON public.chat_sessions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Allow users to insert their own sessions"
  ON public.chat_sessions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Allow users to update their own sessions"
  ON public.chat_sessions FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Allow users to delete their own sessions"
  ON public.chat_sessions FOR DELETE
  USING (auth.uid() = user_id);

-- Messages Policies (Linked to Session ownership)
CREATE POLICY "Allow users to read messages in their own sessions"
  ON public.messages FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.chat_sessions
      WHERE public.chat_sessions.id = public.messages.session_id
      AND public.chat_sessions.user_id = auth.uid()
    )
  );

CREATE POLICY "Allow users to insert messages in their own sessions"
  ON public.messages FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.chat_sessions
      WHERE public.chat_sessions.id = public.messages.session_id
      AND public.chat_sessions.user_id = auth.uid()
    )
  );

CREATE POLICY "Allow users to delete messages in their own sessions"
  ON public.messages FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.chat_sessions
      WHERE public.chat_sessions.id = public.messages.session_id
      AND public.chat_sessions.user_id = auth.uid()
    )
  );
