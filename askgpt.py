import openai
import argparse
import sys
import time
import os
import sqlite3
from datetime import datetime


# Read the API key from the environment variable
openai.api_key = os.environ["OPENAI_API_KEY"]
history_file = os.path.expanduser('~/chatgpthistory.sqlite')

def chat(prompt):
    """
    runs the user chat with chatGPT. It first gets the last several entries from the database, then uses them as the initial messages for the chat. It then appends the user's prompt and the chatGPT response to the database.
    """
    
    messages = [{"role": "system", "content": "You are a helpful assistant to a user. The user is trying to get a task done. You can help the user by answering their questions. You can also ask the user for more information if you need it."},
                {"role": "user", "content": "I am going to give you our previous history and then you can respond to my immedieate need."}]
    
    entries = get_last_entries()

    for entry in entries:
        timestamp = entry['timestamp']
        historical_prompt = entry['prompt']
        message = entry['message']
        # print(f"Timestamp: {timestamp}")
        # print(f"Prompt: {historical_prompt}")
        # print(f"Message: {message}")
        # print()

        messages.append({"role": "user", "content": historical_prompt})
        messages.append({"role": "system", "content": message})
        
    messages.append({"role": "user", "content": prompt})
    # print(messages)
    print("...")
    # message = {"role": "user", "content": prompt}

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = messages
    )

    message = response.choices[0].message.content

    return message

def save_chat(session, prompt, message):
    conn = sqlite3.connect(session)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO chat (timestamp, prompt, message) VALUES (?, ?, ?)", (timestamp, prompt, message))
    conn.commit()
    conn.close()

def init_database(session):
    conn = sqlite3.connect(session)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, prompt TEXT, message TEXT)")
    conn.commit()
    conn.close()
    
def get_last_entries(session=history_file, n=4):
    conn = sqlite3.connect(session)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM chat ORDER BY timestamp DESC LIMIT ?", (n,))
    entries = c.fetchall()
    conn.close()
    return entries

def metaBetter():
    prompt = input("How can we make this script better?\n")
    with open(sys.argv[0], "r") as file:
        script = file.read()
    script += "\n\n" + prompt
    response = chat(script)
    with open("better.py", "w") as file:
        file.write(response)
    print(f"Better script written to better.py")
    file.close()


if __name__ == '__main__':
    # Create the chat history database if it doesn't exist
    history_file = os.path.expanduser('~/chatgpthistory.sqlite')
    if not os.path.exists(history_file):
        init_database(history_file)

    parser = argparse.ArgumentParser(description='Chat with GPT')
    parser.add_argument('--prompt', '-p', type=str, help='Initial prompt for chat', default=None)
    parser.add_argument('--last', '-l', type=int, help='Retrieve last N entries from chat history', default=None)
    parser.add_argument('--better', '-b', action='store_true', help='Use GPT to improve the script')

    args = parser.parse_args()

    if args.last:
        entries = get_last_entries(history_file, args.last)
        for entry in entries:
            print(f"{entry[1]} - You: {entry[2]}\nChatGPT: {entry[3]}\n")
    elif args.prompt:
        prompt = args.prompt
        response = chat(prompt)
        while response is None:
            time.sleep(5)
            response = chat(prompt)
        print(response)
        save_chat(history_file, prompt, response)
    else:
        while True:
            prompt = sys.stdin.read()
            if prompt.strip().lower() == 'q':
                sys.exit()
            response = chat(prompt)
            while response is None:
                print("ChatGPT: I'm sorry, I encountered an error. Could you please rephrase your input?")
                error_prompt = sys.stdin.read()
                response = chat(prompt + error_prompt)
            print("ChatGPT: " + response)
            save_chat(history_file, prompt, response)