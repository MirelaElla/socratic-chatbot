import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
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

def check_admin_role(user_id):
    """Check if user has admin role in the user_profiles table"""
    try:
        supabase = get_supabase_client()
        response = supabase.table("user_profiles").select("user_role").eq("id", user_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]["user_role"] == "admin"
        return False
    except Exception as e:
        st.error(f"Error checking admin role: {e}")
        return False

def authenticate_admin(email, password):
    """Authenticate admin users with proper role validation"""
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            # Check if user has admin role in user_profiles table
            if check_admin_role(response.user.id):
                return response.user
            else:
                st.error("❌ Access denied: Admin role required")
                return None
        else:
            return None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_comprehensive_data():
    """Fetch all data in one comprehensive query"""
    supabase = get_supabase_client()
    
    try:
        # Execute the RPC function to get comprehensive analytics data
        response = supabase.rpc('get_comprehensive_analytics_data').execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
        else:
            st.error("No data returned from analytics function. Please contact administrator.")
            return pd.DataFrame()
        
        # Data preprocessing
        if not df.empty:
            # Convert timestamps to datetime
            timestamp_columns = ['profile_created_at', 'chat_created_at', 'message_created_at']
            for col in timestamp_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
            
            # Create local timezone column for message timestamps
            if 'message_created_at' in df.columns:
                df['message_created_at_local'] = pd.to_datetime(df['message_created_at']).dt.tz_convert('Europe/Zurich').dt.tz_localize(None)
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching comprehensive data: {e}")
        return pd.DataFrame()

def get_user_registration_metrics(df):
    """Calculate user registration metrics from comprehensive DataFrame"""
    if df.empty:
        return {
            'total_registered': 0,
            'students': 0,
            'admins': 0,
            'testers': 0,
            'role_breakdown': {}
        }
    
    # Get unique users with their roles
    user_data = df[['user_id', 'user_role']].drop_duplicates()
    
    total_registered = len(user_data)
    role_counts = user_data['user_role'].value_counts()
    
    return {
        'total_registered': total_registered,
        'students': role_counts.get('student', 0),
        'admins': role_counts.get('admin', 0),
        'testers': role_counts.get('tester', 0),
        'role_breakdown': role_counts.to_dict()
    }

def get_student_chat_metrics(df):
    """Calculate student-specific chat metrics"""
    if df.empty:
        return {
            'students_who_chatted': 0,
            'total_students': 0,
            'avg_messages_per_student': 0.0,
            'avg_messages_per_active_student': 0.0,
            'student_chat_participation_rate': 0.0
        }
    
    # Get all students
    students_df = df[df['user_role'] == 'student']
    unique_students = students_df[['user_id', 'user_role']].drop_duplicates()
    total_students = len(unique_students)
    
    # Get students who have chat messages (user messages only)
    student_user_messages = students_df[
        (students_df['message_id'].notna()) & 
        (students_df['message_role'] == 'user')
    ]
    
    if student_user_messages.empty:
        return {
            'students_who_chatted': 0,
            'total_students': total_students,
            'avg_messages_per_student': 0.0,
            'avg_messages_per_active_student': 0.0,
            'student_chat_participation_rate': 0.0
        }
    
    students_who_chatted = student_user_messages['user_id'].nunique()
    total_student_user_messages = len(student_user_messages)
    
    avg_messages_per_student = total_student_user_messages / total_students if total_students > 0 else 0
    avg_messages_per_active_student = total_student_user_messages / students_who_chatted if students_who_chatted > 0 else 0
    participation_rate = (students_who_chatted / total_students * 100) if total_students > 0 else 0
    
    return {
        'students_who_chatted': students_who_chatted,
        'total_students': total_students,
        'avg_messages_per_student': avg_messages_per_student,
        'avg_messages_per_active_student': avg_messages_per_active_student,
        'student_chat_participation_rate': participation_rate
    }

