import multiprocessing
import subprocess

def run_script1():
    subprocess.run(['python', 'talk.py'])

def run_script2():
    subprocess.run(['python', 'loop.py'])

def run_parallel_scripts():
    p1 = multiprocessing.Process(target=run_script1)
    p2 = multiprocessing.Process(target=run_script2)
    
    p1.start()
    p2.start()
    
    p1.join()
    p2.join()


import subprocess
import sys

def run_apple_script(script):
    try:
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, 
                              text=True)
        if result.stderr:
            if "Not authorized" in result.stderr:
                print("\nError: Permission Denied!")
                print("\nPlease grant permissions:")
                print("1. Open System Preferences")
                print("2. Go to Security & Privacy > Privacy")
                print("3. Click on 'Automation' in the left sidebar")
                print("4. Find your terminal app or IDE")
                print("5. Check the box next to 'System Events'")
                print("6. Run this script again")
                sys.exit(1)
            else:
                print(f"Error: {result.stderr}")
        return result.stdout
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

def hide_all_except_brave_textedit():
    script = '''
    tell application "System Events"
        set visible of every process whose name is not "Brave Browser" and name is not "TextEdit" to false
    end tell
    '''
    run_apple_script(script)

def show_all_windows():
    script = '''
    tell application "System Events"
        set visible of every process to true
    end tell
    '''
    run_apple_script(script)

def check_app_names():
    script = '''
    tell application "System Events"
        get name of every process where background only is false
    end tell
    '''
    result = run_apple_script(script)
    print("\nRunning applications:")
    print(result)

if __name__ == "__main__":
    run_parallel_scripts()

if __name__ == "__main__":
    print("Window Manager Script")
    print("--------------------")
    
    # Uncomment to check app names
    # check_app_names()
    
    print("\nAttempting to hide windows...")
    hide_all_except_brave_textedit()
    
    print("\nDone! Only Brave Browser and TextEdit should be visible.")
    print("To show all windows again, uncomment the show_all_windows() line in the script.")
    