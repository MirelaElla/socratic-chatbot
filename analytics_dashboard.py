import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import re
from dotenv import load_dotenv
from supabase import create_client
import os

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Analytics Dashboard - Socratic Chatbot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Supabase client
@st.cache_resource
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def is_valid_email(email):
    """Check if email is valid and ends with allowed domains for admin access"""
    # Allow admin access for university domains and specific admin emails
    pattern = r'^[a-zA-Z0-9._%+-]+@(unidistance\.ch|fernuni\.ch|admin\.local)$'
    return re.match(pattern, email) is not None

def create_demo_data():
    """Create demo data for testing when no real data is available"""
    from datetime import datetime, timedelta
    import uuid
    
    # Generate demo data
    demo_data = []
    
    # Create some demo users
    user_ids = [str(uuid.uuid4()) for _ in range(10)]
    
    # Generate demo interactions over the last 30 days
    start_date = datetime.now() - timedelta(days=30)
    
    for i in range(100):  # 100 demo messages
        user_id = np.random.choice(user_ids)
        chat_mode = np.random.choice(['Sokrates', 'Aristoteles'], p=[0.6, 0.4])
        role = np.random.choice(['user', 'assistant'])
        
        # Create timestamp within last 30 days
        days_ago = np.random.randint(0, 30)
        hours_ago = np.random.randint(0, 24)
        timestamp = start_date + timedelta(days=days_ago, hours=hours_ago)
        
        # Generate content
        if role == 'user':
            content = np.random.choice([
                "What is working memory?",
                "How does the phonological loop work?",
                "Can you explain episodic memory?",
                "What are the differences between short-term and long-term memory?",
                "How does memory consolidation work?"
            ])
            feedback_rating = None
            feedback_text = None
        else:
            content = np.random.choice([
                "Let me help you understand working memory by asking you this question...",
                "Working memory is a crucial cognitive system that...",
                "The phonological loop is one component of working memory that...",
                "Episodic memory refers to our ability to recall specific events...",
                "Memory consolidation is the process by which..."
            ])
            # Some assistant messages have feedback
            if np.random.random() < 0.3:  # 30% feedback rate
                feedback_rating = np.random.choice([0, 1], p=[0.2, 0.8])  # 80% positive
                feedback_text = np.random.choice([
                    "Very helpful explanation!",
                    "Could be clearer",
                    "Perfect, thank you!",
                    "I need more details",
                    None
                ]) if np.random.random() < 0.5 else None
            else:
                feedback_rating = None
                feedback_text = None
        
        demo_data.append({
            'id': i + 1,
            'user_id': user_id,
            'role': role,
            'content': content,
            'chat_mode': chat_mode,
            'feedback_rating': feedback_rating,
            'feedback_text': feedback_text,
            'created_at': timestamp.isoformat()
        })
    
    return pd.DataFrame(demo_data)

def authenticate_admin(email, password):
    """Simple admin authentication - in production, use proper admin roles"""
    # For demo purposes, allow demo login
    if email == "demo@admin.local" and password == "demo":
        return {"email": email, "id": "demo-user"}
    
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if response.user and is_valid_email(email):
            return response.user
        else:
            return None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_analytics_data():
    """Fetch all analytics data from the database"""
    supabase = get_supabase_client()
    
    try:
        # Fetch chat history data
        chat_response = supabase.table("chat_history").select("*").execute()
        chat_data = pd.DataFrame(chat_response.data) if chat_response.data else pd.DataFrame()
        
        # If no real data, create demo data for testing
        if chat_data.empty:
            st.info("🔄 No real data found. Showing demo data for testing purposes.")
            chat_data = create_demo_data()
        
        return chat_data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        st.info("🔄 Using demo data due to connection error.")
        return create_demo_data()

