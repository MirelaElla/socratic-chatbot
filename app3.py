import streamlit as st
from openai import OpenAI
import os
import re
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Supabase client for auth using Streamlit secrets
@st.cache_resource
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# Page configuration
st.set_page_config(page_title="Chatbot Memory")

def is_valid_email(email):
    """Check if email is valid and ends with allowed domains"""
    pattern = r'^[a-zA-Z0-9._%+-]+@(unidistance\.ch|fernuni\.ch)$'
    return re.match(pattern, email) is not None

def authenticate_user(email, password):
    """Authenticate user with Supabase Auth"""
    supabase = get_supabase_client()
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return response.user
    except Exception as e:
        st.error(f"Login error: {e}")
        return None

def handle_auth_callback():
    """Handle authentication callback after email confirmation"""
    # Check for auth callback parameters in URL
    query_params = st.query_params
    
    # Check for different possible parameter combinations
    if "access_token" in query_params and "refresh_token" in query_params:
        supabase = get_supabase_client()
        try:
            # Set the session with the tokens from URL
            supabase.auth.set_session(
                query_params["access_token"],
                query_params["refresh_token"]
            )
            
            # Get user info
            user = supabase.auth.get_user()
            if user and user.user:
                st.session_state.authenticated = True
                st.session_state.user_email = user.user.email
                st.session_state.user_id = user.user.id
                
                # Clear the URL parameters and redirect
                st.query_params.clear()
                st.success("✅ E-Mail erfolgreich bestätigt! Sie sind jetzt angemeldet.")
                st.rerun()
                
        except Exception as e:
            st.error(f"Fehler bei der E-Mail-Bestätigung: {e}")
    
    # Check for any confirmation-related parameters
    elif any(param in query_params for param in ["token_hash", "type", "confirmation_url", "email_confirmed"]):
        # Set a flag in session state to show confirmation message
        st.session_state.email_confirmed = True
        st.query_params.clear()
        st.rerun()
    
    elif "error" in query_params:
        st.error(f"❌ Fehler bei der E-Mail-Bestätigung: {query_params.get('error_description', 'Unbekannter Fehler')}")
        st.query_params.clear()

def sign_up_user(email, password):
    """Sign up new user with Supabase Auth"""
    supabase = get_supabase_client()
    try:
        # Get the current app URL for redirect
        # For localhost development, Streamlit typically runs on port 8501
        redirect_url = "http://localhost:8501"
        
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "email_redirect_to": redirect_url
            }
        })
        return response.user
    except Exception as e:
        st.error(f"Sign up error: {e}")
        return None

