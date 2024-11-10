from pathlib import Path
from openai import OpenAI
from subprocess import Popen
import time
import os
import dotenv
dotenv.load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

def generate_and_play_speech(text, filename):
    # Generate the speech file
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",  # You can change to echo, fable, onyx, nova, or shimmer
        input=text
    )
    
    # Save the file
    response.stream_to_file(filename)
    
    # Play using macOS afplay
    Popen(['afplay', filename])

# Example usage in a loop
texts = [
"I am streaming wow this is interesting"
]

if __name__ == "__main__":
    for i, text in enumerate(texts):
        speech_file = f"speech_{i}.mp3"
        generate_and_play_speech(text, speech_file)
        time.sleep(2)  # Wait a bit between messages