def calculate_user_metrics(df):
    """Calculate user-related metrics"""
    if df.empty:
        return {}
    
    # Convert created_at to datetime
    df['created_at'] = pd.to_datetime(df['created_at'])
    
    # Unique users
    unique_users = df['user_id'].nunique()
    
    # User interactions (messages per user)
    user_interactions = df.groupby('user_id').size()
    avg_interactions = user_interactions.mean()
    
    # Active users (users who interacted in the last 7 days)
    last_week = pd.Timestamp.now(tz='UTC') - timedelta(days=7)
    recent_users = df[df['created_at'] > last_week]['user_id'].nunique()
    
    # User retention (users who came back)
    user_sessions = df.groupby('user_id')['created_at'].apply(lambda x: x.dt.date.nunique())
    returning_users = (user_sessions > 1).sum()
    
    return {
        'unique_users': unique_users,
        'avg_interactions': avg_interactions,
        'active_users_7d': recent_users,
        'returning_users': returning_users,
        'user_interactions': user_interactions
    }

def calculate_chat_mode_metrics(df):
    """Calculate chat mode usage metrics"""
    if df.empty:
        return {}
    
    # Chat mode distribution
    mode_counts = df['chat_mode'].value_counts()
    mode_percentages = (mode_counts / mode_counts.sum() * 100).round(2)
    
    # User preference (which mode each user uses most)
    user_mode_preference = df.groupby('user_id')['chat_mode'].apply(lambda x: x.mode()[0] if len(x.mode()) > 0 else 'Unknown')
    user_preference_counts = user_mode_preference.value_counts()
    
    return {
        'mode_counts': mode_counts,
        'mode_percentages': mode_percentages,
        'user_preferences': user_preference_counts
    }

def calculate_feedback_metrics(df):
    """Calculate feedback-related metrics"""
    if df.empty:
        return {}
    
    # Filter assistant messages with feedback
    feedback_data = df[(df['role'] == 'assistant') & (df['feedback_rating'].notna())]
    
    if feedback_data.empty:
        return {
            'total_feedback': 0,
            'positive_feedback': 0,
            'negative_feedback': 0,
            'feedback_rate': 0,
            'avg_rating': 0
        }
    
    total_feedback = len(feedback_data)
    positive_feedback = (feedback_data['feedback_rating'] == 1).sum()
    negative_feedback = (feedback_data['feedback_rating'] == 0).sum()
    
    # Feedback rate (percentage of assistant messages that received feedback)
    total_assistant_messages = (df['role'] == 'assistant').sum()
    feedback_rate = (total_feedback / total_assistant_messages * 100) if total_assistant_messages > 0 else 0
    
    # Average rating
    avg_rating = feedback_data['feedback_rating'].mean()
    
    return {
        'total_feedback': total_feedback,
        'positive_feedback': positive_feedback,
        'negative_feedback': negative_feedback,
        'feedback_rate': feedback_rate,
        'avg_rating': avg_rating,
        'feedback_by_mode': feedback_data.groupby('chat_mode')['feedback_rating'].agg(['count', 'mean'])
    }

def calculate_usage_patterns(df):
    """Calculate usage patterns over time"""
    if df.empty:
        return {}
    
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['date'] = df['created_at'].dt.date
    df['hour'] = df['created_at'].dt.hour
    df['day_of_week'] = df['created_at'].dt.day_name()
    
    # Daily usage
    daily_usage = df.groupby('date').agg({
        'user_id': 'nunique',
        'id': 'count'
    }).rename(columns={'user_id': 'unique_users', 'id': 'total_messages'})
    
    # Hourly patterns
    hourly_usage = df.groupby('hour').size()
    
    # Day of week patterns
    dow_usage = df.groupby('day_of_week').size()
    
    return {
        'daily_usage': daily_usage,
        'hourly_usage': hourly_usage,
        'dow_usage': dow_usage
    }

def show_admin_login():
    """Display admin login form"""
    st.title("🔐 Analytics Dashboard - Admin Access")
    st.markdown("Please enter your administrator credentials to access the analytics dashboard.")
    
    # Demo credentials info
    with st.expander("🧪 Demo Access (for testing)"):
        st.code("""
Demo Credentials:
Email: demo@admin.local
Password: demo

This will show demo data for testing purposes.
        """)
    
    with st.form("admin_login"):
        email = st.text_input("Admin Email", placeholder="admin@unidistance.ch")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if email and password:
                user = authenticate_admin(email, password)
                if user:
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_email = email
                    st.success("✅ Successfully logged in!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials or insufficient permissions")
            else:
                st.warning("⚠️ Please enter both email and password")

