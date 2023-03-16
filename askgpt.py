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
    
    LastPrompt = ""
    LastResponse = ""
    FileContents = ""
    
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
        
        self.LastPrompt = prompt
        
        messages = [{"role": "system", "content": "You are a helpful assistant to a user. The user is trying to get a task done. You can help the user by answering their questions. You can also ask the user for more information if you need it."},
                    {"role": "user", "content": "I am going to give you our previous history and then you can respond to my immedieate need."}]
        entries = self.get_last_entries()
 
        for entry in entries:
            timestamp = entry['timestamp']
            historical_prompt = entry['prompt']
            message = entry['message']
            
            messages.append({"role": "user", "content": f"At {timestamp}: {historical_prompt}"})
            messages.append({"role": "system", "content": f"At {timestamp}: {message}"})
 
        messages.append({"role": "user", "content": prompt})
        print("...")
 
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            # model = 'text-davinci-003',
            messages = messages
        )

        message = response.choices[0].message.content
        self.LastResponse = message
 
        return self.LastResponse
 
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
 
    def get_last_entries(self, n=10):
        conn = sqlite3.connect(self.history_file)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM chat ORDER BY timestamp DESC LIMIT ?", (n,))
        entries = c.fetchall()
        conn.close()
        return entries
        
    def StartChat(self):
        while True:
            prompt = self.AskForInput()
            response = self.chat(prompt)
            print(f"{response}\n...\n")
            
                
    def AskForInput(self, hint = 'Ask me anything! (Enter two consecutive empty lines to exit)'):
        """
        Ask the user for input until two blank lines are entered.
        
        :return: The user input as a single string
        """
        while True:
            # Initialize an empty list to hold the user inputs
            print(hint)
            user_inputs = []
            
            # Keep accepting input until two consecutive empty lines are entered
            while len(user_inputs) < 2 or user_inputs[-2:] != ["", ""]:
                user_input = input()
                
                if user_input == "```":
                    while user_input != "```":
                        user_input = input()
                        user_inputs.append(user_input)
                
                    if user_input == "exit" or user_input == "quit":
                        exit(0)
                        
                elif user_input == "exit" or user_input == "quit":
                    exit(0)
                    
                user_inputs.append(user_input)
                
            # Remove the two consecutive empty lines from the user inputs
            user_inputs = user_inputs[:-2]
            
            # Combine the individual lines into a single string
            prompt = "\n".join(user_inputs)
            
            if not prompt.strip():
                print("You didn't enter a prompt. Please try again.")
            else:
                return prompt
            
if __name__ == '__main__':

    # Set up parser
    parser = argparse.ArgumentParser(description='Interact with the OpenAI GPT-3 API')
    # parser.add_argument('-p', '--prompt', type=str, help='The prompt to provide to the API')
    parser.add_argument('-s', '--stop', type=str, default=None, help='The stop sequence for the API to use')

    # Add extra arguments
    parser.add_argument('--max_tokens', type=int, help='The maximum number of tokens to generate in the chat response', default=3000)
    parser.add_argument('--temperature', type=float, default=.7,
                                help='The softmax temperature to use for the API response')
    parser.add_argument('--frequency_penalty', type=float, default=0,
                                help='The frequency penalty to use for the API response')
    parser.add_argument('--last', '-l', type=int, help='Retrieve last N entries from chat history', default=None)
    args = parser.parse_args()

    bot = chat = ChatGPT(max_tokens=args.max_tokens, temperature=args.temperature, frequency_penalty=args.frequency_penalty)
        
    print(f"\nYou can use ``` to enter code. End code block with ``` and still use two consecutive empty lines to exit.")
    bot.StartChat()