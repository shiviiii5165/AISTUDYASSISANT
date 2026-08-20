import psycopg2
import os

# NEVER hardcode credentials — use environment variables
CONNECTION_STRING = os.environ.get("DATABASE_URL", "")

if not CONNECTION_STRING:
    print("WARNING: DATABASE_URL environment variable is not set.")
    print("Set it like: DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres")

SCHEMA_SQL = """
-- Users (handled by Supabase Auth, extend with profile)
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY,
  full_name TEXT,
  email TEXT,
  avatar_url TEXT,
  provider TEXT DEFAULT 'email',
  exam_target TEXT, -- 'JEE', 'NEET', 'UPSC', etc.
  plan TEXT DEFAULT 'free', -- 'free' or 'pro'
  subscription_status TEXT DEFAULT 'inactive',
  subscription_end_date TIMESTAMPTZ,
  streak_count INTEGER DEFAULT 0,
  last_active DATE,
  last_login_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- PDFs
CREATE TABLE IF NOT EXISTS pdfs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  subject TEXT DEFAULT 'General',
  status TEXT DEFAULT 'processing', -- 'processing', 'ready', 'error'
  page_count INTEGER,
  file_url TEXT,
  source_type TEXT DEFAULT 'pdf', -- 'pdf' or 'handwritten'
  created_at TIMESTAMP DEFAULT NOW()
);

-- Chat History
CREATE TABLE IF NOT EXISTS chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  pdf_id UUID REFERENCES pdfs(id) ON DELETE CASCADE,
  role TEXT NOT NULL, -- 'user' or 'assistant'
  content TEXT NOT NULL,
  sources JSONB, -- [{page: 3, text: "..."}]
  created_at TIMESTAMP DEFAULT NOW()
);

-- Quiz Results
CREATE TABLE IF NOT EXISTS quiz_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  pdf_id UUID REFERENCES pdfs(id) ON DELETE CASCADE,
  score INTEGER,
  total INTEGER,
  topic TEXT,
  answers JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Daily Activity (for streak tracking)
CREATE TABLE IF NOT EXISTS daily_activity (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  questions_asked INTEGER DEFAULT 0,
  quizzes_taken INTEGER DEFAULT 0,
  UNIQUE(user_id, date)
);
"""

def init_db():
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(CONNECTION_STRING)
        cur = conn.cursor()
        
        print("Executing schema...")
        cur.execute(SCHEMA_SQL)
        conn.commit()
        
        cur.close()
        conn.close()
        print("Database schema successfully initialized!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    init_db()