def show_dashboard():
    """Main dashboard display"""
    st.title("📊 Socratic Chatbot - Analytics Dashboard")
    st.markdown(f"Welcome back, {st.session_state.admin_email}")
    
    # Logout button
    if st.sidebar.button("🚪 Logout"):
        st.session_state.admin_authenticated = False
        st.session_state.admin_email = None
        st.rerun()
    
    # Fetch data
    with st.spinner("Loading analytics data..."):
        df = fetch_analytics_data()
    
    if df.empty:
        st.warning("No data available yet. Start using the chatbot to see analytics!")
        return
    
    # Calculate metrics
    user_metrics = calculate_user_metrics(df)
    chat_metrics = calculate_chat_mode_metrics(df)
    feedback_metrics = calculate_feedback_metrics(df)
    usage_metrics = calculate_usage_patterns(df)
    
    # Overview Cards
    st.header("📈 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="👥 Total Users",
            value=user_metrics.get('unique_users', 0),
            delta=user_metrics.get('active_users_7d', 0),
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            label="💬 Avg Interactions/User",
            value=f"{user_metrics.get('avg_interactions', 0):.1f}",
            delta=f"{user_metrics.get('returning_users', 0)} returning"
        )
    
    with col3:
        st.metric(
            label="⭐ Feedback Rate",
            value=f"{feedback_metrics.get('feedback_rate', 0):.1f}%",
            delta=f"{feedback_metrics.get('total_feedback', 0)} total"
        )
    
    with col4:
        st.metric(
            label="👍 Satisfaction",
            value=f"{feedback_metrics.get('avg_rating', 0):.2f}",
            delta=f"{feedback_metrics.get('positive_feedback', 0)}/{feedback_metrics.get('total_feedback', 0)}"
        )
    
    # Chat Mode Analysis
    st.header("🎭 Chat Mode Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        if 'mode_percentages' in chat_metrics and not chat_metrics['mode_percentages'].empty:
            fig_mode = px.pie(
                values=chat_metrics['mode_percentages'].values,
                names=chat_metrics['mode_percentages'].index,
                title="Chat Mode Usage Distribution",
                color_discrete_map={'Sokrates': '#FF6B6B', 'Aristoteles': '#4ECDC4'}
            )
            st.plotly_chart(fig_mode, use_container_width=True)
    
    with col2:
        if 'user_preferences' in chat_metrics and not chat_metrics['user_preferences'].empty:
            fig_pref = px.bar(
                x=chat_metrics['user_preferences'].index,
                y=chat_metrics['user_preferences'].values,
                title="User Preferred Chat Mode",
                labels={'x': 'Chat Mode', 'y': 'Number of Users'},
                color=chat_metrics['user_preferences'].index,
                color_discrete_map={'Sokrates': '#FF6B6B', 'Aristoteles': '#4ECDC4'}
            )
            st.plotly_chart(fig_pref, use_container_width=True)
    
    # Usage Patterns
    st.header("📅 Usage Patterns")
    
    if 'daily_usage' in usage_metrics:
        col1, col2 = st.columns(2)
        
        with col1:
            # Daily usage over time
            daily_df = usage_metrics['daily_usage'].reset_index()
            fig_daily = px.line(
                daily_df,
                x='date',
                y=['unique_users', 'total_messages'],
                title="Daily Usage Trends",
                labels={'value': 'Count', 'date': 'Date'}
            )
            st.plotly_chart(fig_daily, use_container_width=True)
        
        with col2:
            # Hourly usage pattern
            if 'hourly_usage' in usage_metrics:
                fig_hourly = px.bar(
                    x=usage_metrics['hourly_usage'].index,
                    y=usage_metrics['hourly_usage'].values,
                    title="Usage by Hour of Day",
                    labels={'x': 'Hour', 'y': 'Messages'},
                    color=usage_metrics['hourly_usage'].values,
                    color_continuous_scale='viridis'
                )
                st.plotly_chart(fig_hourly, use_container_width=True)
    
    # Feedback Analysis
    st.header("💭 Feedback Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Overall feedback distribution
        if feedback_metrics.get('total_feedback', 0) > 0:
            feedback_labels = ['Positive 👍', 'Negative 👎']
            feedback_values = [
                feedback_metrics.get('positive_feedback', 0),
                feedback_metrics.get('negative_feedback', 0)
            ]
            
            fig_feedback = px.pie(
                values=feedback_values,
                names=feedback_labels,
                title="Feedback Distribution",
                color_discrete_map={'Positive 👍': '#2ECC71', 'Negative 👎': '#E74C3C'}
            )
            st.plotly_chart(fig_feedback, use_container_width=True)
        else:
            st.info("No feedback data available yet.")
    
    with col2:
        # Feedback by chat mode
        if 'feedback_by_mode' in feedback_metrics:
            feedback_mode_df = feedback_metrics['feedback_by_mode'].reset_index()
            if not feedback_mode_df.empty:
                fig_mode_feedback = px.bar(
                    feedback_mode_df,
                    x='chat_mode',
                    y=['count', 'mean'],
                    title="Feedback by Chat Mode",
                    labels={'value': 'Value', 'chat_mode': 'Chat Mode'},
                    barmode='group'
                )
                st.plotly_chart(fig_mode_feedback, use_container_width=True)
    
    # User Engagement
    st.header("👤 User Engagement")
    
    if 'user_interactions' in user_metrics:
        # Distribution of user interactions
        interactions_dist = user_metrics['user_interactions'].value_counts().sort_index()
        
        fig_engagement = px.histogram(
            x=user_metrics['user_interactions'].values,
            nbins=20,
            title="Distribution of User Interactions",
            labels={'x': 'Number of Interactions', 'y': 'Number of Users'},
            color_discrete_sequence=['#3498DB']
        )
        st.plotly_chart(fig_engagement, use_container_width=True)
        
        # Engagement statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Most Active User", f"{user_metrics['user_interactions'].max()} interactions")
        with col2:
            st.metric("Median Interactions", f"{user_metrics['user_interactions'].median():.0f}")
        with col3:
            st.metric("Users with 1 interaction", f"{(user_metrics['user_interactions'] == 1).sum()}")
    
    # Recent Activity
    st.header("🕐 Recent Activity")
    
    # Show recent messages (last 10)
    recent_messages = df.sort_values('created_at', ascending=False).head(10)
    
    st.subheader("Latest Interactions")
    for _, row in recent_messages.iterrows():
        with st.expander(f"{row['role'].title()} - {row['chat_mode']} - {row['created_at']}"):
            st.write(f"**Content:** {row['content'][:200]}{'...' if len(row['content']) > 200 else ''}")
            if row['feedback_rating'] is not None:
                rating = "👍" if row['feedback_rating'] == 1 else "👎"
                st.write(f"**Feedback:** {rating}")
                if row['feedback_text']:
                    st.write(f"**Feedback Text:** {row['feedback_text']}")
    
    # Data Export
    st.header("📤 Data Export")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Download Analytics Summary"):
            summary_data = {
                'Metric': [
                    'Total Users',
                    'Average Interactions per User',
                    'Active Users (7 days)',
                    'Returning Users',
                    'Total Feedback',
                    'Positive Feedback Rate',
                    'Sokrates Usage %',
                    'Aristoteles Usage %'
                ],
                'Value': [
                    user_metrics.get('unique_users', 0),
                    f"{user_metrics.get('avg_interactions', 0):.2f}",
                    user_metrics.get('active_users_7d', 0),
                    user_metrics.get('returning_users', 0),
                    feedback_metrics.get('total_feedback', 0),
                    f"{feedback_metrics.get('avg_rating', 0):.2f}",
                    f"{chat_metrics.get('mode_percentages', {}).get('Sokrates', 0):.1f}%",
                    f"{chat_metrics.get('mode_percentages', {}).get('Aristoteles', 0):.1f}%"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            csv = summary_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"chatbot_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

def main():
    """Main application logic"""
    # Initialize session state
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    
    # Show appropriate interface
    if not st.session_state.admin_authenticated:
        show_admin_login()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
