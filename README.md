# socratic-chatbot
This is an AI chatbot that uses Socratic dialogue to help students understand the key concepts of the book "Memory" by Baddeley, Anderson und Eysenck.

**Experience the chatbot in action:**  
[Launch the Socratic Chatbot live!](https://socratic-chat.streamlit.app/)

### Example:
![Demo](assets/example.png)

## Features
- **Two Chat Modes:**
  - **Sokrates**: Socratic dialogue with guiding questions to encourage self-discovery
  - **Aristoteles**: Direct, informative answers to your questions
- **User Authentication**: Secure login with institutional email addresses (@unidistance.ch, @fernuni.ch)
- **Chat History Storage**: Conversations are saved to database for analytics and feedback purposes
- **Fresh Start**: Each session begins with a clean chat interface (no previous conversation history shown)
- **Feedback System**: Rate assistant responses with thumbs up/down and optional text feedback
- **Session Management**: Automatic session expiry handling for security

## Getting started
* Use python version 3.13.2 (check current version with `python --version`)
* You need an OpenAI API key saved in the ".env" file (OPENAI_API_KEY = "your-key-comes-here"). The .env file is git-ignored.
* Set up Supabase project with authentication and database (see database_setup.sql)
* Create environment in cmd terminal (if not done yet): `python -m venv venv` (`py -3.13 -m venv venv`)
* Activate environment (on Windows): `venv\Scripts\activate`
* To install all required packages run `pip install -r requirements.txt`
--> if access denied due to managed laptops from work enter: `python -m pip install -r requirements.txt`
* (To save the current packages: `pip freeze > requirements.txt`)
* Then run the command in cmd terminal `streamlit run app.py` (or `python -m streamlit run app.py`) to run the app on localhost.

## Database Setup
Run the SQL commands in the following order in your Supabase SQL editor:

1. **`database_setup.sql`**: Initial database schema setup
   - `user_profiles`: Links to auth.users with user roles (admin, student, tester)
   - `chats`: Tracks individual chat sessions with mode selection (Sokrates/Aristoteles)
   - `chat_messages`: Stores individual messages within chat sessions
   - Includes feedback columns: `feedback_rating` (0/1 for thumbs down/up) and `feedback_text`

2. **`database_setup_RLS.sql`**: Security enhancements for multi-user sessions (improved session handling)
   - Adds Row Level Security (RLS) policies to isolate user data
   - Creates database trigger to automatically set `user_id` from JWT authentication
   - Prevents cross-user data contamination in concurrent sessions
   - (before this users could not chat concurrently, 04 Oct. 2025)

For e-mail verification, just enable the "Confirm email" option in Supabase Authentication settings (under SignIn/Providers). Currently, it is disabled to allow easy testing.


## Models used
* OpenAI's `gpt-4.1`

# To Do
- [x] user auth
- [x] user history logging  
- [x] User feedback system
- [x] Streaming answers
- [x] Analytics dashboard for feedback data (adjust to new DB structure, review SQL syntax)
- [x] Improve system prompt for socrates chat to be more helpful (less fixed on the book)
- [x] Registration issue: Outlook puts the confirmation email into quarantine. --> remove verification step
- [x] Handle multiple concurrent users
- [x] Add pagination for long DB queries (analytics_dashboard.py & analytics_function.sql)
- [ ] Test email verification step on Fernuni email (supabase email has been whitelisted by Fernuni)
- [ ] refactor app code for easier maintenance
