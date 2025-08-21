-- Add this function to your Supabase SQL editor to support the analytics dashboard
-- This function provides a consolidated view of chat data for analytics

CREATE OR REPLACE FUNCTION get_analytics_data()
RETURNS TABLE (
    id INTEGER,
    chat_id INTEGER,
    role VARCHAR(20),
    content TEXT,
    feedback_rating INTEGER,
    feedback_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    user_id UUID,
    chat_mode VARCHAR(20)
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT 
        cm.id,
        cm.chat_id,
        cm.role,
        cm.content,
        cm.feedback_rating,
        cm.feedback_text,
        cm.created_at,
        c.user_id,
        c.mode as chat_mode
    FROM chat_messages cm
    JOIN chats c ON cm.chat_id = c.id
    ORDER BY cm.created_at DESC;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION get_analytics_data() TO authenticated;
