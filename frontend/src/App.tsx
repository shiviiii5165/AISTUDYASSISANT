import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import Dashboard from './pages/Dashboard';
import LibraryPage from './pages/LibraryPage';
import ChatPage from './pages/ChatPage';
import PricingPage from './pages/PricingPage';
import PaymentVerifyPage from './pages/PaymentVerifyPage';
import SupportPage from './pages/SupportPage';
import { useAuthStore } from './store/useAuthStore';
import CookieConsent from './components/CookieConsent';

// Legal Pages
import PrivacyPolicy from './pages/legal/PrivacyPolicy';
import CookiePolicy from './pages/legal/CookiePolicy';
import TermsOfService from './pages/legal/TermsOfService';

// SEO Pages
import AITutorPage from './pages/seo/AITutorPage';
import PDFChatPage from './pages/seo/PDFChatPage';
import MCQGeneratorPage from './pages/seo/MCQGeneratorPage';
import ExamPrepPage from './pages/seo/ExamPrepPage';
import DoubtSolverPage from './pages/seo/DoubtSolverPage';
import ChatGPTAlternativePage from './pages/seo/ChatGPTAlternativePage';
import AIToolsForStudentsPage from './pages/seo/AIToolsForStudentsPage';
import FreeMCQGeneratorPage from './pages/seo/FreeMCQGeneratorPage';

// Blog Pages
import BlogIndexPage from './pages/blog/BlogIndexPage';
import BlogPostPage from './pages/blog/BlogPostPage';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { session, loading } = useAuthStore();
  
  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-3 border-[var(--accent-green)] border-t-transparent rounded-full animate-spin" />
          <span className="text-[var(--text-secondary)] text-sm font-medium">Loading...</span>
        </div>
      </div>
    );
  }
  
  if (!session) {
    return <Navigate to="/auth" replace />;
  }
  
  return <>{children}</>;
};

function App() {
  const { initializeAuth } = useAuthStore();

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  return (
    <HelmetProvider>
      <BrowserRouter>
        <CookieConsent />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route 
            path="/payment/verify" 
            element={
              <ProtectedRoute>
                <PaymentVerifyPage />
              </ProtectedRoute>
            } 
          />
          
          {/* Legal Pages */}
          <Route path="/privacy-policy" element={<PrivacyPolicy />} />
          <Route path="/cookie-policy" element={<CookiePolicy />} />
          <Route path="/terms-of-service" element={<TermsOfService />} />
          
          {/* SEO Pages */}
          <Route path="/ai-tutor-for-students" element={<AITutorPage />} />
          <Route path="/pdf-chat-ai" element={<PDFChatPage />} />
          <Route path="/mcq-generator" element={<MCQGeneratorPage />} />
          <Route path="/exam-preparation-ai" element={<ExamPrepPage />} />
          <Route path="/doubt-solver" element={<DoubtSolverPage />} />
          <Route path="/chatgpt-alternative-for-students" element={<ChatGPTAlternativePage />} />
          <Route path="/ai-tools-for-students" element={<AIToolsForStudentsPage />} />
          <Route path="/free-mcq-generator" element={<FreeMCQGeneratorPage />} />
          
          {/* Blog Pages */}
          <Route path="/blog" element={<BlogIndexPage />} />
          <Route path="/blog/:slug" element={<BlogPostPage />} />
          
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/library" 
            element={
              <ProtectedRoute>
                <LibraryPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/chat" 
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/support" 
            element={
              <ProtectedRoute>
                <SupportPage />
              </ProtectedRoute>
            } 
          />
        </Routes>
      </BrowserRouter>
    </HelmetProvider>
  );
}

export default App;
