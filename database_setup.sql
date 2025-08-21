-- Database setup for Socratic Chatbot with Supabase Auth
-- Run these commands in your Supabase SQL editor

-- Note: We use Supabase's built-in auth.users table which contains:
-- - id (UUID)
-- - email
-- - created_at
-- - last_sign_in_at

-- 1. Create user_profiles table linked to auth.users
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    user_role TEXT CHECK (user_role IN ('admin', 'student', 'tester')) NOT NULL DEFAULT 'student',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create a function to automatically insert a user profile when a user is created
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, user_role)
    VALUES (NEW.id, 'student');  -- Default role is 'student'
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a trigger to call the function
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Enable Row Level Security for user_profiles
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Create policies for user_profiles table
CREATE POLICY "Users can view own profile" ON public.user_profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Admins can update user roles" ON public.user_profiles
    FOR UPDATE 
    TO authenticated 
    USING ((SELECT user_role FROM public.user_profiles WHERE id = auth.uid()) = 'admin')
    WITH CHECK ((SELECT user_role FROM public.user_profiles WHERE id = auth.uid()) = 'admin');

-- 2. Create chats table to track chat sessions
CREATE TABLE IF NOT EXISTS public.chats (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    mode VARCHAR(20) NOT NULL CHECK (mode IN ('Sokrates', 'Aristoteles')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security for chats
ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;

-- Create policies for chats table
CREATE POLICY "Users can view own chats" ON public.chats
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own chats" ON public.chats
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- 3. Create chat_messages table
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER REFERENCES public.chats(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    feedback_rating INTEGER CHECK (feedback_rating IN (0, 1)),  -- 0 for thumbs down, 1 for thumbs up
    feedback_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security for chat_messages
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- Create policies for chat_messages table
CREATE POLICY "Users can view messages from own chats" ON public.chat_messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.chats 
            WHERE chats.id = chat_messages.chat_id 
            AND chats.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert messages to own chats" ON public.chat_messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.chats 
            WHERE chats.id = chat_messages.chat_id 
            AND chats.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update own chat messages" ON public.chat_messages
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.chats 
            WHERE chats.id = chat_messages.chat_id 
            AND chats.user_id = auth.uid()
        )
    ) WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.chats 
            WHERE chats.id = chat_messages.chat_id 
            AND chats.user_id = auth.uid()
        )
    );

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON public.user_profiles(id);
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON public.chats(user_id);
CREATE INDEX IF NOT EXISTS idx_chats_created_at ON public.chats(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_id ON public.chat_messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON public.chat_messages(created_at);
