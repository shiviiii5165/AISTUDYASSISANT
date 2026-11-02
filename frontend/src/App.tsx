import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import Dashboard from './pages/Dashboard';
import LibraryPage from './pages/LibraryPage';
import ChatPage from './pages/ChatPage';
import TopicDeckPage from './pages/TopicDeckPage';
import TeachMePage from './pages/TeachMePage';
import VideoGeneratorPage from './pages/VideoGeneratorPage';
import PricingPage from './pages/PricingPage';
import PaymentVerifyPage from './pages/PaymentVerifyPage';
import SupportPage from './pages/SupportPage';
import LessonPlannerPage from './pages/LessonPlannerPage';
import QuizGeneratorPage from './pages/QuizGeneratorPage';
import QuizPage from './pages/QuizPage';
import JoinLiveQuizPage from './pages/JoinLiveQuizPage';
import NotesGeneratorPage from './pages/NotesGeneratorPage';
import LearnerProfilePage from './pages/LearnerProfilePage';
import DiagnosticPage from './pages/DiagnosticPage';
import { MasteryMapPage } from './pages/MasteryMapPage';
import MistakesPage from './pages/MistakesPage';
import PracticePage from './pages/PracticePage';
import { TransferCheckPage } from './pages/TransferCheckPage';
import StepCheckPage from './pages/StepCheckPage';
import LearnStudioPage from './pages/LearnStudioPage';

// Specialized & Institutional Portals
import ParentDashboard from './pages/parent/ParentDashboard';
import ChildDetailPage from './pages/parent/ChildDetailPage';
import TeacherDashboard from './pages/teacher/TeacherDashboard';
import ClassroomDetailPage from './pages/teacher/ClassroomDetailPage';
import SchoolAdminDashboard from './pages/school_admin/SchoolAdminDashboard';
import CreatorDashboard from './pages/creator/CreatorDashboard';
import SuperAdminDashboard from './pages/admin/SuperAdminDashboard';

// Architectural Role Guard & Portal Dispatcher
import RoleGuard from './components/RoleGuard';
import DashboardDispatcher from './components/DashboardDispatcher';

// Lazy-loaded Live Quiz routes for strict code-splitting (§14)
const LiveQuizHostPage = React.lazy(() => import('./pages/LiveQuizHostPage'));
const LiveQuizParticipantPage = React.lazy(() => import('./pages/LiveQuizParticipantPage'));
const LiveQuizReportPage = React.lazy(() => import('./pages/LiveQuizReportPage'));


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
      <div className="min-h-[100dvh] bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-3 border-[var(--accent-green)] border-t-transparent rounded-full animate-spin" />
          <span className="text-[var(--text-secondary)] text-sm font-medium">Loading...</span>
        </div>
      </div>
    );
  }
  
  if (!session) {
    if (
      import.meta.env.DEV &&
      typeof window !== 'undefined' &&
      (window.location.search.includes('mock_auth=true') ||
        localStorage.getItem('learnbygenie_dev_auth') === 'true' ||
        localStorage.getItem('teachgenie_dev_auth') === 'true')
    ) {
      return <>{children}</>;
    }
    return <Navigate to="/auth" replace />;
  }
  
  return <>{children}</>;
};

function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
    const main = document.querySelector('main');
    if (main) {
      main.scrollTo(0, 0);
    }
  }, [pathname]);

  return null;
}

