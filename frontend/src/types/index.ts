export interface DocumentItem {
  id: string;
  name: string;
  chunksCount: number;
  status: string;
  timestamp: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
}

export interface SourceCitation {
  filename: string;
  chunk_id: string;
  page_number: number | null;
  relevance_score: number;
  context: string;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  sources: SourceCitation[];
  queryType: string | null;
}
