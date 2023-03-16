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
class ChatGPT:
    
    def __init__(self, api_key = os.environ["OPENAI_API_KEY"], history_file = history_file, max_tokens=2048, temperature=0.9, frequency_penalty=0.0, stop=None):
        openai.api_key = api_key
        self.history_file = os.path.expanduser(history_file)
        
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.frequency_penalty = frequency_penalty
        self.stop = stop

 
        # Create the chat history database if it doesn't exist
        if not os.path.exists(self.history_file):
            self._init_database()
 
    def chat(self, prompt):
        messages = [{"role": "system", "content": "You are a helpful assistant to a user. The user is trying to get a task done. You can help the user by answering their questions. You can also ask the user for more information if you need it."},
                    {"role": "user", "content": "I am going to give you our previous history and then you can respond to my immedieate need."}]
        entries = self.get_last_entries()
 
        for entry in entries:
            timestamp = entry['timestamp']
            historical_prompt = entry['prompt']
            message = entry['message']
            
            messages.append({"role": "user", "content": historical_prompt})
            messages.append({"role": "system", "content": message})
 
        messages.append({"role": "user", "content": prompt})
        print("...")
 
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            # model = 'text-davinci-003',
            messages = messages
        )

        message = response.choices[0].message.content
 
        return message
 
    def save_chat(self, prompt, message):
        conn = sqlite3.connect(self.history_file)
        c = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO chat (timestamp, prompt, message) VALUES (?, ?, ?)", (timestamp, prompt, message))
        conn.commit()
        conn.close()
 
    def _init_database(self):
        conn = sqlite3.connect(self.history_file)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, prompt TEXT, message TEXT)")
        conn.commit()
        conn.close()
 
    def get_last_entries(self, n=4):
        conn = sqlite3.connect(self.history_file)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM chat ORDER BY timestamp DESC LIMIT ?", (n,))
        entries = c.fetchall()
        conn.close()
        return entries
        
    def metaBetter(self):
        prompt = input("How can we make this script better?\n")
        with open(sys.argv[0], "r") as file:
            script = file.read()
        script += "\n\n" + prompt
        response = self.chat(script)
        with open("better.py", "w") as file:
            file.write(response)
        print(f"Better script written to better.py")


if __name__ == '__main__':

    # Set up parser
    parser = argparse.ArgumentParser(description='Interact with the OpenAI GPT-3 API')
    parser.add_argument('-p', '--prompt', type=str, help='The prompt to provide to the API')
    parser.add_argument('-s', '--stop', type=str, default=None, help='The stop sequence for the API to use')

    # Add extra arguments
    parser.add_argument('--max_tokens', type=int, help='The maximum number of tokens to generate in the chat response', default=2048)

    parser.add_argument('--temperature', type=float, default=.7,
                                help='The softmax temperature to use for the API response')
    parser.add_argument('--frequency_penalty', type=float, default=0,
                                help='The frequency penalty to use for the API response')
    parser.add_argument('--last', '-l', type=int, help='Retrieve last N entries from chat history', default=None)
    parser.add_argument('--better', '-b', action='store_true', help='Use GPT to improve the script')
    args = parser.parse_args()

    chat = ChatGPT(max_tokens=args.max_tokens, temperature=args.temperature, frequency_penalty=args.frequency_penalty)

    if args.better:
        chat.metaBetter()
        sys.exit()
    elif args.last:
        entries = chat.get_last_entries(history_file, args.last)
        for entry in entries:
            print(f"{entry[1]} - You: {entry[2]}\nChatGPT: {entry[3]}\n")
    elif args.prompt:
        prompt = args.prompt
        response = chat.chat(prompt)
        while response is None:
            time.sleep(5)
            response = chat.chat(prompt)
        print(f"{response}\n..")
        chat.save_chat(history_file, prompt, response)
    else:
        while True:
            prompt = sys.stdin.read()
            if prompt.strip().lower() == 'q':
                sys.exit()
            response = chat.chat(prompt)
            while response is None:
                print("ChatGPT: I'm sorry, I encountered an error. Could you please rephrase your input?")
                error_prompt = sys.stdin.read()
                response = chat(prompt + error_prompt)
            print("ChatGPT: " + response)
            chat.save_chat(prompt, response)