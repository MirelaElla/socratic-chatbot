import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
from st_supabase_connection import SupabaseConnection, execute_query

# Initialize connection.
conn = st.connection("supabase", type=SupabaseConnection)

# Perform query.
rows = execute_query(conn.table("mytable").select("*"), ttl="10m")
# the query result is cached for no longer than 10 minutes. You can also set ttl=0 to disable caching.

# Print results.
for row in rows.data:
    st.write(f"{row['name']} has a :{row['pet']}:")

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# App title
st.image("assets/Unidistance_Logo_couleur_RVB.png", width=200)  # Display logo
st.markdown("""
*This is a digital teaching and learning tool designed for psychology courses. It helps students explore and understand memory-related concepts and relationships through guided Socratic dialogue.*
""")

st.set_page_config(page_title="Chatbot Memory")
st.title("💬 Chatbot zum Buch 'Memory'")

# Initialize session state
if "messages" not in st.session_state:
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
    st.session_state.messages.append({"role": "user", "content": user_input})

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
    except Exception as e:
        st.error(f"API Error: {e}")

# Display messages
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").markdown(msg["content"])
    else:
        st.chat_message("assistant").markdown(msg["content"])
