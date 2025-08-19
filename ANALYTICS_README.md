# Analytics Dashboard - Setup and Usage Guide

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
7. **Data Export**: Download analytics summaries

## Setup Instructions

### 1. Install Dependencies
Make sure you have the updated requirements installed:
```bash
pip install -r requirements.txt
```

The new requirement added:
- `plotly==5.24.1` - For interactive charts and visualizations

### 2. Environment Configuration
The dashboard uses the same Supabase configuration as the main chatbot app. Ensure your `.streamlit/secrets.toml` file contains:

```toml
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_key"
```

### 3. Admin Access
The dashboard requires admin authentication. Users with emails ending in:
- `@unidistance.ch`
- `@fernuni.ch`
- `@admin.local` (for testing)

Can access the dashboard using their regular Supabase credentials.

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
- Enter your admin credentials (university email + password)
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
- Uses same authentication system as main app
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
- Ensure your email domain is whitelisted
- Check Supabase credentials
- Verify user exists in auth.users table

#### 2. No Data Displayed
- Check if chat_history table has data
- Verify database connection
- Check for proper table permissions

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
chat_history:
- id (SERIAL PRIMARY KEY)
- user_id (UUID)
- role (VARCHAR: 'user' or 'assistant')
- content (TEXT)
- chat_mode (VARCHAR: 'Sokrates' or 'Aristoteles')
- feedback_rating (INTEGER: 0 or 1)
- feedback_text (TEXT)
- created_at (TIMESTAMP WITH TIME ZONE)
```

## Customization

### Adding New Metrics
To add new analytics:

1. **Update Data Fetching**: Modify `fetch_analytics_data()`
2. **Create Calculation Function**: Add new metric calculation
3. **Update Dashboard**: Add visualization in `show_dashboard()`
4. **Update Export**: Include in CSV export

### Styling and Branding
- Modify color schemes in plotly charts
- Update page config and titles
- Add custom CSS for branding

### Performance Optimization
- Adjust caching TTL in `@st.cache_data(ttl=300)`
- Add data filtering options
- Implement pagination for large datasets

## Future Enhancements

### Potential Features
- **Real-time Updates**: Live dashboard updates
- **Email Reports**: Automated weekly/monthly reports
- **Advanced Filtering**: Date ranges, user segments
- **Comparative Analysis**: Period-over-period comparisons
- **Predictive Analytics**: Usage forecasting
- **A/B Testing**: Compare different prompts or features

### Integration Ideas
- **Learning Management System**: Connect with university LMS
- **Student Information System**: Link with student records (anonymized)
- **Research Tools**: Export data for academic research
- **Alert System**: Notifications for unusual patterns

## Support
For issues or questions:
1. Check this README first
2. Review error logs in terminal
3. Check Supabase dashboard for data issues
4. Contact system administrator
