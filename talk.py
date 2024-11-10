from pathlib import Path
from openai import OpenAI
from subprocess import Popen
import time
import os
import dotenv

dotenv.load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# Create a directory for speech files if it doesn't exist
SPEECH_DIR = Path("speech_files")
SPEECH_DIR.mkdir(exist_ok=True)

def generate_and_play_speech(text):
    # Generate unique filename using timestamp
    filename = SPEECH_DIR / f"speech.mp3"
    
    # Generate the speech file
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )
    
    # Save the file
    response.stream_to_file(filename)
    # Play using macOS afplay
    Popen(['afplay', str(filename)])

def remove_speech_file():
    filename = SPEECH_DIR / "speech.mp3"
    if filename.exists():
        filename.unlink()

def watch_for_text_changes(filename="input.txt"):
    """Watch for changes in a text file and generate speech when it changes"""
    last_modified = None
    last_content = ""
    
    while True:
        try:
            # Get the current modification time of the file
            current_modified = os.path.getmtime(filename)
            
            # If file has been modified
            if last_modified != current_modified:
                with open(filename, 'r') as f:
                    content = f.read().strip()
                
                # Only generate speech if content has changed
                if content and content != last_content:
                    generate_and_play_speech(content)
                    last_content = content
                
                last_modified = current_modified
            
            time.sleep(1)  # Check every second
            
        except FileNotFoundError:
            print(f"Waiting for {filename} to be created...")
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":

    watch_for_text_changes()