-- Database setup for Socratic Chatbot with Supabase Auth
-- Run these commands in your Supabase SQL editor

-- Note: We'll use Supabase's built-in auth.users table which already contains:
-- - id (UUID)
-- - email
-- - created_at
-- - last_sign_in_at
-- - email_confirmed_at
-- No need for additional user_profiles table

-- Create chat_history table
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history(created_at);

-- Enable Row Level Security (RLS)
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;

-- Create policies for chat_history table
-- Note: For now, we'll use more permissive policies since we're handling auth in the app
CREATE POLICY "Enable read access for authenticated users" ON chat_history
    FOR SELECT USING (true);

CREATE POLICY "Enable insert access for authenticated users" ON chat_history
    FOR INSERT WITH CHECK (true);

-- If you want stricter RLS later, you can replace these with:
-- CREATE POLICY "Users can read their own chat history" ON chat_history
--     FOR SELECT USING (auth.uid() = user_id);
-- CREATE POLICY "Users can insert their own chat messages" ON chat_history
--     FOR INSERT WITH CHECK (auth.uid() = user_id);
