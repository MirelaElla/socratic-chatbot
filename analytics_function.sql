-- Add this function to your Supabase SQL editor to support the analytics dashboard
-- This function provides a consolidated view of chat data for analytics
-- Note: This function uses SECURITY DEFINER to bypass RLS for analytics

CREATE OR REPLACE FUNCTION get_analytics_data()
RETURNS TABLE (
    id INTEGER,
    chat_id INTEGER,
    role VARCHAR(20),
    content TEXT,
    feedback_rating INTEGER,
    feedback_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    created_at_local TIMESTAMP WITHOUT TIME ZONE,
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
        cm.created_at AT TIME ZONE 'Europe/Zurich' AS created_at_local,
        c.user_id,
        c.mode as chat_mode
    FROM chat_messages cm
    JOIN chats c ON cm.chat_id = c.id
    ORDER BY cm.created_at DESC;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION get_analytics_data() TO authenticated;

-- Additional function to get all user profiles for analytics (bypasses RLS)
CREATE OR REPLACE FUNCTION get_all_user_profiles()
RETURNS TABLE (
    id UUID,
    user_role TEXT,
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    SELECT id, user_role, created_at FROM user_profiles;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION get_all_user_profiles() TO authenticated;
