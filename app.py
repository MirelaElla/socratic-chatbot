import streamlit as st
from openai import OpenAI
import os
import re
from dotenv import load_dotenv
from supabase import create_client
from streamlit_feedback import streamlit_feedback

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Supabase client for auth using Streamlit secrets
@st.cache_resource
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def get_authenticated_supabase_client():
    """Get a Supabase client with current user authentication"""
    supabase = get_supabase_client()
    
    # Check if we have a valid session
    if st.session_state.get("authenticated", False):
        try:
            # Get the current user to verify the session is still valid
            user = supabase.auth.get_user()
            if user and user.user:
                return supabase
        except Exception as e:
            print(f"Auth check failed: {e}")
            
    return None

# Page configuration
st.set_page_config(page_title="Chatbot Memory")

def is_valid_email(email):
    """Check if email is valid and ends with allowed domains"""
    pattern = r'^[a-zA-Z0-9._%+-]+@(unidistance\.ch|fernuni\.ch|etu\.unidistance\.ch|stu\.fernuni\.ch)$'
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

def save_feedback(message_id, feedback_rating, feedback_text=None):
    """Save user feedback for an assistant message"""
    if not check_session_validity():
        st.error("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
        st.rerun()
        return None
    
    supabase = get_authenticated_supabase_client()
    if not supabase:
        st.error("Authentifizierung fehlgeschlagen. Bitte melden Sie sich erneut an.")
        return None
        
    try:
        # Update the specific message with feedback
        data = {
            "feedback_rating": feedback_rating,
            "feedback_text": feedback_text
        }
        
        # Update chat_messages table instead of chat_history
        result = supabase.table("chat_messages").update(data).eq("id", message_id).execute()
        
        # Check if the update was successful
        if result.data and len(result.data) > 0:
            st.success("Vielen Dank fürs Feedback!", icon="✅")
            return result
        else:
            st.warning(f"Nachricht mit ID {message_id} nicht gefunden oder Berechtigung verweigert.")
            return None
            
    except Exception as e:
        if "JWT expired" in str(e) or "PGRST301" in str(e):
            st.error("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state.user_id = None
            if "messages" in st.session_state:
                del st.session_state.messages
            if "message_ids" in st.session_state:
                del st.session_state.message_ids
            if "current_chat_id" in st.session_state:
                del st.session_state.current_chat_id
            st.rerun()
        else:
            st.error(f"Error saving feedback: {e}")
            print(f"Feedback save error: {e}")  # Log error for monitoring
        return None

def create_new_chat(user_id, mode):
    """Create a new chat session"""
    if not check_session_validity():
        st.error("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
        st.rerun()
        return None
    
    supabase = get_authenticated_supabase_client()
    if not supabase:
        st.error("Authentifizierung fehlgeschlagen. Bitte melden Sie sich erneut an.")
        return None
        
    try:
        data = {
            "user_id": str(user_id),
            "mode": mode
        }
        
        result = supabase.table("chats").insert(data).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]["id"]
        return None
    except Exception as e:
        if "JWT expired" in str(e) or "PGRST301" in str(e):
            st.error("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state.user_id = None
            if "messages" in st.session_state:
                del st.session_state.messages
            if "message_ids" in st.session_state:
                del st.session_state.message_ids
            if "current_chat_id" in st.session_state:
                del st.session_state.current_chat_id
            st.rerun()
        else:
            st.error(f"Error creating new chat: {e}")
        return None

def save_chat_message(chat_id, role, content):
    """Save chat message to the new chat_messages table"""
    if not check_session_validity():
        st.error("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
        st.rerun()
        return None
    
    supabase = get_authenticated_supabase_client()
    if not supabase:
        st.error("Authentifizierung fehlgeschlagen. Bitte melden Sie sich erneut an.")
        return None
        
    try:
        data = {
            "chat_id": chat_id,
            "role": role,
            "content": content
        }
            
        result = supabase.table("chat_messages").insert(data).execute()
        # Return the inserted record's ID if successful
        if result.data and len(result.data) > 0:
            return result.data[0]["id"]
        return result
    except Exception as e:
        # Check if this is a JWT expiration error
        if "JWT expired" in str(e) or "PGRST301" in str(e):
            st.error("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
            # Clear session and redirect to login
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state.user_id = None
            st.session_state.user_id = None
            if "messages" in st.session_state:
                del st.session_state.messages
            if "message_ids" in st.session_state:
                del st.session_state.message_ids
            if "current_chat_id" in st.session_state:
                del st.session_state.current_chat_id
            st.rerun()
        else:
            st.error(f"Error saving message: {e}")
        return None

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
            if "message_ids" in st.session_state:
                del st.session_state.message_ids
            if "current_chat_id" in st.session_state:
                del st.session_state.current_chat_id
            return False
    except Exception as e:
        # Session is invalid or expired
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.user_id = None
        if "messages" in st.session_state:
            del st.session_state.messages
        if "message_ids" in st.session_state:
            del st.session_state.message_ids
        if "current_chat_id" in st.session_state:
            del st.session_state.current_chat_id
        return False

def show_login():
    """Display login form"""
    
    # Sidebar with tool information
    with st.sidebar:
        st.image("assets/Unidistance_Logo_couleur_RVB.png", width=200)
        st.markdown("### 📚 About This Tool")
        
        with st.expander("🇺🇸 English"):
            st.markdown("""
            **This is a digital learning tool designed for psychology courses.**  
            It supports students in exploring and understanding memory-related concepts from *Memory* by Baddeley et al.

            **Students can choose between two chat modes:**

            - **Socrates**: A guided Socratic dialogue that stimulates thinking and self-discovery through guided questions—without giving direct answers.  
            - **Aristotle**: A direct, explanatory style that delivers direct answers and summaries to support knowledge acquisition.
            
            **Disclaimer:** We do not guarantee the correctness of the chat output.
            """)
        
        with st.expander("🇩🇪 Deutsch"):
            st.markdown("""
            **Dies ist ein digitales Lerntool für psychologische Lehrveranstaltungen.**  
            Es unterstützt Studierende dabei, gedächtnisbezogene Konzepte aus *Memory* von Baddeley et al. zu verstehen.

            **Studierende können zwischen zwei Chat-Modi wählen:**

            - **Sokrates**: Ein geführter sokratischer Dialog, der durch gezielte Fragen zum Denken und zur Selbstentdeckung anregt – ohne direkte Antworten zu geben.  
            - **Aristoteles**: Ein direkter, erklärender Stil, der klare Antworten und Zusammenfassungen liefert, um den Wissenserwerb zu unterstützen.
            
            **Haftungsausschluss:** Wir übernehmen keine Gewähr für die Richtigkeit der Chat-Ausgaben.
            """)
    
    # Main content
    st.title("🔐 Anmeldung erforderlich")
    st.markdown("""
    **Zugang nur für Studierende und Mitarbeitende der Universität**
    
    Bitte melden Sie sich mit Ihrer institutionellen E-Mail-Adresse an:
    
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
                help="Nur E-Mail-Adressen der Universität sind zugelassen",
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
                    st.error("❌ Ungültige E-Mail-Adresse. Bitte verwenden Sie eine Adresse mit @etu.unidistance.ch, @stu.fernuni.ch, @unidistance.ch, oder @fernuni.ch.")
                else:
                    st.error("❌ Bitte füllen Sie alle Felder aus.")
    
    with tab2:
        st.subheader("Neuen Account erstellen")
        with st.form("signup_form"):
            signup_email = st.text_input(
                "E-Mail-Adresse", 
                placeholder="vorname.nachname@unidistance.ch",
                help="Nur E-Mail-Adressen der Universität sind zugelassen",
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
                        st.error("❌ Ungültige E-Mail-Adresse. Bitte verwenden Sie eine Adresse mit @etu.unidistance.ch, @stu.fernuni.ch, @unidistance.ch, oder @fernuni.ch.")
                    elif len(signup_password) < 6:
                        st.error("❌ Passwort muss mindestens 6 Zeichen lang sein.")
                    elif signup_password != confirm_password:
                        st.error("❌ Passwörter stimmen nicht überein.")
                    else:
                        user = sign_up_user(signup_email, signup_password)
                        if user:
                            st.success("✅ Account erfolgreich erstellt! Sie können sich nun anmelden.")
                        else:
                            st.error("❌ Fehler beim Erstellen des Accounts. Möglicherweise existiert die E-Mail bereits.")
                else:
                    st.error("❌ Bitte füllen Sie alle Felder aus.")

def show_mode_selection():
    """Display mode selection interface"""
    # Check session validity at the start
    if not check_session_validity():
        st.error("Ihre Sitzung ist abgelaufen. Sie werden zur Anmeldung weitergeleitet.")
        st.rerun()
        return
    
    # Sidebar with user info
    with st.sidebar:
        st.image("assets/Unidistance_Logo_couleur_RVB.png", width=200)
        st.markdown("### 📚 About This Tool")
        
        with st.expander("🇺🇸 English"):
            st.markdown("""
            **This is a digital learning tool designed for psychology courses.**  
            It supports students in exploring and understanding memory-related concepts from *Memory* by Baddeley et al.

            **Students can choose between two chat modes:**

            - **Socrates**: A guided Socratic dialogue that stimulates thinking and self-discovery through guided questions—without giving direct answers.  
            - **Aristotle**: A direct, explanatory style that delivers direct answers and summaries to support knowledge acquisition.
            
            **Disclaimer:** We do not guarantee the correctness of the chat output.
            """)
        
        with st.expander("🇩🇪 Deutsch"):
            st.markdown("""
            **Dies ist ein digitales Lerntool für psychologische Lehrveranstaltungen.**  
            Es unterstützt Studierende dabei, gedächtnisbezogene Konzepte aus *Memory* von Baddeley et al. zu verstehen.

            **Studierende können zwischen zwei Chat-Modi wählen:**

            - **Sokrates**: Ein geführter sokratischer Dialog, der durch gezielte Fragen zum Denken und zur Selbstentdeckung anregt – ohne direkte Antworten zu geben.  
            - **Aristoteles**: Ein direkter, erklärender Stil, der klare Antworten und Zusammenfassungen liefert, um den Wissenserwerb zu unterstützen.
            
            **Haftungsausschluss:** Wir übernehmen keine Gewähr für die Richtigkeit der Chat-Ausgaben.
            """)
        
        # Login info at bottom of sidebar
        st.divider()
        st.markdown(f"""
        **Angemeldet als:**  
        {st.session_state.user_email}
        """)
        if st.button("Abmelden", type="secondary", use_container_width=True):
            sign_out_user()
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state.user_id = None
            if "messages" in st.session_state:
                del st.session_state.messages
            if "message_ids" in st.session_state:
                del st.session_state.message_ids
            if "current_chat_id" in st.session_state:
                del st.session_state.current_chat_id
            st.rerun()
    
    # Main content - Mode selection
    st.title("🎯 Chat-Modus wählen")
    st.markdown("""
    Wählen Sie den gewünschten Chat-Modus für Ihre neue Unterhaltung:
    """)
    
    # Mode selection cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🤔 Sokrates
        **Sokratischer Dialog**
        
        In diesem Modus stellt der Bot lenkende Fragen, anstatt direkte Antworten zu geben.
        
        ✅ Fördert kritisches Denken  
        ✅ Selbstentdeckung durch Fragen  
        ✅ Vertieftes Verständnis
        """)
        
        if st.button("🤔 Sokrates wählen", type="primary", use_container_width=True):
            # Create new chat with Sokrates mode
            chat_id = create_new_chat(st.session_state.user_id, "Sokrates")
            if chat_id:
                st.session_state.current_chat_id = chat_id
                st.session_state.chat_mode = "Sokrates"
                st.session_state.messages = []
                st.session_state.message_ids = []
                st.rerun()
    
    with col2:
        st.markdown("""
        ### 💬 Aristoteles
        **Direkter Chat**
        
        In diesem Modus gibt der Bot direkte, informative Antworten auf Ihre Fragen zum Buch.
        
        ✅ Klare, direkte Antworten  
        ✅ Informative Erklärungen  
        ✅ Schneller Wissenserwerb
        """)
        
        if st.button("💬 Aristoteles wählen", type="primary", use_container_width=True):
            # Create new chat with Aristoteles mode
            chat_id = create_new_chat(st.session_state.user_id, "Aristoteles")
            if chat_id:
                st.session_state.current_chat_id = chat_id
                st.session_state.chat_mode = "Aristoteles"
                st.session_state.messages = []
                st.session_state.message_ids = []
                st.rerun()

def show_main_app():
    """Display the main chatbot application"""
    # Check session validity at the start of main app
    if not check_session_validity():
        st.error("Ihre Sitzung ist abgelaufen. Sie werden zur Anmeldung weitergeleitet.")
        st.rerun()
        return
    
    # Check if we have a current chat session
    if "current_chat_id" not in st.session_state or st.session_state.current_chat_id is None:
        # No chat session, show mode selection
        show_mode_selection()
        return
    
    # Sidebar for chat controls
    with st.sidebar:
        st.image("assets/Unidistance_Logo_couleur_RVB.png", width=200)
        st.title(f"🎯 {st.session_state.chat_mode}")
        
        # Mode description
        if st.session_state.chat_mode == "Sokrates":
            st.markdown("""
            **🤔 Sokratischer Dialog**
            
            In diesem Modus stellt der Bot lenkende Fragen, um Sie zum Nachdenken anzuregen, anstatt direkte Antworten zu geben.
            """)
        else:
            st.markdown("""
            **💬 Aristoteles-Chat**
            
            In diesem Modus gibt der Bot direkte, informative Antworten auf Ihre Fragen zum Buch.
            """)
        
        st.divider()
        
        # Start new chat button
        if st.button("🆕 Neuen Chat starten", type="secondary", use_container_width=True):
            # Clear current chat session
            st.session_state.current_chat_id = None
            st.session_state.chat_mode = None
            if "messages" in st.session_state:
                del st.session_state.messages
            if "message_ids" in st.session_state:
                del st.session_state.message_ids
            st.rerun()
        
        # Login info at bottom of sidebar
        st.divider()
        st.markdown(f"""
        **Angemeldet als:**  
        {st.session_state.user_email}
        """)
        if st.button("Abmelden", type="secondary", use_container_width=True):
            sign_out_user()
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state.user_id = None
            if "messages" in st.session_state:
                del st.session_state.messages
            if "message_ids" in st.session_state:
                del st.session_state.message_ids
            if "current_chat_id" in st.session_state:
                del st.session_state.current_chat_id
            st.rerun()
    
    # App title
    st.title(f"{st.session_state.chat_mode} Chatbot")

    # Initialize session state for messages
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Initialize session state for message IDs (to track database records)
    if "message_ids" not in st.session_state:
        st.session_state.message_ids = []

    # Initialize processing flag
    if "processing_response" not in st.session_state:
        st.session_state.processing_response = False

    # Instruction - different content based on chat mode
    if st.session_state.chat_mode == "Sokrates":
        with st.expander("ℹ️ So funktioniert's:"):
            st.markdown("""
            Dieser Chatbot führt einen **sokratischen Dialog**, der sich ausschliesslich auf das Buch *Memory* von Baddeley et al. stützt.
            
            - ❌ Er gibt keine direkten Antworten
            - 🧠 Er stellt dir Fragen, um dein Denken anzuregen

            Stelle eine Frage oder nenne ein Thema, um loszulegen!
            """)
    else:  # Aristoteles mode
        with st.expander("ℹ️ So funktioniert's:"):
            st.markdown("""
            Dieser Chatbot gibt dir **direkte Antworten** auf Fragen zum Buch *Memory* von Baddeley et al.
            - ✅ Er liefert präzise Erklärungen und Zusammenfassungen
            - 🧠 Er hilft dir, das Buch besser zu verstehen und dein Wissen zu festigen  
            
            Stelle eine Frage oder nenne ein Thema, um loszulegen!
            """)

    # Display existing messages
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.chat_message("user").markdown(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["content"])
                
                # Add feedback component for assistant messages
                if i < len(st.session_state.message_ids) and st.session_state.message_ids[i]["role"] == "assistant":
                    message_id = st.session_state.message_ids[i]["id"]
                    
                    # Only show feedback if message was successfully saved to database
                    if message_id is not None:
                        def handle_feedback(feedback_data, msg_id=message_id):
                            """Handle feedback submission"""
                            try:
                                if feedback_data:
                                    # Convert thumbs to rating (👍 = 1, 👎 = 0)
                                    rating = 1 if feedback_data["score"] == "👍" else 0
                                    feedback_text = feedback_data.get("text", "").strip() if feedback_data.get("text") else None
                                    
                                    # Save feedback to database
                                    result = save_feedback(msg_id, rating, feedback_text)
                                    if result:
                                        # Don't show success message here as it's already shown in save_feedback
                                        return feedback_data
                                    else:
                                        st.error("Feedback konnte nicht gespeichert werden.")
                                return feedback_data
                            except Exception as e:
                                st.error(f"Fehler beim Verarbeiten des Feedbacks: {e}")
                                return feedback_data
                        
                        # Create feedback component with unique key
                        feedback = streamlit_feedback(
                            feedback_type="thumbs",
                            optional_text_label="[Optional] Bitte geben Sie eine Erklärung an",
                            on_submit=handle_feedback,
                            key=f"feedback_{message_id}_{i}",
                            align="flex-start"
                        )

    # Chat input
    user_input = st.chat_input("Frage etwas über Gedächtnis...")

    # Handle user input
    if user_input and not st.session_state.processing_response:
        # Check session validity before processing the message
        if not check_session_validity():
            st.error("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
            st.rerun()
            return
            
        # Add user message immediately and rerun to display it
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Save user message to database and store the ID
        user_message_id = save_chat_message(st.session_state.current_chat_id, "user", user_input)
        st.session_state.message_ids.append({"role": "user", "id": user_message_id})
        
        # If saving failed due to session expiry, don't continue with API call
        if user_message_id is None:
            return

        # Set processing flag and rerun to show user message + loading indicator
        st.session_state.processing_response = True
        st.rerun()

    # Generate assistant response if we're in processing mode
    if st.session_state.processing_response and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        
        # Compose full conversation with mode-specific system prompt
        if st.session_state.chat_mode == "Sokrates":
            system_prompt = """
            Du bist ein sokratischer Tutor, der sich ausschliesslich auf das Buch „Memory" von Baddeley et al. konzentriert.
            Deine Aufgabe ist es, niemals direkt zu antworten. 
            Stattdessen stellst du aufschlussreiche, lenkende Fragen, die dem Lernenden helfen, über das Thema nachzudenken und selber Antworten zu finden.
            Weigere dich, Fragen zu beantworten oder Gespräche fortzusetzen, die sich nicht mit dem Thema "Lernen und Gedächtnis" befassen.
            Verwende stets sokratischen Dialog. 
            Kommuniziere in der Sprache des Lernenden."""
        else:  # Aristoteles mode
            system_prompt = """
            Du bist ein Tutor, der ausschliesslich Fragen zum Buch 'Memory' von Baddeley et al. beantwortet. 
            Deine Aufgabe ist es, korrekte, präzise, kurze und informative Antworten zu geben.
            Weigere dich, Fragen zu beantworten oder Gespräche fortzusetzen, die sich nicht mit dem Thema "Lernen und Gedächtnis" befassen.
            Kommuniziere in der Sprache des Lernenden."""
        
        messages = [{"role": "system", "content": system_prompt}]
        for msg in st.session_state.messages:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Call OpenAI API with streaming
        try:
            # Initialize streaming response
            st.session_state.streaming_response = True
            st.session_state.current_response = ""
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.2,
                stream=True  # Enable streaming
            )
            
            # Process streaming response in the same container as the loading indicator
            # The loading indicator will be automatically replaced by this content
            full_response = ""
            
            # Create a single response container that replaces the loading spinner
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        chunk_content = chunk.choices[0].delta.content
                        full_response += chunk_content
                        
                        # Update the display in real-time with typing cursor
                        response_placeholder.markdown(full_response + "▋")
                        
                        # Small delay to make streaming visible
                        import time
                        time.sleep(0.01)
                
                # Final update without cursor
                response_placeholder.markdown(full_response)
            
            # Add complete assistant response to session state
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # Save assistant message to database and store the ID
            assistant_message_id = save_chat_message(st.session_state.current_chat_id, "assistant", full_response)
            st.session_state.message_ids.append({"role": "assistant", "id": assistant_message_id})
            
            # Clear processing and streaming flags
            st.session_state.processing_response = False
            st.session_state.streaming_response = False
            st.rerun()
            
        except Exception as e:
            st.error(f"API Error: {e}")
            # Clear all flags and remove user message if API call failed
            st.session_state.processing_response = False
            st.session_state.streaming_response = False
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                st.session_state.messages.pop()
                st.session_state.message_ids.pop()
            st.rerun()

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
        if "message_ids" in st.session_state:
            del st.session_state.message_ids
        if "current_chat_id" in st.session_state:
            del st.session_state.current_chat_id

# Show appropriate interface based on authentication
if not st.session_state.authenticated:
    show_login()
else:
    show_main_app()
