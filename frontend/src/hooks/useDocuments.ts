import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { DocumentItem } from '../types';
import { supabase } from '../supabaseClient';
import { User } from '@supabase/supabase-js';
import { BACKEND_URL, DEMO_DOCUMENT_ID, MAX_UPLOAD_MB, SUPPORTED_UPLOAD_EXTENSIONS } from '../config';

const IKIGAI_DEMO_DOC: DocumentItem = {
  id: DEMO_DOCUMENT_ID,
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

  // Keyed on the id, not the user object: Supabase hands back a new object on every token
  // refresh, which would otherwise clear the selected document filters mid-session.
  const userId = user?.id ?? null;

  // Load documents when user changes
  useEffect(() => {
    let cancelled = false;

    // Filters reference filenames from the previous identity's library, so reset them.
    setActiveFilters([]);

    if (user) {
      const loadUserDocuments = async () => {
        // RLS restricts this to the caller's rows; the explicit filter keeps the intent clear
        // and keeps the query correct even if policies are ever relaxed.
        const { data: docs, error } = await supabase
          .from('documents')
          .select('*')
          .eq('user_id', user.id)
          .order('created_at', { ascending: false });

        if (cancelled) return;

        if (error) {
          console.error('Error loading documents:', error);
          setDocuments([IKIGAI_DEMO_DOC]);
          return;
        }

        const mappedDocs = (docs || []).map(d => ({
          id: d.id,
          name: d.name,
          chunksCount: d.chunks_count,
          status: d.status,
          timestamp: new Date(d.created_at).toLocaleDateString()
        }));
        // The shared demo document is queryable by everyone, so keep it listed alongside
        // the user's own library.
        setDocuments([...mappedDocs, IKIGAI_DEMO_DOC]);
      };
      loadUserDocuments();
    } else {
      // Check if guest has deleted the demo document
      const deleted: string[] = readDeletedIds();
      setDocuments(deleted.includes(IKIGAI_DEMO_DOC.id) ? [] : [IKIGAI_DEMO_DOC]);
    }

    return () => {
      cancelled = true;
    };
  }, [userId]);

  const readDeletedIds = (): string[] => {
    try {
      const parsed = JSON.parse(localStorage.getItem('deletedDocIds') || '[]');
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  };

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
      // Allow re-selecting the same file after a failed attempt.
      e.target.value = '';
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  const failUpload = (message: string) => {
    setUploadStatus(message);
    setTimeout(() => {
      setIsUploading(false);
      setUploadStatus('');
    }, 4000);
  };

  const uploadFile = async (file: File) => {
    if (isUploading) return;

    setIsUploading(true);
    setUploadStatus('Validating...');

    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !SUPPORTED_UPLOAD_EXTENSIONS.includes(ext)) {
      failUpload('Unsupported file format.');
      return;
    }

    if (file.size === 0) {
      failUpload('That file is empty.');
      return;
    }

    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      failUpload(`File is larger than the ${MAX_UPLOAD_MB} MB limit.`);
      return;
    }

    const session = (await supabase.auth.getSession()).data.session;
    if (!session) {
      // Indexing requires an owner so the document can be scoped to you on retrieval.
      failUpload('Sign in to upload and index documents.');
      return;
    }

    setUploadStatus('Parsing & Chunking...');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${BACKEND_URL}/api/upload`, formData, {
        headers: { Authorization: `Bearer ${session.access_token}` }
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

      const { error: insertError } = await supabase.from('documents').insert({
        id: data.document_id,
        user_id: session.user.id,
        name: data.filename,
        chunks_count: data.chunks_created,
        status: data.status
      });

      if (insertError) {
        // The vectors exist but the library row does not; say so rather than showing a
        // document that silently disappears on the next reload.
        console.error('Error saving document metadata:', insertError);
        failUpload('Indexed, but saving to your library failed. Please retry.');
        return;
      }

      setDocuments(prev => [newDoc, ...prev]);
      setUploadStatus('Ingested & Indexed!');

      setTimeout(() => {
        setIsUploading(false);
        setUploadStatus('');
        if (onUploadSuccess) onUploadSuccess();
      }, 1500);

    } catch (error: any) {
      console.error(error);
      const errMsg = error.response?.data?.detail || error.message || 'Server error';
      failUpload(`Error: ${errMsg}`);
    }
  };

  const deleteDocument = async (id: string, name: string) => {
    const isDemoDoc = id === DEMO_DOCUMENT_ID;

    const previousDocuments = documents;
    setDocuments(prev => prev.filter(doc => doc.id !== id));
    setActiveFilters(prev => prev.filter(f => f !== name));

    if (isDemoDoc) {
      // The shared demo document is not owned by anyone and stays in the index; guests and
      // signed-in users simply hide it locally.
      const deleted = readDeletedIds();
      if (!deleted.includes(id)) {
        localStorage.setItem('deletedDocIds', JSON.stringify([...deleted, id]));
      }
      return;
    }

    try {
      const session = (await supabase.auth.getSession()).data.session;
      if (!session) {
        throw new Error('You must be signed in to delete documents.');
      }

      const response = await fetch(`${BACKEND_URL}/api/documents/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${session.access_token}` }
      });

      if (!response.ok) {
        throw new Error(`Vector deletion failed with status ${response.status}`);
      }

      const { error: deleteError } = await supabase.from('documents').delete().eq('id', id);
      if (deleteError) throw deleteError;
    } catch (err) {
      // Restore the entry: leaving it hidden would suggest the document was removed when
      // its vectors are still indexed and still searchable.
      console.error('Error deleting document:', err);
      setDocuments(previousDocuments);
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
