import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Lock, User as UserIcon, Loader2, ArrowRight } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useAuthStore } from '../store/useAuthStore';
import SEO from '../components/SEO';

const AuthPage: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [googleLoading, setGoogleLoading] = useState(false);
  const navigate = useNavigate();
  const { setSession, setUser } = useAuthStore();

  const handleGoogleSignIn = async () => {
    setGoogleLoading(true);
    setError('');
    try {
      const { error: authError } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/dashboard`,
          queryParams: {
            prompt: 'select_account'
          }
        }
      });
      if (authError) throw authError;
    } catch (err: any) {
      setError(err.message || 'Failed to sign in with Google');
      setGoogleLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccessMsg('');

    try {
      if (isLogin) {
        const { data, error: authError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (authError) throw authError;

        if (data.session) {
          setSession(data.session);
          setUser({
            id: data.session.user.id,
            email: data.session.user.email,
            full_name: data.session.user.user_metadata?.full_name,
          });
          navigate('/dashboard');
        }
      } else {
        const { data, error: authError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: fullName,
            },
          },
        });

        if (authError) throw authError;

        if (data.session) {
          // Auto-confirmed (e.g., in dev or if email confirm is disabled)
          setSession(data.session);
          setUser({
            id: data.session.user.id,
            email: data.session.user.email,
            full_name: fullName,
          });
          navigate('/dashboard');
        } else {
          // Email confirmation required
          setSuccessMsg('Account created! Check your email to confirm your account.');
        }
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[100dvh] flex items-center justify-center bg-[var(--bg-secondary)] p-4 relative overflow-hidden">
      <SEO 
        title={isLogin ? 'Log In' : 'Sign Up'} 
        description="Log in or sign up to TeachGenie to access your AI study assistant and chat with your notes." 
      />
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-[var(--accent-green)] opacity-[0.04] rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-[var(--accent-green)] opacity-[0.04] rounded-full blur-3xl" />
      </div>

      <div className="bg-white p-6 md:p-8 rounded-xl shadow-[var(--shadow-lg)] w-full max-w-sm border border-[var(--border)] relative z-10">
        <div className="flex items-center justify-center gap-2 mb-6">
          <img src="/logo.png" alt="TeachGenie Logo" className="w-8 h-8 object-contain" />
          <span className="text-xl font-bold text-[var(--text-primary)]">TeachGenie</span>
        </div>

        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-0.5 text-center">
          {isLogin ? 'Welcome back' : 'Create an account'}
        </h2>
        <p className="text-[var(--text-secondary)] text-center mb-6 text-xs">
          {isLogin ? 'Log in to continue learning' : 'Join TeachGenie and learn from your notes'}
        </p>

        {/* Error / Success messages */}
        {error && (
          <div className="mb-3 p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs font-medium flex items-start gap-2">
            <span className="shrink-0 mt-0.5">⚠️</span>
            <span>{error}</span>
          </div>
        )}
        {successMsg && (
          <div className="mb-3 p-2.5 rounded-lg bg-green-50 border border-green-200 text-green-700 text-xs font-medium flex items-start gap-2">
            <span className="shrink-0 mt-0.5">✅</span>
            <span>{successMsg}</span>
          </div>
        )}

        <button
          onClick={handleGoogleSignIn}
          disabled={loading || googleLoading}
          className="w-full bg-white border border-[var(--border)] text-[var(--text-primary)] font-medium py-2.5 rounded-lg shadow-[var(--shadow-sm)] hover:bg-gray-50 transition-all mb-5 flex items-center justify-center gap-2.5 disabled:opacity-60 disabled:cursor-not-allowed text-sm"
        >
          {googleLoading ? (
            <Loader2 className="w-5 h-5 animate-spin text-gray-500" />
          ) : (
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25C22.56 11.47 22.49 10.72 22.36 10H12V14.26H17.92C17.67 15.63 16.89 16.79 15.73 17.57V20.34H19.29C21.37 18.42 22.56 15.6 22.56 12.25Z" fill="#4285F4"/>
              <path d="M12 23C14.97 23 17.46 22.02 19.29 20.34L15.73 17.57C14.74 18.23 13.48 18.63 12 18.63C9.13 18.63 6.7 16.69 5.84 14.1H2.18V16.94C3.99 20.53 7.7 23 12 23Z" fill="#34A853"/>
              <path d="M5.84 14.1C5.62 13.44 5.49 12.73 5.49 12C5.49 11.27 5.62 10.56 5.84 9.9V7.06H2.18C1.43 8.55 1 10.22 1 12C1 13.78 1.43 15.45 2.18 16.94L5.84 14.1Z" fill="#FBBC05"/>
              <path d="M12 5.38C13.62 5.38 15.06 5.93 16.2 7.02L19.36 3.86C17.45 2.08 14.97 1 12 1C7.7 1 3.99 3.47 2.18 7.06L5.84 9.9C6.7 7.31 9.13 5.38 12 5.38Z" fill="#EA4335"/>
            </svg>
          )}
          <span>Continue with Google</span>
        </button>

        <div className="relative flex items-center mb-5">
          <div className="flex-grow border-t border-[var(--border)]"></div>
          <span className="shrink-0 px-3 text-[10px] font-medium text-[var(--text-muted)] uppercase tracking-wider">
            Or continue with email
          </span>
          <div className="flex-grow border-t border-[var(--border)]"></div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {!isLogin && (
            <div>
              <label className="block text-xs font-medium text-[var(--text-primary)] mb-1">Full Name</label>
              <div className="relative">
                <UserIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] w-4.5 h-4.5" />
                <input
                  type="text"
                  placeholder="Rahul Kumar"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full pl-10 pr-3 py-2.5 rounded-lg border border-[var(--border)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-green)] focus:border-transparent transition-all bg-[var(--bg-primary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] text-sm"
                  required
                  disabled={loading}
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-[var(--text-primary)] mb-1">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] w-4.5 h-4.5" />
              <input
                type="email"
                placeholder="student@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-3 py-2.5 rounded-lg border border-[var(--border)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-green)] focus:border-transparent transition-all bg-[var(--bg-primary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] text-sm"
                required
                disabled={loading}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[var(--text-primary)] mb-1">Password</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] w-4.5 h-4.5" />
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-3 py-2.5 rounded-lg border border-[var(--border)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-green)] focus:border-transparent transition-all bg-[var(--bg-primary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] text-sm"
                required
                minLength={6}
                disabled={loading}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[var(--accent-green)] text-white font-semibold py-2.5 rounded-lg shadow-sm hover:bg-[var(--accent-green-hover)] transition-all mt-4 flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed text-sm"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                {isLogin ? 'Log in' : 'Sign up'}
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-5 text-center">
          <button
            onClick={() => {
              setIsLogin(!isLogin);
              setError('');
              setSuccessMsg('');
            }}
            className="text-[var(--accent-green-text)] font-medium hover:underline text-sm"
            disabled={loading}
          >
            {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Log in'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;