def get_chat_mode_metrics(df):
    """Calculate chat mode usage metrics for students only"""
    if df.empty:
        return {}
    
    # Filter to student messages only
    student_messages = df[(df['user_role'] == 'student') & (df['message_id'].notna())]
    
    if student_messages.empty:
        return {}
    
    # Message distribution by mode
    mode_counts = student_messages['chat_mode'].value_counts()
    mode_percentages = (mode_counts / mode_counts.sum() * 100).round(2)
    
    # Chat session distribution by mode
    student_chats = student_messages[['chat_id', 'chat_mode']].drop_duplicates()
    chat_session_counts = student_chats['chat_mode'].value_counts()
    chat_session_percentages = (chat_session_counts / chat_session_counts.sum() * 100).round(2)
    
    # User preferences
    def determine_user_preference(user_messages):
        mode_counts = user_messages.value_counts()
        if len(mode_counts) == 0:
            return 'Unknown'
        elif len(mode_counts) == 1:
            return mode_counts.index[0]
        elif len(mode_counts) == 2 and mode_counts.iloc[0] == mode_counts.iloc[1]:
            return 'Equal Usage'
        else:
            return mode_counts.index[0]
    
    user_mode_preference = student_messages.groupby('user_id')['chat_mode'].apply(determine_user_preference)
    user_preference_counts = user_mode_preference.value_counts()
    
    return {
        'mode_counts': mode_counts,
        'mode_percentages': mode_percentages,
        'chat_session_counts': chat_session_counts,
        'chat_session_percentages': chat_session_percentages,
        'user_preferences': user_preference_counts
    }

def get_feedback_metrics(df):
    """Calculate feedback metrics for students only"""
    if df.empty:
        return {
            'total_feedback': 0,
            'positive_feedback': 0,
            'negative_feedback': 0,
            'feedback_rate': 0,
            'avg_rating': 0
        }
    
    # Filter to student assistant messages
    student_assistant_messages = df[
        (df['user_role'] == 'student') & 
        (df['message_role'] == 'assistant') & 
        (df['message_id'].notna())
    ]
    
    if student_assistant_messages.empty:
        return {
            'total_feedback': 0,
            'positive_feedback': 0,
            'negative_feedback': 0,
            'feedback_rate': 0,
            'avg_rating': 0
        }
    
    # Messages with feedback
    feedback_messages = student_assistant_messages[student_assistant_messages['message_feedback_rating'].notna()]
    
    if feedback_messages.empty:
        return {
            'total_feedback': 0,
            'positive_feedback': 0,
            'negative_feedback': 0,
            'feedback_rate': 0,
            'avg_rating': 0
        }
    
    total_feedback = len(feedback_messages)
    positive_feedback = (feedback_messages['message_feedback_rating'] == 1).sum()
    negative_feedback = (feedback_messages['message_feedback_rating'] == 0).sum()
    
    # Feedback rate
    total_assistant_messages = len(student_assistant_messages)
    feedback_rate = (total_feedback / total_assistant_messages * 100) if total_assistant_messages > 0 else 0
    
    # Average rating
    avg_rating = feedback_messages['message_feedback_rating'].mean()
    
    # Feedback by mode
    feedback_by_mode = feedback_messages.groupby('chat_mode')['message_feedback_rating'].agg(['count', 'mean'])
    
    return {
        'total_feedback': total_feedback,
        'positive_feedback': positive_feedback,
        'negative_feedback': negative_feedback,
        'feedback_rate': feedback_rate,
        'avg_rating': avg_rating,
        'feedback_by_mode': feedback_by_mode
    }

def get_usage_patterns(df):
    """Calculate usage patterns for students only"""
    if df.empty:
        return {}
    
    # Filter to student user messages with timestamps
    student_messages = df[
        (df['user_role'] == 'student') & 
        (df['message_role'] == 'user') & 
        (df['message_id'].notna()) & 
        (df['message_created_at_local'].notna())
    ].copy()
    
    if student_messages.empty:
        return {}
    
    # Add time-based columns
    student_messages['date'] = student_messages['message_created_at_local'].dt.date
    student_messages['hour'] = student_messages['message_created_at_local'].dt.hour
    student_messages['day_of_week'] = student_messages['message_created_at_local'].dt.day_name()
    
    # Daily usage
    daily_usage = student_messages.groupby('date').agg({
        'user_id': 'nunique',
        'message_id': 'count'
    }).rename(columns={'user_id': 'unique_users', 'message_id': 'total_messages'})
    
    # Hourly patterns
    hourly_usage = student_messages.groupby('hour').size()
    
    # Day of week patterns
    dow_usage = student_messages.groupby('day_of_week').size()
    
    return {
        'daily_usage': daily_usage,
        'hourly_usage': hourly_usage,
        'dow_usage': dow_usage
    }

