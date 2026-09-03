-- ============================================================================
-- TeachGenie — URGENT RLS Security Fixes
-- Enable RLS on vulnerable production tables and secure handle_new_user()
-- ============================================================================

DO $$
BEGIN
  -- 1. Enable RLS for all 5 vulnerable tables
  ALTER TABLE IF EXISTS public.pdfs ENABLE ROW LEVEL SECURITY;
  ALTER TABLE IF EXISTS public.chat_messages ENABLE ROW LEVEL SECURITY;
  ALTER TABLE IF EXISTS public.quiz_results ENABLE ROW LEVEL SECURITY;
  ALTER TABLE IF EXISTS public.daily_activity ENABLE ROW LEVEL SECURITY;
  ALTER TABLE IF EXISTS public.profiles ENABLE ROW LEVEL SECURITY;

  -- (Optional) Drop existing policies if any were partially created to avoid conflicts
  DROP POLICY IF EXISTS "Users can manage their own pdfs" ON public.pdfs;
  DROP POLICY IF EXISTS "Users can manage their own chat messages" ON public.chat_messages;
  DROP POLICY IF EXISTS "Users can manage their own quiz results" ON public.quiz_results;
  DROP POLICY IF EXISTS "Users can manage their own daily activity" ON public.daily_activity;
  DROP POLICY IF EXISTS "Users can manage their own profile" ON public.profiles;

  -- 2. PDFs (Direct Ownership)
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pdfs') THEN
    CREATE POLICY "Users can manage their own pdfs" ON public.pdfs
    FOR ALL USING (auth.uid() = user_id);
  END IF;

  -- 3. Daily Activity (Direct Ownership)
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'daily_activity') THEN
    CREATE POLICY "Users can manage their own daily activity" ON public.daily_activity
    FOR ALL USING (auth.uid() = user_id);
  END IF;

  -- 4. Profiles (ID matches UID)
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'profiles') THEN
    CREATE POLICY "Users can manage their own profile" ON public.profiles
    FOR ALL USING (auth.uid() = id);
  END IF;

  -- 5. Chat Messages (Check for session_id inheritance vs user_id direct)
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chat_messages' AND column_name = 'session_id') THEN
    CREATE POLICY "Users can manage their own chat messages" ON public.chat_messages
    FOR ALL USING (
      EXISTS (
        SELECT 1 FROM public.chat_sessions 
        WHERE chat_sessions.id = public.chat_messages.session_id 
        AND chat_sessions.user_id = auth.uid()
      )
    );
  ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chat_messages' AND column_name = 'user_id') THEN
    CREATE POLICY "Users can manage their own chat messages" ON public.chat_messages
    FOR ALL USING (auth.uid() = user_id);
  END IF;

  -- 6. Quiz Results (Check for quiz_id inheritance vs user_id direct)
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'quiz_results' AND column_name = 'quiz_id') THEN
    CREATE POLICY "Users can manage their own quiz results" ON public.quiz_results
    FOR ALL USING (
      EXISTS (
        SELECT 1 FROM public.quizzes
        WHERE quizzes.id = public.quiz_results.quiz_id
        AND quizzes.owner_user_id = auth.uid()
      )
    );
  ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'quiz_results' AND column_name = 'user_id') THEN
    CREATE POLICY "Users can manage their own quiz results" ON public.quiz_results
    FOR ALL USING (auth.uid() = user_id);
  END IF;

END $$;

-- 7. Fix SECURITY DEFINER vulnerability on handle_new_user()
ALTER FUNCTION public.handle_new_user() SET search_path = public;
