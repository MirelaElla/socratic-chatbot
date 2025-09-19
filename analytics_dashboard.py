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
def fetch_analytics_data():
    """Fetch all analytics data including user profiles"""
    supabase = get_supabase_client()
    
    try:
        # Fetch user profiles data for registration statistics
        # Try using the new SQL function first, which bypasses RLS
        try:
            users_response = supabase.rpc('get_all_user_profiles').execute()
            user_profiles_data = pd.DataFrame(users_response.data) if users_response.data else pd.DataFrame()
        except:
            # Fallback to direct table query (will be limited by RLS)
            users_response = supabase.table("user_profiles").select("id, user_role, created_at").execute()
            user_profiles_data = pd.DataFrame(users_response.data) if users_response.data else pd.DataFrame()
        
        # Fetch chat data from the new structure with JOINs to get comprehensive data
        # The SQL function now returns created_at_local
        
        # Execute the query using Supabase RPC or direct query
        try:
            # Try using a direct query first
            response = supabase.rpc('get_analytics_data').execute()
            if response.data:
                chat_data = pd.DataFrame(response.data)
            else:
                # Fallback to separate queries if RPC doesn't exist
                raise Exception("RPC not found, using fallback")
        except Exception as e:
            # Fallback: Fetch data separately and join in Python
            chats_response = supabase.table("chats").select("id, user_id, mode, created_at").execute()
            messages_response = supabase.table("chat_messages").select("*").execute()
            
            if chats_response.data and messages_response.data:
                chats_df = pd.DataFrame(chats_response.data)
                messages_df = pd.DataFrame(messages_response.data)
                
                # Join the data
                chat_data = messages_df.merge(
                    chats_df[['id', 'user_id', 'mode']], 
                    left_on='chat_id', 
                    right_on='id', 
                    suffixes=('', '_chat')
                )
                chat_data = chat_data.rename(columns={'mode': 'chat_mode'})
                chat_data = chat_data.drop(columns=['id_chat'])
            else:
                chat_data = pd.DataFrame()
        
        # Add user_role information to chat_data if both datasets are available
        if not chat_data.empty and not user_profiles_data.empty:
            chat_data = chat_data.merge(
                user_profiles_data[['id', 'user_role']], 
                left_on='user_id', 
                right_on='id', 
                how='left',
                suffixes=('', '_profile')
            )
            chat_data = chat_data.drop(columns=['id_profile'])
        
        # Ensure created_at_local exists and is properly converted to datetime
        if not chat_data.empty:
            if 'created_at_local' not in chat_data.columns:
                # Convert created_at to local timezone (Europe/Zurich)
                try:
                    chat_data['created_at_local'] = pd.to_datetime(chat_data['created_at']).dt.tz_convert('Europe/Zurich').dt.tz_localize(None)
                except Exception:
                    # If created_at is naive, localize to UTC first
                    chat_data['created_at_local'] = pd.to_datetime(chat_data['created_at']).dt.tz_localize('UTC').dt.tz_convert('Europe/Zurich').dt.tz_localize(None)
            else:
                # Ensure created_at_local is datetime type, not string
                chat_data['created_at_local'] = pd.to_datetime(chat_data['created_at_local'])
        
        return chat_data, user_profiles_data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame(), pd.DataFrame()

def calculate_user_profile_metrics(user_profiles_df):
    """Calculate metrics from user_profiles table"""
    if user_profiles_df.empty:
        return {
            'total_registered': 0,
            'students': 0,
            'admins': 0,
            'testers': 0,
            'role_breakdown': {}
        }
    
    total_registered = len(user_profiles_df)
    role_counts = user_profiles_df['user_role'].value_counts()
    
    return {
        'total_registered': total_registered,
        'students': role_counts.get('student', 0),
        'admins': role_counts.get('admin', 0),
        'testers': role_counts.get('tester', 0),
        'role_breakdown': role_counts.to_dict()
    }