function App() {
  const { initializeAuth } = useAuthStore();

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  return (
    <HelmetProvider>
      <BrowserRouter>
        <ScrollToTop />
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
            element={<DashboardDispatcher />} 
          />
          <Route 
            path="/profile" 
            element={
              <ProtectedRoute>
                <LearnerProfilePage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/diagnostic" 
            element={
              <ProtectedRoute>
                <DiagnosticPage />
              </ProtectedRoute>
            } 
          />
          <Route
            path="/studio"
            element={
              <ProtectedRoute>
                <LearnStudioPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/mastery"
            element={
              <ProtectedRoute>
                <MasteryMapPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/mastery-map" 
            element={
              <ProtectedRoute>
                <MasteryMapPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/mistakes" 
            element={
              <ProtectedRoute>
                <MistakesPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/practice" 
            element={
              <ProtectedRoute>
                <PracticePage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/transfer-check" 
            element={
              <ProtectedRoute>
                <TransferCheckPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/step-check" 
            element={
              <ProtectedRoute>
                <StepCheckPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/teach" 
            element={
              <ProtectedRoute>
                <TeachMePage />
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
            path="/notes" 
            element={
              <ProtectedRoute>
                <NotesGeneratorPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/decks" 
            element={
              <RoleGuard allowedRoles={['teacher', 'content_creator']}>
                <TopicDeckPage />
              </RoleGuard>
            } 
          />
          <Route 
            path="/quizzes" 
            element={
              <ProtectedRoute>
                <QuizGeneratorPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/quiz/:quizId" 
            element={
              <ProtectedRoute>
                <QuizPage />
              </ProtectedRoute>
            } 
          />
          <Route path="/join" element={<JoinLiveQuizPage />} />
          <Route 
            path="/quiz/:quizId/live" 
            element={
              <RoleGuard allowedRoles={['teacher']}>
                <React.Suspense fallback={<div className="flex h-screen items-center justify-center"><div className="w-8 h-8 border-2 border-[var(--accent-royal)] border-t-transparent rounded-full animate-spin" /></div>}>
                  <LiveQuizHostPage />
                </React.Suspense>
              </RoleGuard>
            } 
          />
          <Route 
            path="/live/:sessionId" 
            element={
              <React.Suspense fallback={<div className="flex h-screen items-center justify-center"><div className="w-8 h-8 border-2 border-[var(--accent-royal)] border-t-transparent rounded-full animate-spin" /></div>}>
                <LiveQuizParticipantPage />
              </React.Suspense>
            } 
          />
          <Route 
            path="/live/:sessionId/report" 
            element={
              <React.Suspense fallback={<div className="flex h-screen items-center justify-center"><div className="w-8 h-8 border-2 border-[var(--accent-royal)] border-t-transparent rounded-full animate-spin" /></div>}>
                <LiveQuizReportPage />
              </React.Suspense>
            } 
          />
          <Route 
            path="/video" 
            element={
              <RoleGuard allowedRoles={['teacher', 'content_creator']}>
                <VideoGeneratorPage />
              </RoleGuard>
            } 
          />
          <Route 
            path="/lesson-planner" 
            element={
              <RoleGuard allowedRoles={['teacher', 'school_admin']}>
                <LessonPlannerPage />
              </RoleGuard>
            } 
          />
          {/* Institutional & Specialized Portals Guarded by Server-Verified Roles */}
          <Route 
            path="/parent" 
            element={
              <RoleGuard allowedRoles={['parent']}>
                <ParentDashboard />
              </RoleGuard>
            } 
          />
          <Route 
            path="/parent/child/:id" 
            element={
              <RoleGuard allowedRoles={['parent']}>
                <ChildDetailPage />
              </RoleGuard>
            } 
          />
          <Route 
            path="/teacher" 
            element={
              <RoleGuard allowedRoles={['teacher']}>
                <TeacherDashboard />
              </RoleGuard>
            } 
          />
          <Route 
            path="/teacher/classroom/:id" 
            element={
              <RoleGuard allowedRoles={['teacher']}>
                <ClassroomDetailPage />
              </RoleGuard>
            } 
          />
          <Route 
            path="/school-admin" 
            element={
              <RoleGuard allowedRoles={['school_admin']}>
                <SchoolAdminDashboard />
              </RoleGuard>
            } 
          />
          <Route 
            path="/creator" 
            element={
              <RoleGuard allowedRoles={['content_creator']}>
                <CreatorDashboard />
              </RoleGuard>
            } 
          />
          <Route 
            path="/admin" 
            element={
              <RoleGuard allowedRoles={['super_admin']}>
                <SuperAdminDashboard />
              </RoleGuard>
            } 
          />
          <Route path="/support" element={<SupportPage />} />
        </Routes>
      </BrowserRouter>
    </HelmetProvider>
  );
}

export default App;
