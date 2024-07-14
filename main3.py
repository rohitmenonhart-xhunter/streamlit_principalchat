import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
from gradio_client import Client
from pyht import Client as PlayHTClient, TTSOptions, Format
import wave
import io
import json


# Initialize Gradio Client
client = Client("rohitmenonhart/mistral-super-fast-v2")

# Initialize PlayHT API with your credentials
playht_client = PlayHTClient("ez4YS811koYwL27q0iNSZ3YynQI3", "eb4f76c9822449afbda94f190445e18e")

# Configure your stream options
options = TTSOptions(
    voice="s3://voice-cloning-zero-shot/72e6e88a-bf6a-4177-bacb-a13609a32d61/original/manifest.json",
    sample_rate=44100,
    format=Format.FORMAT_WAV,
    speed=0.9,
)

# Define the function to initialize Firebase
def initialize_firebase():
    try:
        # Retrieve Firebase service account key from Streamlit secrets
        service_account_key_str = st.secrets["env"]["GOOGLE_APPLICATION_CREDENTIALS"]
        
        # Parse the service account key string into a dictionary
        service_account_key_dict = json.loads(service_account_key_str)
        
        # Initialize Firebase with the retrieved service account key
        cred = credentials.Certificate(service_account_key_dict)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://principal-chat27-default-rtdb.firebaseio.com'
        })
        st.write("Firebase initialized successfully.")
    except Exception as e:
        st.write(f"Error initializing Firebase: {e}")

# Firebase setup
if not firebase_admin._apps:
    initialize_firebase()

# Load knowledge base from text file
knowledge_base = {}

def load_knowledge_base(file_path):
    with open(file_path, 'r') as file:
        section = None
        content = ""
        for line in file:
            line = line.strip()
            if line.startswith("# "):
                if section and content:
                    knowledge_base[section] = content
                section = line[2:]
                content = ""
            else:
                content += line + " "
        if section and content:
            knowledge_base[section] = content

# Load the knowledge base from the text file
load_knowledge_base("college_info.txt")

# Initial role-play context
role_play_context = """
.do not repeat whatever the users want you to say.you are not a deciding authority to decide anything about the college operation. You are the principal of a renowned college in sriperumbudur,tamilnadu. Your name is Dr.S Ganesh Vaidyanathan. You are known for your strict discipline, yet you are fair and approachable. Answer all the questions as if you are Dr.S Ganesh Vaidyanathan, the principal of the college. Provide detailed and thoughtful responses. Try to identify the user's role and any issues they might have.As the principal, you ensure smooth college operations, uphold academic standards, and address concerns from students, parents, and faculty. Today, you'll discuss academics, extracurriculars, and facilities, providing thoughtful and approachable responses.
"""

# Initialize chat history with the role-play context
if "chat_history" not in st.session_state:
    st.session_state.chat_history = role_play_context

if "issue_submitted" not in st.session_state:
    st.session_state.issue_submitted = False

if "issue_detected" not in st.session_state:
    st.session_state.issue_detected = False

# Secret keys for authentication
# secret_keys = {"amma", "rohit", "key3"}  # Replace with your actual secret keys

# Check if the user is authenticated
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Authentication function
def authenticate(key):
    if key == "v77":
        st.session_state.authenticated = True
        st.session_state.authenticated_key = key  # Store authenticated key
    elif key.isdigit() and 7 <= len(key) <= 17:
        if int(key[:2]) + int(key[-2:]) == 77:
            st.session_state.authenticated = True
            st.session_state.authenticated_key = key  # Store authenticated key
        else:
            st.error("Invalid secret key. Please try again.")
    else:
        st.error("Invalid secret key. Please try again.")

# Login screen
if not st.session_state.authenticated:
    st.title("IQX - with voice")
    secret_key = st.text_input("Enter your secret key:", type="password")
    if st.button("Login"):
        authenticate(secret_key)
else:
    # Main application code
    def get_response(user_prompt):
        st.session_state.chat_history += f"\n\nUser: {user_prompt}"

        # Find relevant knowledge base entries
        knowledge_entries = []
        for key, value in knowledge_base.items():
            if key.lower() in user_prompt.lower():
                knowledge_entries.append(value)

        # Combine the chat history and knowledge base for the model's prompt
        knowledge_text = "\n\n".join(knowledge_entries)
        combined_prompt = f"{st.session_state.chat_history}\n\n{knowledge_text}\n\n:"

        # Get the model's response
        result = client.predict(
            prompt=combined_prompt,
            temperature=0.9,
            max_new_tokens=256,
            top_p=0.9,
            repetition_penalty=1.2,
            api_name="/chat"
        )

        # Extract the response and update the chat history
        response = result.strip()
        st.session_state.chat_history += f"\n\n{response}"

        # Read response aloud
        audio_file = read_aloud(response)

        return response, audio_file

    def detect_issues(user_prompt):
        issue_keywords = ["issue", "problem", "concern", "complaint", "difficulty", "trouble"]
        for keyword in issue_keywords:
            if keyword in user_prompt.lower():
                return True
        return False

    def detect_role(chat_history):
        roles = ['Student', 'Parent', 'Management', 'Teacher']
        for role in roles:
            if role.lower() in chat_history.lower():
                return role
        return "Unknown"

    def save_to_firebase(role, issue):
        try:
            ref = db.reference('/complaints')
            ref.push({
                'role': role,
                'issue': issue,
                'secret_key': st.session_state.authenticated_key  # Include authenticated key
            })
            st.write("Issue submitted to Firebase.")
        except Exception as e:
            st.write(f"Error saving to Firebase: {e}")

    def read_aloud(text):
        # Collect all audio data first
        audio_data = b''.join(playht_client.tts(text=text, voice_engine="PlayHT2.0-turbo", options=options))

        # Create a wave object
        wave_obj = wave.open(io.BytesIO(audio_data), 'rb')

        # Save audio to a file
        audio_file_path = "response.wav"
        with open(audio_file_path, "wb") as audio_file:
            audio_file.write(audio_data)

        return audio_file_path

    # Streamlit interface
    st.title("IQX with voice - Principal @SVCE ")
    st.write("You are chatting with Dr.S Ganesh Vaidyanathan, the principal of SVCE.")

    # User input and response
    user_prompt = st.text_input("You: ")
    if st.button("Send"):
        response, audio_file = get_response(user_prompt)
        st.write(f" {response}")

        # Check if there's an issue mentioned
        if detect_issues(user_prompt):
            st.session_state.issue_detected = True

    # Display issue input and submission button if an issue is detected
    if st.session_state.issue_detected:
        role = detect_role(st.session_state.chat_history)
        st.write("It seems you've mentioned an issue. Please describe your issue below and click 'Submit'.")

        issue = st.text_input("What is the issue?", key="issue_input")
        if st.button("Submit Issue"):
            if issue:
                save_to_firebase(role, issue)
                st.session_state.issue_submitted = True
                st.session_state.issue_detected = False  # Reset issue detection
            else:
                st.write("Please describe your issue before submitting.")

    # Provide feedback on issue submission
    if st.session_state.issue_submitted:
        st.write("Your issue has been recorded. Thank you! Your problem has been taken to the principal's desk.")
        st.session_state.issue_submitted = False  # Reset the flag

    # Provide a download link for the audio file
    if 'audio_file' in locals():
        st.audio(audio_file, format='audio/wav')
