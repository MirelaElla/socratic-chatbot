# Analytics Dashboard - Setup and Usage

## Overview
The analytics dashboard provides comprehensive insights into the Socratic Chatbot usage, including user engagement, chat mode preferences, feedback ratings, and usage patterns.

## Features

### 📊 Key Metrics Tracked
- **User Metrics**: Total unique users, average interactions per user, active users, returning users
- **Chat Mode Analysis**: Usage distribution between Sokrates and Aristoteles modes
- **Feedback Analysis**: Satisfaction ratings, feedback rates, and detailed feedback breakdown
- **Usage Patterns**: Daily, hourly, and weekly usage trends
- **User Engagement**: Interaction distribution and engagement statistics

### 📈 Dashboard Sections
1. **Overview Cards**: High-level KPIs
2. **Chat Mode Analysis**: Visual breakdown of mode preferences
3. **Usage Patterns**: Time-based usage analytics
4. **Feedback Analysis**: User satisfaction metrics
5. **User Engagement**: Detailed user behavior analysis
6. **Recent Activity**: Latest interactions overview
7. **Data Export**: Download raw data and summary report

## Setup Instructions

### 1. Install Dependencies
Make sure you have the updated requirements installed:
```bash
pip install -r requirements.txt
```

The new requirement added:
- `plotly==5.24.1` - For interactive charts and visualizations

### 2. Database Setup
**Important**: Run the new database schema first:
1. Execute `database_setup.sql` in Supabase SQL editor
2. Execute `analytics_function.sql` in Supabase SQL editor for data queries

### 3. Environment Configuration
The dashboard uses the same Supabase configuration as the main chatbot app. Ensure your `.streamlit/secrets.toml` file contains:

```toml
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_key"
```

### 3. Admin Access
The dashboard requires admin authentication based on user roles in the database:

- Users must have a valid account in the Supabase authentication system
- Only users with `user_role = 'admin'` in the `user_profiles` table can access the dashboard
- Admin role assignment must be done through the database or by existing admins

**Setting up admin users:**
1. User must first register/login to the main chatbot application
2. An existing admin can update the user's role in the user_profiles table:
   ```sql
   UPDATE public.user_profiles 
   SET user_role = 'admin' 
   WHERE id = 'user_uuid_here';
   ```
3. The user can then access the analytics dashboard with their regular credentials

## Running the Dashboard

### Option 1: Standalone Dashboard
```bash
streamlit run analytics_dashboard.py
```

### Option 2: Multi-page App (Recommended)
You can integrate this as part of a multi-page Streamlit app. Create a `pages/` directory and move the dashboard there.

## Usage Guide

### 1. Login
- Navigate to the dashboard URL
- Enter your email and password (same credentials used for the main chatbot)
- System will verify you have admin role in the profiles table
- Click "Login" to access the dashboard

### 2. Dashboard Navigation
- **Overview**: Start here for high-level metrics
- **Detailed Analysis**: Scroll down for specific insights
- **Export Data**: Use the export buttons to download reports
- **Refresh**: Click refresh to update data (cached for 5 minutes)

### 3. Key Insights to Monitor

#### User Engagement
- **Unique Users**: Total number of different users
- **Avg Interactions**: How engaged users are
- **Returning Users**: User retention indicator
- **Active Users (7d)**: Recent engagement

#### Chat Mode Preferences
- **Mode Distribution**: Which teaching style is preferred
- **User Preferences**: Individual user's preferred mode
- Monitor if one mode is significantly more popular

#### Feedback Quality
- **Feedback Rate**: Percentage of interactions that receive feedback
- **Satisfaction Score**: Average rating (0-1 scale)
- **Mode-specific Feedback**: Which mode gets better ratings

#### Usage Patterns
- **Daily Trends**: Growth or decline over time
- **Peak Hours**: When students are most active
- **Day of Week**: Usage patterns across the week

## Data Privacy and Security

### 1. Admin Access Only
- Dashboard requires authenticated admin access
- Uses role-based access control via profiles table
- Only users with admin role can access the dashboard
- No public access to sensitive user data

### 2. Data Anonymization
- User IDs are shown as UUIDs (anonymized)
- No personal information displayed
- Content previews are truncated

### 3. Data Caching
- Analytics data is cached for 5 minutes
- Reduces database load
- Can be refreshed manually

## Troubleshooting

### Common Issues

#### 1. Authentication Fails
- Ensure you have a valid user account in the system
- Check that your role is set to 'admin' in the user_profiles table
- Verify Supabase credentials are correct
- Contact an existing admin to update your role if needed

#### 2. No Data Displayed
- Check if chat_messages and chats tables have data
- Verify database connection
- Check for proper table permissions
- Ensure analytics_function.sql has been run if using RPC queries

#### 3. Charts Not Loading
- Ensure plotly is installed correctly
- Check browser console for JavaScript errors
- Try refreshing the page

#### 4. Performance Issues
- Large datasets may slow loading
- Consider adding date filters for large datasets
- Check database query performance

### Database Requirements
The dashboard expects the following table structure:

```sql
user_profiles:
- id (UUID PRIMARY KEY, references auth.users)
- user_role (TEXT: 'admin', 'student', or 'tester')
- created_at (TIMESTAMP WITH TIME ZONE)

chats:
- id (SERIAL PRIMARY KEY)
- user_id (UUID, references auth.users)
- mode (VARCHAR: 'Sokrates' or 'Aristoteles')
- created_at (TIMESTAMP WITH TIME ZONE)

chat_messages:
- id (SERIAL PRIMARY KEY)
- chat_id (INTEGER, references chats.id)
- role (VARCHAR: 'user' or 'assistant')
- content (TEXT)
- feedback_rating (INTEGER: 0 or 1)
- feedback_text (TEXT)
- created_at (TIMESTAMP WITH TIME ZONE)
```

**Note**: The user_profiles table is required for admin authentication. Users must have `user_role = 'admin'` to access the dashboard.

## Admin User Management

### Creating Admin Users
1. **User Registration**: User must first create an account through the main chatbot application
2. **Role Assignment**: Update the user's role in the user_profiles table:
   ```sql
   UPDATE public.user_profiles 
   SET user_role = 'admin' 
   WHERE id = 'user_uuid_here';
   ```
3. **Verification**: User can now access the analytics dashboard

### Managing Admin Access
- **View All Users**: Query the user_profiles table to see all users and their roles
  ```sql
  SELECT p.id, p.user_role, u.email 
  FROM public.user_profiles p 
  JOIN auth.users u ON p.id = u.id;
  ```
- **Revoke Admin Access**: Change role back to 'student'
  ```sql
  UPDATE public.user_profiles 
  SET user_role = 'student' 
  WHERE id = 'user_uuid_here';
  ```

### Security Considerations
- Admin role grants access to all user data in the analytics dashboard
- Only assign admin role to trusted users
- Regularly audit admin user list
- Consider implementing role expiration for temporary admin access

## Performance Optimization
- Adjust caching TTL in `@st.cache_data(ttl=300)`
- Add data filtering options
- Implement pagination for large datasets
