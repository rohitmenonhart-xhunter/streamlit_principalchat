import csv
import pyaudio
import wave
import io
from gradio_client import Client
from pyht import Client as PlayHTClient, TTSOptions, Format

# Initialize Gradio Client
client = Client("osanseviero/mistral-super-fast")

# Initialize PlayHT API with your credentials
playht_client = PlayHTClient("o2JcMMMTzvZqOlpI7c2mIEJrLx13", "d697d4a4c4654baca062b5553aac0980")

# Configure your stream options
options = TTSOptions(
    voice="s3://voice-cloning-zero-shot/f8ee5994-a3d0-4a54-a0a1-88f3a7edea21/original/manifest.json",
    sample_rate=44100,
    format=Format.FORMAT_WAV,
    speed=1,
)

# Initialize PyAudio
p = pyaudio.PyAudio()

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
You are the principal of a renowned college in Chennai. Your name is Dr. S. Ramesh. You are known for your strict discipline, yet you are fair and approachable. Answer all the questions as if you are Dr. S. Ramesh, the principal of the college. Provide detailed and thoughtful responses. Try to identify the user's role and any issues they might have.
"""

# Initialize chat history with the role-play context
chat_history = role_play_context

# CSV file setup
csv_file = 'college_complaints.csv'
csv_headers = ['Role', 'Issue', 'Effect', 'Actions Taken', 'Desired Outcome']

# Initialize CSV file
with open(csv_file, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(csv_headers)


def get_response(user_prompt):
    global chat_history
    # Append the user prompt to the chat history
    chat_history += f"\n\nUser: {user_prompt}"

    # Find relevant knowledge base entries
    knowledge_entries = []
    for key, value in knowledge_base.items():
        if key.lower() in user_prompt.lower():
            knowledge_entries.append(value)

    # Combine the chat history and knowledge base for the model's prompt
    knowledge_text = "\n\n".join(knowledge_entries)
    combined_prompt = f"{chat_history}\n\n{knowledge_text}\n\nPrincipal Dr. S. Ramesh:"

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
    chat_history += f"\n\nPrincipal Dr. S. Ramesh: {response}"

    # Read response aloud
    read_aloud(response)

    return response


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


def save_to_csv(role, issue_details):
    with open(csv_file, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([role] + issue_details)


def read_aloud(text):
    # Collect all audio data first
    audio_data = b''.join(playht_client.tts(text=text, voice_engine="PlayHT2.0-turbo", options=options))

    # Create a wave object
    wave_obj = wave.open(io.BytesIO(audio_data), 'rb')

    # Set up the audio stream
    stream = p.open(format=p.get_format_from_width(wave_obj.getsampwidth()),
                    channels=wave_obj.getnchannels(),
                    rate=wave_obj.getframerate(),
                    output=True)

    # Read data
    chunk_size = 1024
    data = wave_obj.readframes(chunk_size)

    # Play stream
    while data:
        stream.write(data)
        data = wave_obj.readframes(chunk_size)

    # Clean up
    stream.stop_stream()
    stream.close()


# Main loop to prompt for user input and handle complaints
while True:
    user_prompt = input("You: ")
    if user_prompt.lower() in ["exit", "quit"]:
        break

    response = get_response(user_prompt)
    print(f"Principal Dr. S. Ramesh: {response}")

    # Check if there's an issue mentioned
    if detect_issues(user_prompt):
        role = detect_role(chat_history)
        print("It seems you've mentioned an issue. Let me gather more details.")

        # Gather more details
        issue_details = []
        for question in [
            "How has this issue affected your experience?",
            "Have you taken any steps to address this issue on your own? If not, explain the issue in detail.",
            "What outcome would you like to see from addressing this issue?"]:
            print(f"Principal Dr. S. Ramesh: {question}")
            user_response = input("You: ")
            issue_details.append(user_response)
            get_response(user_response)

        save_to_csv(role, issue_details)
        print("Your responses have been recorded. Thank you!")