# socratic-chatbot
This is an AI chatbot that uses Socratic dialogue to help students understand the key concepts of the book "Memory" by Baddeley, Anderson und Eysenck.

![Demo](assets/example.png)

## Getting started
* You need an OpenAI API key saved in the ".env" file (OPENAI_API_KEY = "your-key-comes-here"). The .env file is git-ignored.
* Create environment in cmd terminal (if not done yet): `python -m venv venv`
* Activate environment (on Windows): `venv\Scripts\activate`
* To install all required packages run `pip install -r requirements.txt`
* (To save the current packages: `pip freeze > requirements.txt`)
* Then run the command in cmd terminal `streamlit run app.py` to run the app on localhost. You can ask questions about the book "Memory" (What is the levels of processing framework?). The chatbot asks leading questions (à la Socrates) to help you find the answer yourself.

## Models used
* OpenAI's `gpt-4`

# To Do
[ ] Streaming answers
[ ] Add a retry loop that checks if GPT drifted from the Socratic tone or topic. --> not necessary, it already stays on topic.