def save_chat_message(user_id, role, content):
    """Save chat message to Supabase"""
    # Check if session is still valid before saving
    if not check_session_validity():
        st.error("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
        st.rerun()
        return None
    
    supabase = get_supabase_client()
    try:
        result = supabase.table("chat_history").insert({
            "user_id": str(user_id),  # Ensure user_id is string format
            "role": role,
            "content": content
        }).execute()
        return result
    except Exception as e:
        # Check if this is a JWT expiration error
        if "JWT expired" in str(e) or "PGRST301" in str(e):
            st.error("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
            # Clear session and redirect to login
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state.user_id = None
            if "messages" in st.session_state:
                del st.session_state.messages
            st.rerun()
        else:
            st.error(f"Error saving message: {e}")
        return None

def load_chat_history(user_id):
    """Load chat history from Supabase"""
    # Check if session is still valid before loading
    if not check_session_validity():
        return []
    
    supabase = get_supabase_client()
    try:
        result = supabase.table("chat_history").select("role, content").eq("user_id", str(user_id)).order("created_at").execute()
        return [{"role": msg["role"], "content": msg["content"]} for msg in result.data]
    except Exception as e:
        # Check if this is a JWT expiration error
        if "JWT expired" in str(e) or "PGRST301" in str(e):
            st.error("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
            # Clear session and redirect to login
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state.user_id = None
            if "messages" in st.session_state:
                del st.session_state.messages
            st.rerun()
        else:
            st.error(f"Error loading chat history: {e}")
        return []

def sign_out_user():
    """Sign out user from Supabase Auth"""
    supabase = get_supabase_client()
    try:
        supabase.auth.sign_out()
    except Exception as e:
        st.error(f"Sign out error: {e}")

def check_session_validity():
    """Check if the current session is still valid and refresh if needed"""
    if not st.session_state.get("authenticated", False):
        return False
    
    supabase = get_supabase_client()
    try:
        # Try to get current user - this will fail if token is expired
        user = supabase.auth.get_user()
        if user and user.user:
            return True
        else:
            # Session is invalid, clear it
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state.user_id = None
            if "messages" in st.session_state:
                del st.session_state.messages
            return False
    except Exception as e:
        # Session is invalid or expired
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.user_id = None
        if "messages" in st.session_state:
            del st.session_state.messages
        return False

def show_login():
    """Display login form"""
    st.image("assets/Unidistance_Logo_couleur_RVB.png", width=200)
    st.title("🔐 Anmeldung erforderlich")
    st.markdown("""
    **Zugang nur für Studierende und Mitarbeitende der Universität**
    
    Bitte geben Sie Ihre institutionelle E-Mail-Adresse ein:
    
    ⚠️ **Hinweis**: Ihre Sitzung läuft nach längerer Inaktivität automatisch ab. 
    Falls Sie eine Fehlermeldung bezüglich einer abgelaufenen Sitzung erhalten, melden Sie sich bitte erneut an.
    """)
    
    # Check if user just came from email confirmation
    if st.session_state.get("email_confirmed", False):
        st.success("✅ E-Mail erfolgreich bestätigt! Ihr Account ist aktiviert.")
        st.info("👇 Sie können sich jetzt mit Ihren Anmeldedaten anmelden.")
        # Clear the flag so it doesn't show again
        st.session_state.email_confirmed = False
    
    # Create tabs for login and signup
    tab1, tab2 = st.tabs(["Anmelden", "Registrieren"])
    
    with tab1:
        st.subheader("Bestehenden Account verwenden")
        with st.form("login_form"):
            email = st.text_input(
                "E-Mail-Adresse", 
                placeholder="vorname.nachname@unidistance.ch",
                help="Nur E-Mail-Adressen mit @unidistance.ch oder @fernuni.ch sind zugelassen",
                key="login_email"
            )
            password = st.text_input(
                "Passwort", 
                type="password",
                key="login_password"
            )
            submit_login = st.form_submit_button("Anmelden")
            
            if submit_login:
                if email and password and is_valid_email(email):
                    user = authenticate_user(email, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.session_state.user_id = user.id
                        # Clear any remaining URL parameters
                        st.query_params.clear()
                        st.success("✅ Erfolgreich angemeldet!")
                        st.rerun()
                    else:
                        st.error("❌ Ungültige Anmeldedaten. Bitte überprüfen Sie E-Mail und Passwort.")
                elif email and not is_valid_email(email):
                    st.error("❌ Ungültige E-Mail-Adresse. Bitte verwenden Sie eine @unidistance.ch oder @fernuni.ch Adresse.")
                else:
                    st.error("❌ Bitte füllen Sie alle Felder aus.")
    
    with tab2:
        st.subheader("Neuen Account erstellen")
        with st.form("signup_form"):
            signup_email = st.text_input(
                "E-Mail-Adresse", 
                placeholder="vorname.nachname@unidistance.ch",
                help="Nur E-Mail-Adressen mit @unidistance.ch oder @fernuni.ch sind zugelassen",
                key="signup_email"
            )
            signup_password = st.text_input(
                "Passwort", 
                type="password",
                help="Mindestens 6 Zeichen",
                key="signup_password"
            )
            confirm_password = st.text_input(
                "Passwort bestätigen", 
                type="password",
                key="confirm_password"
            )
            submit_signup = st.form_submit_button("Registrieren")
            
            if submit_signup:
                if signup_email and signup_password and confirm_password:
                    if not is_valid_email(signup_email):
                        st.error("❌ Ungültige E-Mail-Adresse. Bitte verwenden Sie eine @unidistance.ch oder @fernuni.ch Adresse.")
                    elif len(signup_password) < 6:
                        st.error("❌ Passwort muss mindestens 6 Zeichen lang sein.")
                    elif signup_password != confirm_password:
                        st.error("❌ Passwörter stimmen nicht überein.")
                    else:
                        user = sign_up_user(signup_email, signup_password)
                        if user:
                            st.success("✅ Account erfolgreich erstellt! Bitte überprüfen Sie Ihre E-Mail zur Bestätigung, dann können Sie sich anmelden.")
                        else:
                            st.error("❌ Fehler beim Erstellen des Accounts. Möglicherweise existiert die E-Mail bereits.")
                else:
                    st.error("❌ Bitte füllen Sie alle Felder aus.")

def show_main_app():
    """Display the main chatbot application"""
    # Check session validity at the start of main app
    if not check_session_validity():
        st.error("Ihre Sitzung ist abgelaufen. Sie werden zur Anmeldung weitergeleitet.")
        st.rerun()
        return
    
    # App title
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("assets/Unidistance_Logo_couleur_RVB.png", width=150)
    with col2:
        st.markdown(f"""
        **Angemeldet als:** {st.session_state.user_email}
        
        *This is a digital teaching and learning tool designed for psychology courses. It helps students explore and understand memory-related concepts and relationships through guided Socratic dialogue.*
        """)
        if st.button("Abmelden", type="secondary"):
            sign_out_user()
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state.user_id = None
            if "messages" in st.session_state:
                del st.session_state.messages
            st.rerun()

    st.title("💬 Chatbot zum Buch 'Memory'")

    # Initialize session state for messages and load chat history
    if "messages" not in st.session_state:
        if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
            st.session_state.messages = load_chat_history(st.session_state.user_id)
        else:
            st.session_state.messages = []

    # Instruction
    with st.expander("ℹ️ So funktioniert's:"):
        st.markdown("""
        Stelle eine Frage zum Buch *Memory* von Baddeley et al. und chatte mit dem Bot, um zentrale Konzepte erklärt zu bekommen.
        """)

    # Chat input
    user_input = st.chat_input("Frage etwas über Gedächtnis...")

    # Append user input
    if user_input:
        # Check session validity before processing the message
        if not check_session_validity():
            st.error("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
            st.rerun()
            return
            
        st.session_state.messages.append({"role": "user", "content": user_input})
        # Save user message to database
        save_result = save_chat_message(st.session_state.user_id, "user", user_input)
        
        # If saving failed due to session expiry, don't continue with API call
        if save_result is None:
            return

        # Compose full conversation
        messages = [{"role": "system", "content": 
            """ Du bist ein Tutor, der ausschliesslich Fragen von Studierenden zum Buch 'Memory' von Baddeley et al. beantwortet.
            Deine Aufgabe ist es, korrekte, präzise, kurze und informative Antworten zu geben.
            Weigere dich, Fragen zu beantworten oder Gespräche fortzusetzen, die nicht den Inhalt des Buches betreffen.
            """}]

        for msg in st.session_state.messages:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Call OpenAI API
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.2,
            )
            reply = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": reply})
            # Save assistant message to database
            save_chat_message(st.session_state.user_id, "assistant", reply)
        except Exception as e:
            st.error(f"API Error: {e}")
            # Remove the user message from session if API call failed
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                st.session_state.messages.pop()

    # Display messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").markdown(msg["content"])
        else:
            st.chat_message("assistant").markdown(msg["content"])

# Check authentication status
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Handle auth callback from email confirmation
if not st.session_state.authenticated:
    handle_auth_callback()

# Check session validity before showing the app
if st.session_state.authenticated:
    if not check_session_validity():
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.user_id = None
        if "messages" in st.session_state:
            del st.session_state.messages

# Show appropriate interface based on authentication
if not st.session_state.authenticated:
    show_login()
else:
    show_main_app()
