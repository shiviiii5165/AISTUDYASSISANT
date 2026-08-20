import { create } from 'zustand';
import { supabase } from '../lib/supabase';

interface UserProfile {
  id: string;
  email: string | undefined;
  full_name?: string;
  avatar_url?: string;
  plan?: string;
}

interface AuthState {
  user: UserProfile | null;
  session: any | null;
  loading: boolean;
  setUser: (user: UserProfile | null) => void;
  setSession: (session: any | null) => void;
  signOut: () => Promise<void>;
  initializeAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  session: null,
  loading: true,

  setUser: (user) => set({ user }),
  setSession: (session) => set({ session }),

  signOut: async () => {
    await supabase.auth.signOut();
    set({ user: null, session: null });
  },

  initializeAuth: async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      const syncUserProfile = async (currentSession: any) => {
        if (!currentSession?.user) return;
        
        const { user } = currentSession;
        const metadata = user.user_metadata || {};
        const fullName = metadata.full_name || metadata.name || '';
        const avatarUrl = metadata.avatar_url || metadata.picture || '';
        const provider = user.app_metadata?.provider || 'email';

        try {
          // Upsert the profile into our database
          await supabase.from('profiles').upsert({
            id: user.id,
            email: user.email,
            full_name: fullName,
            avatar_url: avatarUrl,
            provider: provider,
            last_login_at: new Date().toISOString(),
          }, { onConflict: 'id' });
        } catch (err) {
          console.error('Error syncing profile:', err);
        }
      };

      if (session) {
        set({
          session,
          user: {
            id: session.user.id,
            email: session.user.email,
            full_name: session.user.user_metadata?.full_name || session.user.user_metadata?.name,
            avatar_url: session.user.user_metadata?.avatar_url || session.user.user_metadata?.picture,
            plan: 'free', // Will be updated shortly
          },
        });
        syncUserProfile(session);
        
        // Fetch plan
        supabase.from('profiles').select('plan').eq('id', session.user.id).single()
          .then(({ data }) => {
            if (data?.plan) {
              set((state) => ({ user: state.user ? { ...state.user, plan: data.plan } : null }));
            }
          });
      }

      // Listen for auth changes
      supabase.auth.onAuthStateChange((event, session) => {
        if (session) {
          set({
            session,
            user: {
              id: session.user.id,
              email: session.user.email,
              full_name: session.user.user_metadata?.full_name || session.user.user_metadata?.name,
              avatar_url: session.user.user_metadata?.avatar_url || session.user.user_metadata?.picture,
              plan: 'free',
            },
          });
          if (event === 'SIGNED_IN') {
            syncUserProfile(session);
            supabase.from('profiles').select('plan').eq('id', session.user.id).single()
              .then(({ data }) => {
                if (data?.plan) {
                  set((state) => ({ user: state.user ? { ...state.user, plan: data.plan } : null }));
                }
              });
          }
        } else {
          set({ user: null, session: null });
        }
      });
    } catch (error) {
      console.error('Error initializing auth:', error);
    } finally {
      set({ loading: false });
    }
  },
}));
