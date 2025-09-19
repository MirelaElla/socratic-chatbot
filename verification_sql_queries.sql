-- Count distinct students (user_role = 'student') who have at least one chat message = active student
SELECT COUNT(DISTINCT up.id) AS student_with_message_count
FROM public.user_profiles up
JOIN public.chats ch ON ch.user_id = up.id
JOIN public.chat_messages cm ON cm.chat_id = ch.id
WHERE up.user_role = 'student';


-- A) Average messages per student (only students who have >=1 message)
SELECT AVG(msg_count) AS avg_messages_per_active_student
FROM (
  SELECT up.id, COUNT(cm.id) AS msg_count
  FROM public.user_profiles up
  JOIN public.chats ch ON ch.user_id = up.id
  JOIN public.chat_messages cm ON cm.chat_id = ch.id
  WHERE up.user_role = 'student'
  GROUP BY up.id
) t;

-- Feedback rate among active students (using feedback_rating only)
WITH student_message_counts AS (
  SELECT up.id AS student_id,
         COUNT(cm.id) AS msg_count,
         MAX(CASE WHEN cm.feedback_rating IS NOT NULL THEN 1 ELSE 0 END) AS has_feedback
  FROM public.user_profiles up
  JOIN public.chats ch ON ch.user_id = up.id
  JOIN public.chat_messages cm ON cm.chat_id = ch.id
  WHERE up.user_role = 'student'
  GROUP BY up.id
)
SELECT
  COUNT(*) FILTER (WHERE msg_count >= 1) AS active_students,
  COUNT(*) FILTER (WHERE msg_count >= 1 AND has_feedback = 1) AS active_students_with_feedback,
  ROUND((COUNT(*) FILTER (WHERE msg_count >= 1 AND has_feedback = 1)::numeric) / NULLIF(COUNT(*) FILTER (WHERE msg_count >= 1), 0), 4) AS feedback_rate
FROM student_message_counts;

-- Feedback rate = assistant messages with feedback_rating / total assistant messages
-- Assumes chat_messages has a column identifying the role of the message (e.g., role = 'assistant').
SELECT
  SUM(CASE WHEN cm.role = 'assistant' AND cm.feedback_rating IS NOT NULL THEN 1 ELSE 0 END) AS assistant_messages_with_feedback,
  SUM(CASE WHEN cm.role = 'assistant' THEN 1 ELSE 0 END) AS total_assistant_messages,
  ROUND( (SUM(CASE WHEN cm.role = 'assistant' AND cm.feedback_rating IS NOT NULL THEN 1 ELSE 0 END)::numeric) / NULLIF(SUM(CASE WHEN cm.role = 'assistant' THEN 1 ELSE 0 END), 0), 4) AS feedback_rate
FROM public.user_profiles up
JOIN public.chats ch ON ch.user_id = up.id
JOIN public.chat_messages cm ON cm.chat_id = ch.id
WHERE up.user_role = 'student';

-- Feedback metrics for assistant messages within student chats
-- Adds count of assistant messages with feedback_rating = 1 (satisfaction)
SELECT
  SUM(CASE WHEN cm.role = 'assistant' AND cm.feedback_rating IS NOT NULL THEN 1 ELSE 0 END) AS assistant_messages_with_feedback,
  SUM(CASE WHEN cm.role = 'assistant' THEN 1 ELSE 0 END) AS total_assistant_messages,
  SUM(CASE WHEN cm.role = 'assistant' AND cm.feedback_rating = 1 THEN 1 ELSE 0 END) AS assistant_feedback_rating_1_count,
  ROUND( (SUM(CASE WHEN cm.role = 'assistant' AND cm.feedback_rating IS NOT NULL THEN 1 ELSE 0 END)::numeric) / NULLIF(SUM(CASE WHEN cm.role = 'assistant' THEN 1 ELSE 0 END), 0), 4) AS feedback_rate
FROM public.user_profiles up
JOIN public.chats ch ON ch.user_id = up.id
JOIN public.chat_messages cm ON cm.chat_id = ch.id
WHERE up.user_role = 'student';


-- Count chat sessions per mode (only chats that have messages)
SELECT
  COALESCE(SUM(CASE WHEN chat_mode = 'Aristoteles' THEN 1 ELSE 0 END), 0) AS aristoteles_chat_count,
  COALESCE(SUM(CASE WHEN chat_mode = 'Sokrates' THEN 1 ELSE 0 END), 0) AS sokrates_chat_count,
  COALESCE(COUNT(DISTINCT chat_id), 0) AS total_student_chats_with_messages
FROM (
  SELECT DISTINCT 
    cm.chat_id,
    ch.mode as chat_mode
  FROM public.user_profiles up
  JOIN public.chats ch ON ch.user_id = up.id
  JOIN public.chat_messages cm ON cm.chat_id = ch.id
  WHERE up.user_role = 'student'
) AS unique_chats;


-- Count chat messages per chat mode
SELECT
  COALESCE(SUM(CASE WHEN ch.mode = 'Aristoteles' THEN 1 ELSE 0 END), 0) AS aristoteles_count,
  COALESCE(SUM(CASE WHEN ch.mode = 'Sokrates' THEN 1 ELSE 0 END), 0) AS socrates_count,
  COALESCE(COUNT(DISTINCT ch.id), 0) AS total_student_chats
FROM public.user_profiles up
JOIN public.chats ch ON ch.user_id = up.id
JOIN public.chat_messages cm ON cm.chat_id = ch.id
WHERE up.user_role = 'student';


-- User Preferred Chat Mode
WITH user_mode_usage AS (
  -- Count messages per user per mode (only students with messages)
  SELECT 
    up.id as user_id,
    ch.mode as chat_mode,
    COUNT(cm.id) as message_count
  FROM public.user_profiles up
  JOIN public.chats ch ON ch.user_id = up.id
  JOIN public.chat_messages cm ON cm.chat_id = ch.id
  WHERE up.user_role = 'student'
  GROUP BY up.id, ch.mode
),
user_preferences AS (
  -- Determine each user's preference based on message counts
  SELECT 
    user_id,
    CASE 
      -- If user only used one mode
      WHEN COUNT(DISTINCT chat_mode) = 1 THEN 
        MAX(chat_mode)
      -- If user used both modes equally (same message count)
      WHEN COUNT(DISTINCT chat_mode) = 2 AND 
           MAX(message_count) = MIN(message_count) THEN 
        'Equal Usage'
      -- If user has a clear preference (one mode has more messages)
      ELSE 
        (SELECT chat_mode 
         FROM user_mode_usage u2 
         WHERE u2.user_id = user_mode_usage.user_id 
         ORDER BY message_count DESC 
         LIMIT 1)
    END as preferred_mode
  FROM user_mode_usage
  GROUP BY user_id
)
-- Count users by their preferred mode
SELECT 
  preferred_mode,
  COUNT(*) as user_count
FROM user_preferences
GROUP BY preferred_mode
ORDER BY user_count DESC;


-- Total messages sent by students
SELECT COUNT(*) FROM public.user_profiles up
JOIN public.chats ch ON ch.user_id = up.id
JOIN public.chat_messages cm ON cm.chat_id = ch.id
WHERE up.user_role = 'student' AND role = 'user';

-- Total messages sent by students and assistant
SELECT COUNT(*) FROM public.user_profiles up
JOIN public.chats ch ON ch.user_id = up.id
JOIN public.chat_messages cm ON cm.chat_id = ch.id
WHERE up.user_role = 'student';