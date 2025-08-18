-- Add missing UPDATE policy for feedback functionality
-- Run this in your Supabase SQL editor
CREATE POLICY "Users can update their own chat messages" ON chat_history
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);