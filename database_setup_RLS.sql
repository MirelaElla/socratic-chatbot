-- ===================================================================
-- Supabase RLS & Trigger Setup for User Session Security
-- ===================================================================
-- This SQL script fixes the cross-user session contamination issue by:
-- 1. Enabling Row Level Security (RLS) on the chats table
-- 2. Creating a trigger to automatically set user_id from JWT
-- 3. Creating RLS policies to ensure users can only access their own data
-- ===================================================================

-- 3.1 Ensure RLS is enabled
ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;

-- 3.2 Enforce non-null user_id
ALTER TABLE public.chats ALTER COLUMN user_id SET NOT NULL;

-- 3.3 Set user_id from JWT on insert
CREATE OR REPLACE FUNCTION public.set_user_id_from_jwt()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.user_id IS NULL THEN
    NEW.user_id := auth.uid();
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS chats_set_uid ON public.chats;
CREATE TRIGGER chats_set_uid
BEFORE INSERT ON public.chats
FOR EACH ROW
EXECUTE FUNCTION public.set_user_id_from_jwt();

-- 3.4 RLS policies (typical "same owner only")
DROP POLICY IF EXISTS chats_select_own ON public.chats;
DROP POLICY IF EXISTS chats_insert_own ON public.chats;
DROP POLICY IF EXISTS chats_update_own ON public.chats;
DROP POLICY IF EXISTS chats_delete_own ON public.chats;

CREATE POLICY chats_select_own ON public.chats
FOR SELECT USING (user_id = auth.uid());

CREATE POLICY chats_insert_own ON public.chats
FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY chats_update_own ON public.chats
FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

CREATE POLICY chats_delete_own ON public.chats
FOR DELETE USING (user_id = auth.uid());

-- Optional: allow selecting your own auth.users row, if needed for FKs
-- (only if you actually query auth.users; FK checks don't require this)
-- CREATE POLICY users_select_self ON auth.users
-- FOR SELECT USING (id = auth.uid());

-- ===================================================================
-- VERIFICATION QUERIES (run these to verify the setup)
-- ===================================================================
-- Check if RLS is enabled:
-- SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'chats';

-- Check if trigger exists:
-- SELECT tgname FROM pg_trigger WHERE tgrelid = 'public.chats'::regclass;

-- Check policies:
-- SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
-- FROM pg_policies WHERE tablename = 'chats';
