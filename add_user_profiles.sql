-- Create profiles table linked to auth.users
CREATE TABLE public.profiles (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('admin', 'student', 'tester')) NOT NULL DEFAULT 'student'
);

-- Create a function to automatically insert a profile when a user is created
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, role)
    VALUES (NEW.id, 'student');  -- Default role is 'student'
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a trigger to call the function
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Enable Row Level Security
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Create policies to protect the profiles table
CREATE POLICY "Users can view own profile" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

-- Policy for admin to update roles
CREATE POLICY "Admins can update user roles" ON public.profiles
    FOR UPDATE 
    TO authenticated 
    USING ((SELECT role FROM public.profiles WHERE id = auth.uid()) = 'admin')
    WITH CHECK ((SELECT role FROM public.profiles WHERE id = auth.uid()) = 'admin');

-- As an admin, you can update any user's role
-- UPDATE public.profiles 
-- SET role = 'admin' 
-- WHERE id = 'user_uuid_here';