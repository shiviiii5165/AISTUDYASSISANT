import { create } from 'zustand';
import { supabase } from '../lib/supabase';

export type UserRole =
  | 'student'
  | 'parent'
  | 'teacher'
  | 'school_admin'
  | 'content_creator'
  | 'super_admin';

export interface UserProfile {
  id: string;
  email: string | undefined;
  full_name?: string;
  avatar_url?: string;
  plan?: string;
  role?: UserRole;
}

interface AuthState {
  user: UserProfile | null;
  session: any | null;
  loading: boolean;
  activeRole: UserRole;
  setActiveRole: (role: UserRole) => void;
  setUser: (user: UserProfile | null) => void;
  setSession: (session: any | null) => void;
  signOut: () => Promise<void>;
  initializeAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  session: null,
  loading: true,
  activeRole:
    (typeof window !== 'undefined' &&
      (localStorage.getItem('learnbygenie_active_role') as UserRole)) ||
    'student',

  setActiveRole: (role: UserRole) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('learnbygenie_active_role', role);
    }
    set({ activeRole: role });
  },

  setUser: (user) => set({ user }),
  setSession: (session) => set({ session }),

  signOut: async () => {
    await supabase.auth.signOut();
    set({ user: null, session: null });
  },

  initializeAuth: async () => {
    try {
      const isDevAuth =
        typeof window !== 'undefined' &&
        (window.location.search.includes('mock_auth=true') ||
          localStorage.getItem('learnbygenie_dev_auth') === 'true' ||
          localStorage.getItem('teachgenie_dev_auth') === 'true');

      if (import.meta.env.DEV && isDevAuth) {
        if (window.location.search.includes('mock_auth=true')) {
          localStorage.setItem('learnbygenie_dev_auth', 'true');
          localStorage.setItem('teachgenie_dev_auth', 'true');
        }
        const devUser: UserProfile = {
          id: '00000000-0000-0000-0000-000000000001',
          email: 'teacher@learnbygenie.com',
          full_name: 'Teacher Jane',
          plan: 'pro',
          role: 'teacher'
        };
        const devSession = {
          access_token: 'mock-dev-token',
          user: { id: devUser.id, email: devUser.email }
        };
        set({ user: devUser, session: devSession, loading: false });
        return;
      }

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
            plan: 'free',
            role: (session.user.user_metadata?.role as UserRole) || 'student',
          },
        });
        syncUserProfile(session);
        
        // Fetch plan and role
        supabase.from('profiles').select('plan, role').eq('id', session.user.id).single()
          .then(({ data }) => {
            if (data) {
              set((state) => ({
                user: state.user
                  ? {
                      ...state.user,
                      plan: data.plan || state.user.plan,
                      role: (data.role as UserRole) || state.user.role,
                    }
                  : null,
              }));
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
              role: (session.user.user_metadata?.role as UserRole) || 'student',
            },
          });
          if (event === 'SIGNED_IN') {
            syncUserProfile(session);
            supabase.from('profiles').select('plan, role').eq('id', session.user.id).single()
              .then(({ data }) => {
                if (data) {
                  set((state) => ({
                    user: state.user
                      ? {
                          ...state.user,
                          plan: data.plan || state.user.plan,
                          role: (data.role as UserRole) || state.user.role,
                        }
                      : null,
                  }));
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
