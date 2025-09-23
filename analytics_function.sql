-- Add this function to your Supabase SQL editor to support the analytics dashboard
-- This function provides raw chat data for analytics
-- Note: This function uses SECURITY DEFINER to bypass RLS for analytics

-- Create RPC function with proper table aliases and qualified column references
CREATE OR REPLACE FUNCTION public.get_comprehensive_analytics_data()
returns table(
  user_id uuid,
  user_email text,
  user_role text,
  profile_created_at timestamp with time zone,
  chat_id integer,
  chat_mode text,
  chat_created_at timestamp with time zone,
  message_id integer,
  message_role text,
  message_content text,
  message_feedback_rating integer,
  message_feedback_text text,
  message_created_at timestamp with time zone
)
LANGUAGE sql stable
SECURITY definer
as $$
SELECT
  au.id                        AS user_id,
  au.email                     AS user_email,
  up.user_role                 AS user_role,
  up.created_at                AS profile_created_at,
  ch.id                        AS chat_id,
  ch.mode                      AS chat_mode,
  ch.created_at                AS chat_created_at,
  cm.id                        AS message_id,
  cm.role                      AS message_role,
  cm.content                   AS message_content,
  cm.feedback_rating           AS message_feedback_rating,
  cm.feedback_text             AS message_feedback_text,
  cm.created_at                AS message_created_at
FROM auth.users au
LEFT JOIN public.user_profiles up ON up.id = au.id
LEFT JOIN public.chats ch ON ch.user_id = au.id
LEFT JOIN public.chat_messages cm ON cm.chat_id = ch.id
ORDER BY cm.created_at ASC NULLS LAST;
$$;

-- Grant execute to authenticated role
GRANT EXECUTE ON FUNCTION public.get_comprehensive_analytics_data() to authenticated;