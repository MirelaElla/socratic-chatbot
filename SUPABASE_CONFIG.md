# Supabase Auth Configuration Guide

## Problem: Email Confirmation Redirect Issue
After user registration, the email confirmation link redirects to `localhost:3000` instead of the correct Streamlit URL.

## Solution: Configure Supabase Auth Settings

### 1. Access Supabase Dashboard
1. Go to your Supabase project dashboard
2. Navigate to **Authentication** > **URL Configuration**

### 2. Update Site URL
- **Site URL**: `http://localhost:8501` (for development)
- This is the main URL of your application

### 3. Add Redirect URLs
In the **Redirect URLs** section, add:
- `http://localhost:8501`
- `http://localhost:8501/**` (with wildcard)

### 4. For Production Deployment
When you deploy to production (e.g., Streamlit Cloud), update:
- **Site URL**: `https://your-app-name.streamlit.app`
- **Redirect URLs**: Add your production URL

### 5. Email Templates (Optional)
- Go to **Authentication** > **Email Templates**
- You can customize the confirmation email template
- The `{{ .ConfirmationURL }}` variable will use your configured redirect URL

### 6. Additional Settings
- **Enable email confirmations**: Should be ON
- **Enable email change confirmations**: Recommended ON
- **Enable manual linking**: Optional based on your needs

## Development vs Production

### Development (localhost)
```
Site URL: http://localhost:8501
Redirect URLs: 
- http://localhost:8501
- http://localhost:8501/**
```

### Production (Streamlit Cloud)
```
Site URL: https://your-app-name.streamlit.app
Redirect URLs:
- https://your-app-name.streamlit.app
- https://your-app-name.streamlit.app/**
```

## Testing
1. Update the Supabase settings as above
2. Try registering a new user
3. Check the email confirmation link - it should now redirect to the correct URL
4. After clicking confirmation, you should be redirected to your Streamlit app

## Notes
- Changes to URL configuration may take a few minutes to propagate
- Make sure to save changes in the Supabase dashboard
- Test with a new email address after making changes