def get_user_engagement_metrics(df):
    """Calculate user engagement metrics for students only"""
    if df.empty:
        return {}
    
    # Filter to student user messages only
    student_messages = df[
        (df['user_role'] == 'student') & 
        (df['message_role'] == 'user') & 
        (df['message_id'].notna())
    ]
    
    if student_messages.empty:
        return {}
    
    # User interactions
    user_interactions = student_messages.groupby('user_id').size()
    
    # Active users (last 7 days)
    if 'message_created_at_local' in student_messages.columns:
        last_week = pd.Timestamp.now() - timedelta(days=7)
        recent_users = student_messages[
            student_messages['message_created_at_local'] > last_week
        ]['user_id'].nunique()
    else:
        recent_users = 0
    
    # Returning users (users with multiple chat sessions)
    user_sessions = student_messages.groupby('user_id')['chat_id'].nunique()
    returning_users = (user_sessions > 1).sum()
    
    return {
        'unique_users': student_messages['user_id'].nunique(),
        'avg_interactions': user_interactions.mean(),
        'active_users_7d': recent_users,
        'returning_users': returning_users,
        'user_interactions': user_interactions
    }

def show_admin_login():
    """Display admin login form"""
    st.title("🔐 Analytics Dashboard - Admin Access")
    st.markdown("Please enter your administrator credentials to access the analytics dashboard.")
    st.info("ℹ️ Only users with admin role in the system can access this dashboard.")
    
    with st.form("admin_login"):
        email = st.text_input("Admin Email", placeholder="vorname.nachname@unidistance.ch")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if email and password:
                user = authenticate_admin(email, password)
                if user:
                    st.session_state.admin_authenticated = True
                    st.session_state.admin_email = email
                    st.session_state.admin_user_id = user.id
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
        if 'admin_user_id' in st.session_state:
            st.session_state.admin_user_id = None
        st.rerun()
    
    # Fetch comprehensive data
    with st.spinner("Loading analytics data..."):
        df = fetch_comprehensive_data()
    
    if df.empty:
        st.warning("No data available! Please check database connection and permissions.")
        return
    
    # Calculate all metrics
    registration_metrics = get_user_registration_metrics(df)
    student_chat_metrics = get_student_chat_metrics(df)
    chat_mode_metrics = get_chat_mode_metrics(df)
    feedback_metrics = get_feedback_metrics(df)
    usage_patterns = get_usage_patterns(df)
    engagement_metrics = get_user_engagement_metrics(df)
    
    # User Registration Overview
    st.header("👥 User Registration Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📝 Total Registered Users",
            value=registration_metrics.get('total_registered', 0),
            delta=None
        )
    
    with col2:
        st.metric(
            label="🎓 Students",
            value=registration_metrics.get('students', 0),
            delta=f"{registration_metrics.get('students', 0)/registration_metrics.get('total_registered', 1)*100:.1f}%" if registration_metrics.get('total_registered', 0) > 0 else "0%"
        )
    
    with col3:
        st.metric(
            label="👑 Admins",
            value=registration_metrics.get('admins', 0),
            delta=f"{registration_metrics.get('admins', 0)/registration_metrics.get('total_registered', 1)*100:.1f}%" if registration_metrics.get('total_registered', 0) > 0 else "0%"
        )
    
    with col4:
        st.metric(
            label="🧪 Testers",
            value=registration_metrics.get('testers', 0),
            delta=f"{registration_metrics.get('testers', 0)/registration_metrics.get('total_registered', 1)*100:.1f}%" if registration_metrics.get('total_registered', 0) > 0 else "0%"
        )
    
    # Student Chat Activity Overview
    st.header("📈 Student Chat Activity Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="👥 Students Who Chatted",
            value=student_chat_metrics.get('students_who_chatted', 0),
            delta=f"{student_chat_metrics.get('student_chat_participation_rate', 0):.1f}% participation"
        )
    
    with col2:
        # Calculate total student messages (user messages only)
        student_user_messages = df[
            (df['user_role'] == 'student') & 
            (df['message_role'] == 'user') & 
            (df['message_id'].notna())
        ]
        total_student_messages = len(student_user_messages)
        
        st.metric(
            label="📝 Total Student Messages",
            value=total_student_messages,
            delta=f"{student_chat_metrics.get('avg_messages_per_active_student', 0):.1f} avg/active student"
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
            value=f"{feedback_metrics.get('avg_rating', 0)*100:.1f}%",
            delta=f"{feedback_metrics.get('positive_feedback', 0)}/{feedback_metrics.get('total_feedback', 0)}"
        )
    
    # Chat Mode Analysis
    st.header("🎭 Chat Mode Analysis")
    
    if chat_mode_metrics:
        col1, col2, col3 = st.columns(3)

        with col1:
            if 'chat_session_percentages' in chat_mode_metrics and not chat_mode_metrics['chat_session_percentages'].empty:
                fig_sessions = px.pie(
                    values=chat_mode_metrics['chat_session_percentages'].values,
                    names=chat_mode_metrics['chat_session_percentages'].index,
                    title="Chat Session Distribution<br><sub>Number of chats started per mode</sub>",
                    color=chat_mode_metrics['chat_session_percentages'].index,
                    color_discrete_map={'Sokrates': '#FF6B6B', 'Aristoteles': '#4ECDC4'}
                )
                fig_sessions.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_sessions, use_container_width=True)

        with col2:
            if 'mode_percentages' in chat_mode_metrics and not chat_mode_metrics['mode_percentages'].empty:
                fig_messages = px.pie(
                    values=chat_mode_metrics['mode_percentages'].values,
                    names=chat_mode_metrics['mode_percentages'].index,
                    title="Message Distribution<br><sub>Total messages per mode</sub>",
                    color=chat_mode_metrics['mode_percentages'].index,
                    color_discrete_map={'Sokrates': '#FF6B6B', 'Aristoteles': '#4ECDC4'}
                )
                fig_messages.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_messages, use_container_width=True)
        
        with col3:
            if 'user_preferences' in chat_mode_metrics and not chat_mode_metrics['user_preferences'].empty:
                fig_pref = px.bar(
                    x=chat_mode_metrics['user_preferences'].index,
                    y=chat_mode_metrics['user_preferences'].values,
                    title="User Preferred Chat Mode<br><sub>Individual user preferences</sub>",
                    labels={'x': 'Chat Mode', 'y': 'Number of Users'},
                    color=chat_mode_metrics['user_preferences'].index,
                    color_discrete_map={
                        'Sokrates': '#FF6B6B', 
                        'Aristoteles': '#4ECDC4',
                        'Equal Usage': '#9B59B6'
                    }
                )
                fig_pref.update_layout(bargap=0.05, bargroupgap=0.0)
                fig_pref.update_traces(marker_line_width=0, width=0.8)
                st.plotly_chart(fig_pref, use_container_width=True)
    
    # Usage Patterns
    st.header("📅 Usage Patterns")
    st.info("**Course Session:** Activity on Saturday, 04 & 25 Oct. 2025, 10:15-13:00 reflects chat interactions during the course.")
    
    if usage_patterns and 'daily_usage' in usage_patterns:
        col1, col2 = st.columns(2)
        
        with col1:
            # Daily usage over time
            daily_df = usage_patterns['daily_usage'].reset_index()
            if not daily_df.empty:
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
            if 'hourly_usage' in usage_patterns and not usage_patterns['hourly_usage'].empty:
                hourly_usage = usage_patterns['hourly_usage']
                fig_hourly = px.bar(
                    x=hourly_usage.index,
                    y=hourly_usage.values,
                    title="Usage by Hour of Day",
                    labels={'x': 'Hour', 'y': 'Messages'},
                    color=hourly_usage.values,
                    color_continuous_scale='viridis'
                )
                fig_hourly.update_xaxes(dtick=1)
                st.plotly_chart(fig_hourly, use_container_width=True)
    
    # Feedback Analysis
    st.header("💭 Feedback Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Aristoteles feedback
        aristoteles_messages = df[
            (df['user_role'] == 'student') & 
            (df['chat_mode'] == 'Aristoteles') & 
            (df['message_role'] == 'assistant') & 
            (df['message_id'].notna())
        ]
        
        if not aristoteles_messages.empty:
            total_aristoteles_messages = len(aristoteles_messages)
            aristoteles_feedback = aristoteles_messages[aristoteles_messages['message_feedback_rating'].notna()]
            
            if not aristoteles_feedback.empty:
                positive_aristoteles = (aristoteles_feedback['message_feedback_rating'] == 1).sum()
                negative_aristoteles = (aristoteles_feedback['message_feedback_rating'] == 0).sum()
                total_aristoteles_feedback = len(aristoteles_feedback)
                
                feedback_labels = ['Positive 👍', 'Negative 👎', 'No Feedback']
                feedback_values = [
                    positive_aristoteles,
                    negative_aristoteles,
                    total_aristoteles_messages - total_aristoteles_feedback
                ]
                
                fig_feedback = px.pie(
                    values=feedback_values,
                    names=feedback_labels,
                    title="Aristoteles Feedback",
                    color=feedback_labels,
                    color_discrete_map={
                        'Positive 👍': '#2ECC71', 
                        'Negative 👎': '#E74C3C',
                        'No Feedback': '#95A5A6'
                    }
                )
                st.plotly_chart(fig_feedback, use_container_width=True)
            else:
                st.info("No Aristoteles feedback data available yet.")
        else:
            st.info("No Aristoteles messages available yet.")
    
    with col2:
        # Sokrates feedback
        sokrates_messages = df[
            (df['user_role'] == 'student') & 
            (df['chat_mode'] == 'Sokrates') & 
            (df['message_role'] == 'assistant') & 
            (df['message_id'].notna())
        ]
        
        if not sokrates_messages.empty:
            total_sokrates_messages = len(sokrates_messages)
            sokrates_feedback = sokrates_messages[sokrates_messages['message_feedback_rating'].notna()]
            
            if not sokrates_feedback.empty:
                positive_sokrates = (sokrates_feedback['message_feedback_rating'] == 1).sum()
                negative_sokrates = (sokrates_feedback['message_feedback_rating'] == 0).sum()
                total_sokrates_feedback = len(sokrates_feedback)
                
                feedback_labels = ['Positive 👍', 'Negative 👎', 'No Feedback']
                feedback_values = [
                    positive_sokrates,
                    negative_sokrates,
                    total_sokrates_messages - total_sokrates_feedback
                ]
                
                fig_feedback = px.pie(
                    values=feedback_values,
                    names=feedback_labels,
                    title="Sokrates Feedback",
                    color=feedback_labels,
                    color_discrete_map={
                        'Positive 👍': '#2ECC71', 
                        'Negative 👎': '#E74C3C',
                        'No Feedback': '#95A5A6'
                    }
                )
                st.plotly_chart(fig_feedback, use_container_width=True)
            else:
                st.info("No Sokrates feedback data available yet.")
        else:
            st.info("No Sokrates messages available yet.")
    
    # User Engagement
    st.header("👤 User Engagement")
    
    if engagement_metrics and 'user_interactions' in engagement_metrics:
        # Calculate interactions by mode for each user (user messages only)
        student_messages = df[
            (df['user_role'] == 'student') & 
            (df['message_role'] == 'user') & 
            (df['message_id'].notna())
        ]
        
        if not student_messages.empty:
            user_mode_interactions = student_messages.groupby(['user_id', 'chat_mode']).size().reset_index(name='interactions')
            
            # Create stacked histogram
            fig_engagement = px.histogram(
                user_mode_interactions,
                x='interactions',
                color='chat_mode',
                nbins=20,
                title="Distribution of User Interactions by Chat Mode",
                labels={'interactions': 'Number of Interactions', 'count': 'Number of Users'},
                color_discrete_map={'Sokrates': '#FF6B6B', 'Aristoteles': '#4ECDC4'},
                barmode='group'
            )
            fig_engagement.update_yaxes(title_text="Number of Users", dtick=1)
            st.plotly_chart(fig_engagement, use_container_width=True)
            
            # Mode-specific engagement statistics
            st.subheader("📊 Mode Comparison")
            
            sokrates_interactions = user_mode_interactions[user_mode_interactions['chat_mode'] == 'Sokrates']['interactions']
            aristoteles_interactions = user_mode_interactions[user_mode_interactions['chat_mode'] == 'Aristoteles']['interactions']
            
            comparison_data = {
                'Metric': [
                    'Most Active User (interactions)',
                    'Median Interactions per User',
                    'Users with 1 interaction only'
                ],
                'Aristoteles': [
                    f"{aristoteles_interactions.max()}" if len(aristoteles_interactions) > 0 else "No data",
                    f"{aristoteles_interactions.median():.0f}" if len(aristoteles_interactions) > 0 else "No data",
                    f"{(aristoteles_interactions == 1).sum()}" if len(aristoteles_interactions) > 0 else "No data"
                ],
                'Sokrates': [
                    f"{sokrates_interactions.max()}" if len(sokrates_interactions) > 0 else "No data",
                    f"{sokrates_interactions.median():.0f}" if len(sokrates_interactions) > 0 else "No data",
                    f"{(sokrates_interactions == 1).sum()}" if len(sokrates_interactions) > 0 else "No data"
                ]
            }
            
            comparison_df = pd.DataFrame(comparison_data)
            st.table(comparison_df)
    
    # Recent Activity
    st.header("🕐 Recent Activity")
    
    # Get recent chats
    recent_chat_messages = df[df['message_id'].notna()].copy()
    if not recent_chat_messages.empty:
        recent_chats = (recent_chat_messages.groupby(['chat_id', 'chat_mode'])
                       .agg({'message_created_at_local': 'max'})
                       .reset_index()
                       .sort_values('message_created_at_local', ascending=False)
                       .head(10))
        
        st.subheader("Latest Chat Sessions")
        for _, chat_row in recent_chats.iterrows():
            chat_id = chat_row['chat_id']
            chat_mode = chat_row['chat_mode']
            latest_time = chat_row['message_created_at_local']
            
            # Get all messages for this chat
            chat_messages = df[df['chat_id'] == chat_id].sort_values('message_created_at_local')
            
            # Get user role for this chat
            user_role = chat_messages['user_role'].iloc[0] if not chat_messages.empty else 'Unknown'
            user_role_display = user_role.title() if user_role else 'Unknown'
            
            message_count = len(chat_messages[chat_messages['message_id'].notna()])
            with st.expander(f"💬 {chat_mode} Chat - {user_role_display} User - {latest_time} ({message_count} messages)"):
                
                for _, message in chat_messages[chat_messages['message_id'].notna()].iterrows():
                    if message['message_role'] == 'user':
                        display_name = "👤 User"
                    elif message['message_role'] == 'assistant':
                        if chat_mode == 'Sokrates':
                            display_name = "🧙‍♂️ Sokrates"
                        else:
                            display_name = "🎓 Aristoteles"
                    else:
                        display_name = f"❓ {message['message_role'].title()}"
                    
                    st.markdown(f"**{display_name}:**")
                    content_preview = str(message['message_content'])[:300] + ('...' if len(str(message['message_content'])) > 300 else '')
                    st.markdown(f"_{content_preview}_")
                    
                    if message['message_role'] == 'assistant' and pd.notna(message['message_feedback_rating']):
                        rating = "👍 Positive" if message['message_feedback_rating'] == 1 else "👎 Negative"
                        st.markdown(f"**Feedback:** {rating}")
                        if pd.notna(message['message_feedback_text']) and str(message['message_feedback_text']).strip():
                            st.markdown(f"**Feedback Text:** _{message['message_feedback_text']}_")
                    
                    if message.name != chat_messages[chat_messages['message_id'].notna()].index[-1]:
                        st.markdown("---")
    
    # Data Export
    st.header("📤 Data Export")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Download Analytics Summary"):
            summary_data = {
                'Metric': [
                    'Total Registered Users',
                    'Students',
                    'Admins', 
                    'Testers',
                    'Students Who Chatted',
                    'Student Chat Participation Rate',
                    'Average Messages per Active Student',
                    'Active Students (7 days)',
                    'Returning Students',
                    'Total Student Feedback',
                    'Student Satisfaction Rate',
                    'Sokrates Usage %',
                    'Aristoteles Usage %'
                ],
                'Value': [
                    registration_metrics.get('total_registered', 0),
                    registration_metrics.get('students', 0),
                    registration_metrics.get('admins', 0),
                    registration_metrics.get('testers', 0),
                    student_chat_metrics.get('students_who_chatted', 0),
                    f"{student_chat_metrics.get('student_chat_participation_rate', 0):.1f}%",
                    f"{student_chat_metrics.get('avg_messages_per_active_student', 0):.2f}",
                    engagement_metrics.get('active_users_7d', 0),
                    engagement_metrics.get('returning_users', 0),
                    feedback_metrics.get('total_feedback', 0),
                    f"{feedback_metrics.get('avg_rating', 0):.2f}",
                    f"{chat_mode_metrics.get('mode_percentages', {}).get('Sokrates', 0):.1f}%" if chat_mode_metrics else "0%",
                    f"{chat_mode_metrics.get('mode_percentages', {}).get('Aristoteles', 0):.1f}%" if chat_mode_metrics else "0%"
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
        if st.button("📋 Download Raw Dataset"):
            # Prepare raw data for download
            raw_csv = df.to_csv(index=False)
            st.download_button(
                label="Download Raw Data CSV",
                data=raw_csv,
                file_name=f"chatbot_raw_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col3:
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