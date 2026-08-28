import { useState, useEffect } from 'react';
import { supabase } from '../supabaseClient';
import { User } from '@supabase/supabase-js';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Sync auth state on mount and listener
  useEffect(() => {
    // Supabase re-emits auth events with a freshly constructed user object for the *same*
    // person - on TOKEN_REFRESHED, and again when the tab regains focus. Storing every
    // emission would change the `user` reference and re-run every effect keyed on it,
    // including the one that aborts an in-flight chat stream. Keep the previous object
    // whenever the identity has not actually changed so React can bail out of the update.
    const applyUser = (next: User | null) =>
      setUser(prev => (prev?.id === next?.id ? prev : next));

    supabase.auth.getSession().then(({ data: { session } }) => {
      applyUser(session?.user ?? null);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      applyUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  return {
    user,
    isAuthModalOpen,
    setIsAuthModalOpen,
    handleLogout
  };
}