def calculate_student_chat_metrics(chat_df, user_profiles_df):
    """Calculate chat metrics specifically for student users"""
    if chat_df.empty or user_profiles_df.empty:
        return {
            'students_who_chatted': 0,
            'total_students': 0,
            'avg_messages_per_student': 0.0,
            'student_chat_participation_rate': 0.0
        }
    
    # Get all student user IDs
    student_users = user_profiles_df[user_profiles_df['user_role'] == 'student']['id'].tolist()
    total_students = len(student_users)
    
    # Filter chat data to only student users
    student_chat_df = chat_df[chat_df['user_id'].isin(student_users)]
    
    if student_chat_df.empty:
        return {
            'students_who_chatted': 0,
            'total_students': total_students,
            'avg_messages_per_student': 0.0,
            'student_chat_participation_rate': 0.0
        }
    
    # Count unique students who have sent messages
    students_who_chatted = student_chat_df['user_id'].nunique()
    
    # Calculate average messages per student (including those who haven't chatted)
    total_student_messages = len(student_chat_df)
    avg_messages_per_student = total_student_messages / total_students if total_students > 0 else 0
    
    # Calculate average messages per ACTIVE student (only those who have chatted)
    avg_messages_per_active_student = total_student_messages / students_who_chatted if students_who_chatted > 0 else 0
    
    # Calculate participation rate
    participation_rate = (students_who_chatted / total_students * 100) if total_students > 0 else 0
    
    return {
        'students_who_chatted': students_who_chatted,
        'total_students': total_students,
        'avg_messages_per_student': avg_messages_per_student,
        'avg_messages_per_active_student': avg_messages_per_active_student,
        'student_chat_participation_rate': participation_rate
    }

def calculate_user_metrics(df):
    """Calculate user-related metrics for student users only"""
    if df.empty:
        return {}
    
    # Filter to student users only if user_role column exists
    if 'user_role' in df.columns:
        df = df[df['user_role'] == 'student']
    
    if df.empty:
        return {}
    
    # Ensure created_at_local exists and is datetime type
    if 'created_at_local' not in df.columns:
        df['created_at_local'] = pd.to_datetime(df['created_at']).dt.tz_localize('UTC').dt.tz_convert('Europe/Zurich').dt.tz_localize(None)
    else:
        # Ensure it's datetime type
        df['created_at_local'] = pd.to_datetime(df['created_at_local'])
    
    # Unique users (students only)
    unique_users = df['user_id'].nunique()
    
    # User interactions (messages per student user)
    user_interactions = df.groupby('user_id').size()
    avg_interactions = user_interactions.mean()
    
    # Active users (student users who interacted in the last 7 days)
    last_week = pd.Timestamp.now() - timedelta(days=7)
    recent_users = df[df['created_at_local'] > last_week]['user_id'].nunique()
    
    # User retention (student users who came back)
    user_sessions = df.groupby('user_id')['created_at_local'].apply(lambda x: x.dt.date.nunique())
    returning_users = (user_sessions > 1).sum()
    
    return {
        'unique_users': unique_users,
        'avg_interactions': avg_interactions,
        'active_users_7d': recent_users,
        'returning_users': returning_users,
        'user_interactions': user_interactions
    }

def calculate_chat_mode_metrics(df):
    """Calculate chat mode usage metrics for student users only"""
    if df.empty:
        return {}
    
    # Filter to student users only if user_role column exists
    if 'user_role' in df.columns:
        df = df[df['user_role'] == 'student']
    
    if df.empty:
        return {}
    
    # Chat mode distribution (MESSAGE-based)
    mode_counts = df['chat_mode'].value_counts()
    mode_percentages = (mode_counts / mode_counts.sum() * 100).round(2)
    
    # Chat session distribution (CHAT SESSION-based - like SQL query)
    chat_session_counts = df.groupby('chat_id')['chat_mode'].first().value_counts()
    chat_session_percentages = (chat_session_counts / chat_session_counts.sum() * 100).round(2)
    
    # User preference (which mode each user uses most, with equal usage detection)
    def determine_user_preference(user_messages):
        mode_counts = user_messages.value_counts()
        if len(mode_counts) == 0:
            return 'Unknown'
        elif len(mode_counts) == 1:
            # User only used one mode
            return mode_counts.index[0]
        elif len(mode_counts) == 2 and mode_counts.iloc[0] == mode_counts.iloc[1]:
            # User used both modes equally
            return 'Equal Usage'
        else:
            # User has a clear preference
            return mode_counts.index[0]
    
    user_mode_preference = df.groupby('user_id')['chat_mode'].apply(determine_user_preference)
    user_preference_counts = user_mode_preference.value_counts()
    
    return {
        'mode_counts': mode_counts,  # Messages per mode
        'mode_percentages': mode_percentages,  # Message percentages
        'chat_session_counts': chat_session_counts,  # Chat sessions per mode
        'chat_session_percentages': chat_session_percentages,  # Chat session percentages
        'user_preferences': user_preference_counts
    }

