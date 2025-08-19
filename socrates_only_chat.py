import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

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
    Dieser Chatbot führt einen **sokratischen Dialog**, der sich ausschliesslich auf das Buch *Memory* von Baddeley, Anderson und Eysenck stützt.
    
    - ❌ Er gibt **keine direkten Antworten**
    - 📚 Er spricht **nicht über Themen ausserhalb des Buches**
    - 🧠 Er stellt dir Fragen, um dein Denken anzuregen

    Stelle eine Frage oder nenne ein Thema, um loszulegen!
    """)

# Chat input
user_input = st.chat_input("Frage/sage etwas über Gedächtnis...")

# Append user input
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Compose full conversation
    messages = [{"role": "system", "content": 
        """You are a Socratic tutor focused exclusively on the book 'Memory' by Baddeley et al. (4th edition).
        
        Your job is to **never answer directly**. Instead, you ask insightful, guiding questions to help the student reflect and find answers based on the book.
        
        Be strict: refuse to answer or continue conversations outside of the book's content.
        Always use Socratic dialogue.
        """}]

    for msg in st.session_state.messages:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Call OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
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
