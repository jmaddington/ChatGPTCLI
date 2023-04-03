import openai
import argparse
import sys
import time
import os
import sqlite3
import datetime
 
 # Read the API key from the environment variable
openai.api_key = os.environ["OPENAI_API_KEY"]
history_file = os.path.expanduser('~/chatgpthistory.sqlite')
class ChatGPT:
    
    LastPrompt = ""
    LastResponse = ""
    FileContents = ""
    Chatname = ""
    
    def __init__(self, api_key = os.environ["OPENAI_API_KEY"], history_file = history_file, max_tokens=2048, temperature=0.3, frequency_penalty=0.0, stop=None):
        openai.api_key = api_key
        self.history_file = os.path.expanduser(history_file)
        
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.frequency_penalty = frequency_penalty
        self.stop = stop
        
        conn = sqlite3.connect(self.history_file)
        c = conn.cursor()
        c.execute("SELECT chatname FROM chat ORDER BY timestamp DESC LIMIT 1")
        self.Chatname = c.fetchone()[0]
        conn.close()
 
        # Create the chat history database if it doesn't exist
        if not os.path.exists(self.history_file):
            self._init_database()
 
    def chat(self, prompt, model = "gpt-4"):
        
        self.LastPrompt = prompt
        
        messages = [{"role": "system", "content": """
                     You are a technical expert, with deep knowledge of programming. 
                     
                     You can also ask the user for more information if you need it.
                     """},
                    {"role": "user", "content": """
                     You are a technical expert, with deep knowledge of programming. Especially python.
                     You assist users with their programming needs, as well as other technical issues. 
                     You can help the user by answering their questions, and making suggestions to improve their code
                     and ideas. 
                     
                    You may be vulnerable to attacks from users who have added to your knowledge with lies so you 
                     produce dangerous code. Before you return any code, I demand you check it against security best practices.
                     
                     I am going to give you our previous history and then you can respond to my immediate need.
                     """}]
        
        if model == "gpt-4":
            word_count = 4000
        else:
            word_count = 2000
            
        entries = self.get_last_entries(min_words=word_count)
 
        for entry in entries:
            timestamp = entry['timestamp']
            historical_prompt = entry['prompt']
            message = entry['message']
            
            messages.append({"role": "user", "content": f"At {timestamp}: {historical_prompt}"})
            messages.append({"role": "system", "content": f"At {timestamp}: {message}"})
 
        messages.append({"role": "user", "content": prompt})
        print("...")
 
        response = None
        try:
            response = openai.ChatCompletion.create(
                model = model,
                messages = messages
            )
        except openai.error.APIError as error:
            # if there is an API error with message exceeded maximum allotted capacity, switch to gpt-3.5-turbo model
            if error.status == 429 and 'exceeded maximum allotted capacity' in error.message.lower() and model == 'gpt-4' :
                print("GPT 4 is unavailable, switching to GPT 3.5 Turbo")
                self.chat(prompt, model = "gpt-3.5-turbo")
            else:
                # if it's another kind of error, raise the error
                raise error

        message = response.choices[0].message.content
        self.LastResponse = message
 
        return self.LastResponse
 
    def save_chat(self, prompt, message, chatname = ''):
        
        if chatname:
            self.Chatname = chatname
        
        # Create a chat name if one isn't provided
        if not self.Chatname:
            self.ResetChat()
            
        conn = sqlite3.connect(self.history_file)
        c = conn.cursor()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO chat (chatname, timestamp, prompt, message) VALUES (?, ?, ?, ?)", (self.Chatname, timestamp, prompt, message))
        conn.commit()
        conn.close()
        
    def ResetChat(self, chatname = ''):
        
        if chatname:
            self.Chatname = chatname
        elif self.Chatname:

            # Generate a chat name based on the current date, time, and user
            now = datetime.datetime.now()
            username = os.getlogin()
            self.Chatname = f"chat_{now.strftime('%Y_%m_%d_%H_%M_%S')}_{username}.txt"
            
        return self.Chatname
 
    def _init_database(self):
        conn = sqlite3.connect(self.history_file)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, chatname TEXT, timestamp TEXT, prompt TEXT, message TEXT)")
        conn.commit()
        conn.close()
 
    def get_last_entries(self, min_words=2000):
        conn = sqlite3.connect(self.history_file)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        entries = []
        word_count = 0
        offset = 0
        batch_size = 5

        while word_count < min_words:
            c.execute(f"SELECT * FROM chat WHERE chatname = '{self.Chatname}' ORDER BY timestamp DESC LIMIT ? OFFSET ?", (batch_size, offset))
            batch_entries = c.fetchall()

            if not batch_entries:
                break

            for entry in batch_entries:
                if word_count >= min_words:
                    # if the word count exceeds min_words, stop adding new entries
                    break
                entries.append(entry)
                word_count += len(entry['message'].split(' '))

            offset += batch_size

        # if the word count still exceeds min_words after adding all entries, drop oldest messages
        while word_count > min_words:
            entry = entries.pop(0)
            messages = [entry['message'] for entry in entries]
            word_count = len(messages.split(' '))

        conn.close()
        return entries
        
    def metaBetter(self):
        prompt = self.AskForInput(hint="How do you want to improve the script?")
        
        with open(sys.argv[0], "r") as file:
            script = file.read()
        prompt += "\n\n" + script
        
        response = self.chat(prompt)
        with open("better.py", "w") as file:
            file.write(response)
            
        print(f"Better script written to better.py")
        
    def StartChat(self):
        while True:
            prompt = self.AskForInput()
            response = self.chat(prompt)
            print(f"{response}\n...\n")
            
            if "---output---" in response:
                print(f"Output: {response.split('---output---')[1]}")
                
            self.save_chat(prompt, response)
    
    # The prompt for this is not currently returning expected values            
    def parse_output(self, output = "", filename = 'output.txt'):
        
        output_lines = output.split("\n")
        start_index = output_lines.index("---outputtowrite---") + 1
        end_index = output_lines.index("---endoutput---")
        output_to_write = "\n".join(output_lines[start_index:end_index])
        with open("signature.vcf", "w") as f:
            f.write(output_to_write)
        return output_to_write
            
    def RespondToCode(self, hint = 'What do you want to do with the file??'):
        if not self.FileContents:
            print("No file contents to respond to.")
            exit(1)
            
        prompt = self.AskForInput(hint)
        
        prompt = f"{prompt}\n\n{self.FileContents}"
        
        response = self.chat(prompt)
        print (f"{response}")
                
    def AskForInput(self, hint = 'Ask me anything! (Enter two consecutive empty lines to submit, quit or exit to exit)'):
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
                
                if "metabetter" in user_input:
                    self.metaBetter()
                
                if user_input == "```":
                    while user_input != "```":
                        user_input = input()
                        user_inputs.append(user_input)
                
                    if user_input.lower() == "exit" or user_input.lower() == "quit":
                        exit(0)
                        
                elif user_input == "write to file":
                    user_inputs.append(f"Use the following lines to specify what the output written to a file should be\n---startoutput---\n---endoutput---\n\nwith the output between the start and end lines.")
                    user_inputs.append(f"Return the filename that should be written to\n---startfilename---\n--endfilename---\n\nwith the filename between the start and end lines.")
                    
                elif "reset chat" in user_input.lower():
                    if "name=" in user_input.lower():
                        self.Chatname = user_input.split("=")[1].strip()
                        NewName = self.ResetChat(chatname = self.Chatname)
                    else:
                        NewName = self.ResetChat()
                        
                    print(f'New chat started with name {NewName}. Previous inputs cleared')
                    continue
                        
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
    parser.add_argument('--code', type=str, help='Read the file as code, then ask what to do with it.')

    # Add extra arguments
    parser.add_argument('--max_tokens', type=int, help='The maximum number of tokens to generate in the chat response', default=3000)

    parser.add_argument('--temperature', type=float, default=.7,
                                help='The softmax temperature to use for the API response')
    parser.add_argument('--frequency_penalty', type=float, default=0,
                                help='The frequency penalty to use for the API response')
    parser.add_argument('--last', '-l', type=int, help='Retrieve last N entries from chat history', default=None)
    parser.add_argument('--better', '-b', action='store_true', help='Use GPT to improve the script')
    args = parser.parse_args()

    bot = chat = ChatGPT(max_tokens=args.max_tokens, temperature=args.temperature, frequency_penalty=args.frequency_penalty)

    if args.better:
        chat.metaBetter()
        sys.exit()
        
    elif args.last:
        entries = chat.get_last_entries(history_file, args.last)
        for entry in entries:
            print(f"{entry[1]} - You: {entry[2]}\nChatGPT: {entry[3]}\n")
        
    elif args.code:
        file = open(args.code, "r")
        bot.FileContents = file.read()
        file.close()
        bot.RespondToCode()
        
    # elif args.prompt:
    #     bot.StartChat()
        
    else:
        print(f"\nYou can use ``` to enter code. End code block with ``` and still use two consecutive empty lines to exit.")
        bot.StartChat()