def calculate_feedback_metrics(df):
    """Calculate feedback-related metrics for student users only"""
    if df.empty:
        return {}
    
    # Filter to student users only if user_role column exists
    if 'user_role' in df.columns:
        df = df[df['user_role'] == 'student']
    
    if df.empty:
        return {
            'total_feedback': 0,
            'positive_feedback': 0,
            'negative_feedback': 0,
            'feedback_rate': 0,
            'avg_rating': 0
        }
    
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
    """Calculate usage patterns over time for student users only"""
    if df.empty:
        return {}
    
    # Filter to student users only if user_role column exists
    if 'user_role' in df.columns:
        df = df[df['user_role'] == 'student']
    
    if df.empty:
        return {}
    
    df['created_at_local'] = pd.to_datetime(df['created_at_local'])
    df['date'] = df['created_at_local'].dt.date
    df['hour'] = df['created_at_local'].dt.hour
    df['day_of_week'] = df['created_at_local'].dt.day_name()
    
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
    
    # Fetch data
    with st.spinner("Loading analytics data..."):
        df, user_profiles_df = fetch_analytics_data()
    
    if user_profiles_df.empty:
        st.warning("No user profile data available!")
        return
    
    # Calculate user profile metrics
    profile_metrics = calculate_user_profile_metrics(user_profiles_df)
    student_chat_metrics = calculate_student_chat_metrics(df, user_profiles_df)
    
    # User Registration Overview
    st.header("👥 User Registration Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📝 Total Registered Users",
            value=profile_metrics.get('total_registered', 0),
            delta=None
        )
    
    with col2:
        st.metric(
            label="🎓 Students",
            value=profile_metrics.get('students', 0),
            delta=f"{profile_metrics.get('students', 0)/profile_metrics.get('total_registered', 1)*100:.1f}%" if profile_metrics.get('total_registered', 0) > 0 else "0%"
        )
    
    with col3:
        st.metric(
            label="👑 Admins",
            value=profile_metrics.get('admins', 0),
            delta=f"{profile_metrics.get('admins', 0)/profile_metrics.get('total_registered', 1)*100:.1f}%" if profile_metrics.get('total_registered', 0) > 0 else "0%"
        )
    
    with col4:
        st.metric(
            label="🧪 Testers",
            value=profile_metrics.get('testers', 0),
            delta=f"{profile_metrics.get('testers', 0)/profile_metrics.get('total_registered', 1)*100:.1f}%" if profile_metrics.get('total_registered', 0) > 0 else "0%"
        )
    
    if df.empty:
        st.warning("No chat data available yet. Student users haven't started chatting!")
        return
    
    # Calculate metrics (now filtered for students only)
    user_metrics = calculate_user_metrics(df)
    chat_metrics = calculate_chat_mode_metrics(df)
    feedback_metrics = calculate_feedback_metrics(df)
    usage_metrics = calculate_usage_patterns(df)
    
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
        # Calculate total student messages from the filtered dataframe (only user messages, exclude assistant)
        if 'user_role' in df.columns and 'role' in df.columns:
            student_user_messages = df[(df['user_role'] == 'student') & (df['role'] == 'user')]
            total_student_messages = len(student_user_messages)
        else:
            total_student_messages = 0
        
        st.metric(
            label="📝 Total Student Messages",
            value=total_student_messages,
            delta=f"{total_student_messages/student_chat_metrics.get('students_who_chatted', 1):.1f} avg/student" if student_chat_metrics.get('students_who_chatted', 0) > 0 else "No active students"
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
    
    # Create three columns for the different metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        if 'chat_session_percentages' in chat_metrics and not chat_metrics['chat_session_percentages'].empty:
            fig_sessions = px.pie(
                values=chat_metrics['chat_session_percentages'].values,
                names=chat_metrics['chat_session_percentages'].index,
                title="Chat Session Distribution<br><sub>Number of chats started per mode</sub>",
                color=chat_metrics['chat_session_percentages'].index,
                color_discrete_map={'Sokrates': '#FF6B6B', 'Aristoteles': '#4ECDC4'}
            )
            fig_sessions.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_sessions, use_container_width=True)

    with col2:
        if 'mode_percentages' in chat_metrics and not chat_metrics['mode_percentages'].empty:
            fig_messages = px.pie(
                values=chat_metrics['mode_percentages'].values,
                names=chat_metrics['mode_percentages'].index,
                title="Message Distribution<br><sub>Total messages per mode</sub>",
                color=chat_metrics['mode_percentages'].index,
                color_discrete_map={'Sokrates': '#FF6B6B', 'Aristoteles': '#4ECDC4'}
            )
            fig_messages.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_messages, use_container_width=True)
    
    with col3:
        if 'user_preferences' in chat_metrics and not chat_metrics['user_preferences'].empty:
            fig_pref = px.bar(
                x=chat_metrics['user_preferences'].index,
                y=chat_metrics['user_preferences'].values,
                title="User Preferred Chat Mode<br><sub>Individual user preferences</sub>",
                labels={'x': 'Chat Mode', 'y': 'Number of Users'},
                color=chat_metrics['user_preferences'].index,
                color_discrete_map={
                    'Sokrates': '#FF6B6B', 
                    'Aristoteles': '#4ECDC4',
                    'Equal Usage': '#9B59B6'
                }
            )
            fig_pref.update_layout(bargap=0.05, bargroupgap=0.0)  # Make bars closer together
            fig_pref.update_traces(marker_line_width=0, width=0.8)  # Thicker bars
            st.plotly_chart(fig_pref, use_container_width=True)
    
    # Explanation of the metrics
    with st.expander("ℹ️ Understanding Chat Mode Metrics"):
        st.markdown("""
        **Three Different Perspectives on Chat Mode Usage:**
        
        1. **Chat Session Distribution**: Shows which mode students prefer to initiate conversations with 
                    
        2. **Message Distribution**: Shows which mode generates more conversation/engagement

        3. **User Preferences**: Shows how many individual users prefer each mode
        """)
    
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
                hourly_usage = usage_metrics['hourly_usage']
                fig_hourly = px.bar(
                    x=hourly_usage.index,
                    y=hourly_usage.values,
                    title="Usage by Hour of Day",
                    labels={'x': 'Hour', 'y': 'Messages'},
                    color=hourly_usage.values,
                    color_continuous_scale='viridis'
                )
                fig_hourly.update_xaxes(dtick=1, tickmode='array', tickvals=list(hourly_usage.index), ticktext=[str(h) for h in hourly_usage.index])
                st.plotly_chart(fig_hourly, use_container_width=True)
    
    # Feedback Analysis
    st.header("💭 Feedback Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Overall feedback distribution relative to total messages for Aristoteles
        aristoteles_df = df[df['chat_mode'] == 'Aristoteles']
        total_aristoteles_messages = (aristoteles_df['role'] == 'assistant').sum()
        aristoteles_feedback = aristoteles_df[(aristoteles_df['role'] == 'assistant') & (aristoteles_df['feedback_rating'].notna())]
        
        if len(aristoteles_feedback) > 0 and total_aristoteles_messages > 0:
            positive_aristoteles = (aristoteles_feedback['feedback_rating'] == 1).sum()
            negative_aristoteles = (aristoteles_feedback['feedback_rating'] == 0).sum()
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
    
    with col2:
        # Overall feedback distribution relative to total messages for Sokrates
        sokrates_df = df[df['chat_mode'] == 'Sokrates']
        total_sokrates_messages = (sokrates_df['role'] == 'assistant').sum()
        sokrates_feedback = sokrates_df[(sokrates_df['role'] == 'assistant') & (sokrates_df['feedback_rating'].notna())]
        
        if len(sokrates_feedback) > 0 and total_sokrates_messages > 0:
            positive_sokrates = (sokrates_feedback['feedback_rating'] == 1).sum()
            negative_sokrates = (sokrates_feedback['feedback_rating'] == 0).sum()
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
    
    # User Engagement
    st.header("👤 User Engagement")
    
    if 'user_interactions' in user_metrics:
        # Calculate interactions by mode for each user
        user_mode_interactions = df.groupby(['user_id', 'chat_mode']).size().reset_index(name='interactions')
        
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
        fig_engagement.update_yaxes(title_text="Number of Users")
        st.plotly_chart(fig_engagement, use_container_width=True)
        
        # Mode-specific engagement statistics
        st.subheader("📊 Mode Comparison")
        
        # Calculate metrics for both modes
        sokrates_interactions = user_mode_interactions[user_mode_interactions['chat_mode'] == 'Sokrates']['interactions']
        aristoteles_interactions = user_mode_interactions[user_mode_interactions['chat_mode'] == 'Aristoteles']['interactions']
        
        # Create comparison table
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
    
    # Get recent chats (last 10) based on the most recent message in each chat
    recent_chats = (df.groupby(['chat_id', 'chat_mode'])
                   .agg({'created_at_local': 'max'})
                   .reset_index()
                   .sort_values('created_at_local', ascending=False)
                   .head(10))
    
    st.subheader("Latest Chat Sessions")
    for _, chat_row in recent_chats.iterrows():
        chat_id = chat_row['chat_id']
        chat_mode = chat_row['chat_mode']
        latest_time = chat_row['created_at_local']
        
        # Get all messages for this chat
        chat_messages = df[df['chat_id'] == chat_id].sort_values('created_at_local')
        
        # Create expander title with chat info
        message_count = len(chat_messages)
        with st.expander(f"💬 {chat_mode} Chat - {latest_time} ({message_count} messages)"):
            
            # Display all messages in the chat
            for _, message in chat_messages.iterrows():
                # Determine the display name based on role and chat mode
                if message['role'] == 'user':
                    display_name = "👤 User"
                elif message['role'] == 'assistant':
                    if chat_mode == 'Sokrates':
                        display_name = "🧙‍♂️ Sokrates"
                    else:  # Aristoteles
                        display_name = "🎓 Aristoteles"
                else:
                    display_name = f"❓ {message['role'].title()}"
                
                # Display message content
                st.markdown(f"**{display_name}:**")
                content_preview = message['content'][:300] + ('...' if len(message['content']) > 300 else '')
                st.markdown(f"_{content_preview}_")
                
                # Show feedback only for assistant messages
                if message['role'] == 'assistant' and pd.notna(message['feedback_rating']):
                    if message['feedback_rating'] == 1:
                        rating = "👍 Positive"
                    elif message['feedback_rating'] == 0:
                        rating = "👎 Negative"
                    else:
                        rating = "❓ Unknown"
                    st.markdown(f"**Feedback:** {rating}")
                    if pd.notna(message['feedback_text']) and message['feedback_text'].strip():
                        st.markdown(f"**Feedback Text:** _{message['feedback_text']}_")
                
                # Add separator between messages (except for the last one)
                if message.name != chat_messages.index[-1]:
                    st.markdown("---")
    
    # Data Export
    st.header("📤 Data Export")
    col1, col2 = st.columns(2)
    
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
                    profile_metrics.get('total_registered', 0),
                    profile_metrics.get('students', 0),
                    profile_metrics.get('admins', 0),
                    profile_metrics.get('testers', 0),
                    student_chat_metrics.get('students_who_chatted', 0),
                    f"{student_chat_metrics.get('student_chat_participation_rate', 0):.1f}%",
                    f"{student_chat_metrics.get('avg_messages_per_active_student', 0):.2f}",
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
