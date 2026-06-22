import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { DocumentItem } from '../types';
import { supabase } from '../supabaseClient';
import { User } from '@supabase/supabase-js';

const BACKEND_URL = (import.meta as any).env.VITE_BACKEND_URL || 
  ((import.meta as any).env.DEV ? 'http://localhost:8000' : 'https://agentic-rag-fullstack-1.onrender.com');

const IKIGAI_DEMO_DOC: DocumentItem = {
  id: 'ikigai-default-doc-id',
  name: 'Ikigai.pdf',
  chunksCount: 847,
  status: 'indexed',
  timestamp: 'Pre-indexed Demo'
};

export function useDocuments(user: User | null, onUploadSuccess?: () => void) {
  const [documents, setDocuments] = useState<DocumentItem[]>([IKIGAI_DEMO_DOC]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [activeFilters, setActiveFilters] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load documents when user changes
  useEffect(() => {
    if (user) {
      const loadUserDocuments = async () => {
        try {
          const { data: docs, error } = await supabase
            .from('documents')
            .select('*')
            .order('created_at', { ascending: false });

          if (error) throw error;

          const mappedDocs = (docs || []).map(d => ({
            id: d.id,
            name: d.name,
            chunksCount: d.chunks_count,
            status: d.status,
            timestamp: new Date(d.created_at).toLocaleDateString()
          }));
          setDocuments(mappedDocs);
        } catch (err) {
          console.error('Error loading documents:', err);
        }
      };
      loadUserDocuments();
    } else {
      // Check if guest has deleted the demo document
      const deleted: string[] = JSON.parse(localStorage.getItem('deletedDocIds') || '[]');
      if (deleted.includes(IKIGAI_DEMO_DOC.id)) {
        setDocuments([]);
      } else {
        setDocuments([IKIGAI_DEMO_DOC]);
      }
    }
  }, [user]);

  const toggleFilter = (filename: string) => {
    setActiveFilters(prev => 
      prev.includes(filename) 
        ? prev.filter(f => f !== filename) 
        : [...prev, filename]
    );
  };

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
      const session = (await supabase.auth.getSession()).data.session;
      const headers: any = { 'Content-Type': 'multipart/form-data' };
      if (session) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }
      const response = await axios.post(`${BACKEND_URL}/api/upload`, formData, {
        headers: headers
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
      
      setTimeout(() => {
        setIsUploading(false);
        setUploadStatus('');
        if (onUploadSuccess) onUploadSuccess();
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

  const deleteDocument = async (id: string, name: string) => {
    const IS_DEMO_DOC = id === 'ikigai-default-doc-id';

    setDocuments(prev => prev.filter(doc => doc.id !== id));
    setActiveFilters(prev => prev.filter(f => f !== name));

    if (!IS_DEMO_DOC) {
      try {
        const session = (await supabase.auth.getSession()).data.session;
        const headers: any = {};
        if (session) {
          headers['Authorization'] = `Bearer ${session.access_token}`;
        }
        await fetch(`${BACKEND_URL}/api/documents/${id}`, { 
          method: 'DELETE',
          headers: headers
        });
      } catch (err) {
        console.error('Error deleting document vectors from Pinecone:', err);
      }

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
  };

  return {
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
    uploadFile,
    deleteDocument
  };
}
