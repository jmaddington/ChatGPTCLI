import openai
import argparse
import sys
import time
import os
import sqlite3
import datetime
from colorama import Fore, Style, init
from halo import Halo
import requests
from bs4 import BeautifulSoup
 
 # Read the API key from the environment variable
openai.api_key = os.environ["OPENAI_API_KEY"]
history_file = os.path.expanduser('~/chatgpthistory.sqlite')
class ChatGPT:
    
    LastPrompt = ""
    LastResponse = ""
    FileContents = ""
    Chatname = ""
    Model = "gpt-4"
    BingKey = ""
    FactCheck = False
    NumFactchecks = 1
    DEBUG = False 
    PromptColor = Fore.WHITE
    GPTColor = Fore.GREEN
    DebugColor = Fore.YELLOW
    ErrorColor = Fore.RED
    
    def __init__(self, api_key = os.environ["OPENAI_API_KEY"], history_file = history_file, max_tokens=2048, temperature=0.3, frequency_penalty=0.0, stop=None):
        openai.api_key = api_key
        self.history_file = os.path.expanduser(history_file)
        
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.frequency_penalty = frequency_penalty
        self.stop = stop
        
        self.BingKey = os.environ["BING_SEARCH_API_KEY"]

        
        conn = sqlite3.connect(self.history_file)
        c = conn.cursor()
        c.execute("SELECT chatname FROM chat ORDER BY timestamp DESC LIMIT 1")
        self.Chatname = c.fetchone()[0]
        conn.close()
 
        # Create the chat history database if it doesn't exist
        if not os.path.exists(self.history_file):
            self._init_database()
            
        self.printMessage("Welcome to ChatGPT!", message_from="gpt")
        self.printMessage(f"This version does not have extensive error checking. This will be updated in a future version. \n", message_from="gpt")

    def printMessage (self, message, message_from = "prompt"):
        '''
        Print a message to the console, with a color based on who the message is from.
        
        Falls back to default color if the colorama module is not available.
        '''
        if message_from == "prompt":
            color = self.PromptColor
            
        if message_from == "gpt":
            color = self.GPTColor
            
        if message_from == "debug":
            color = self.DebugColor
            
        if message_from == "error":
            color = self.DebugColor
            
        try:    
            print(f"{color}{message}\n{Style.RESET_ALL}")
        except:
            print(f"{message}\n")
        
    def chat(self, prompt, model = "", check_bing = False, attempts = 0, max_retries = 3, backoff_time = 15):
        """
        Main function to chat with GPT. You may need to edit the lines under the message to customize how you want ChatGPT
        to respond. The default is to tell ChatGPT it is a Python expert. Obviously, you can change that to whatever you want.
        
        :param prompt: The prompt to send to GPT
        :type prompt: str
        
        :param model: The model to use. Defaults to gpt-4
        :type model: str
        """
        
        if model:
            self.Model = model
        
        # Tell ChatGPT it is a Python expert
        # It also lets GPT know that we will give it a history of previous conversations
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
        
        # Customize the number of words to use for the history based on the model
        # GPT-4 can handle more words than GPT-3, twice the number of tokens on the base model (8k), up to 32k tokens
        # If you have a gpt-4 model that can take more tokens, modify the word_count here
        # TODO: consider moving this to the class constructor
        if model == "gpt-4":
            word_count = 4000
        else:
            word_count = 2000
        
        # Get previous history from the database
        entries = self.get_last_entries(min_words=word_count)
 
        # ChatGPT needs the entries broken out by prompts and responses
        for entry in entries:
            timestamp = entry['timestamp']
            historical_prompt = entry['prompt']
            message = entry['message']
            
            messages.append({"role": "user", "content": f"At {timestamp}: {historical_prompt}"})
            messages.append({"role": "system", "content": f"At {timestamp}: {message}"})
 
        messages.append({"role": "user", "content": prompt})
        self.printMessage("...",  message_from="prompt")
 
        # Send the prompt to GPT
        # Basic error checking, primarily to catch when GPT-4 is overloaded and switch to GPT-3.5 Turbo
        response = None
        try:
            response = openai.ChatCompletion.create(
                model = self.Model,
                messages = messages
            )
        except openai.error.APIError as error:
            # if there is an API error with message exceeded maximum allotted capacity, switch to gpt-3.5-turbo model
            if error.status == 429 and model == 'gpt-4' :
                self.printMessage("GPT 4 is unavailable, switching to GPT 3.5 Turbo", message_from="error")
                response = self.chat(prompt, model = "gpt-3.5-turbo")
        
        # if there is a rate limit error, wait and try again        
        except openai.error.RateLimitError as error:
            self.printMessage("Rate limit exceeded, waiting 15 seconds and trying again", message_from="error")
            if attempts < max_retries - 1:
                attempts += 1
                time.sleep(backoff_time * attempts)
                response = self.chat(prompt, model = model, check_bing = check_bing, attempts = attempts, max_retries=max_retries, backoff_time = backoff_time)
        except Exception as error:
            # if it's another kind of error, raise the error
            raise error
        
        # Grab the first message from the response.
        # GPT can return more than one message, but we only want the first one. This script only requests a single response.
        # See OpenAI docs for more info on multiple responses
        message = response.choices[0].message.content
        
        self.LastResponse = message
        self.LastPrompt = prompt
 
        return self.LastResponse
 
    def query_chat_gpt(self, prompt, model = "", attempts = 0, max_retries = 3, backoff_time = 15):
        
        if not model:
            model = self.Model
            
        # Send the prompt to GPT
        # Basic error checking, primarily to catch when GPT-4 is overloaded and switch to GPT-3.5 Turbo
        response = None
        try:
            response = openai.ChatCompletion.create(
                model = self.Model,
                messages = messages
            )
        except openai.error.APIError as error:
            # if there is an API error with message exceeded maximum allotted capacity, switch to gpt-3.5-turbo model
            if error.status == 429 and model == 'gpt-4' :
                self.printMessage("GPT 4 is unavailable, switching to GPT 3.5 Turbo", message_from="prompt")
                response = self.query_chat_gpt(prompt, model = "gpt-3.5-turbo", attempts = attempts, max_retries=max_retries, backoff_time=backoff_time)
        
        # if there is a rate limit error, wait and try again        
        except openai.error.RateLimitError:
            self.printMessage("Rate limit exceeded, waiting 15 seconds and trying again", message_from="error")
            if attempts < max_retries - 1:
                attempts += 1
                time.sleep(backoff_time * attempts)
                response = self.query_chat_gpt(prompt, model = model, attempts = attempts, max_retries=max_retries, backoff_time=backoff_time)
        except Exception as error:
            # if it's another kind of error, raise the error
            raise error 
        
        # Grab the first message from the response.
        # GPT can return more than one message, but we only want the first one. This script only requests a single response.
        # See OpenAI docs for more info on multiple responses
        message = response.choices[0].message.content
        
        return message

    def search_bing(self, query, BingKey = ""):
        
        if not BingKey:
            BingKey = self.BingKey
        
        if self.DEBUG:
            self.printMessage(f"Searching Bing for {query}", message_from="debug")
        
        url = f"https://api.bing.microsoft.com/v7.0/search?q={query}"
        headers = {"Ocp-Apim-Subscription-Key": self.BingKey}
        response = requests.get(url, headers=headers)
        results = response.json().get("webPages", {}).get("value", [])
        urls = [result['url'] for result in results]
        
        if self.DEBUG:
            self.printMessage(results, message_from="debug")
            self.printMessage(f"Found {len(results)} results", message_from="debug")
            # self.printMessage(f"First result: {results[0]['url']}", message_from="debug")
            
        return urls if urls else None

    def extract_relevant_text(self, url):
        
        if self.DEBUG:
            self.printMessage(f"Extracting relevant text from {url}", message_from="debug")
        
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join([p.text for p in paragraphs])
        return text
 
    def save_chat(self, prompt, message, chatname = ''):
        """
        Save the chat history to a database.
        
        :param prompt: The prompt to sent to GPT
        :type prompt: str
        
        :param message: The response from GPT
        :type message: str
        
        :param chatname: The name of the chat. If not provided, a chat name will be generated
        :type chatname: str
        """
        
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
            self.Chatname = f"chat_{now.strftime('%Y_%m_%d_%H_%M_%S')}_{username}"
            
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
            entry = entries[0]['message']
            entries.pop(0)
            word_count -= len(entry.split(' '))

        conn.close()
        return entries

    def StartChat(self):
        while True:
            fact_check_response = ""
            response = ""
            prompt = ""
            prompt = self.AskForInput()
            

            try:                
                with Halo(text='GPT is thinking.', spinner='dots'):
                    response = self.chat(prompt)
            except:
                response = self.chat(prompt)
            
            self.save_chat(prompt, response)
            
            if self.FactCheck:
                if self.BingKey == "":
                    self.printMessage("You need to provide a Bing API key to use fact checking", message_from="error")
                    self.printMessage(response, message_from="gpt")
                    self.FactCheck = False
                    continue
              
                with Halo(text='GPT is fact checking.', spinner='dots'):
                    fact_check_response = self.fact_check(prompt, response)

                    if fact_check_response == response:                
                        self.printMessage(response, message_from="gpt")
                        
                    else:
                        self.printMessage(fact_check_response, message_from="gpt")
                        self.save_chat(f"After running a fact check a better response was {fact_check_response}", "Thank you, I will remember that")
                    
            else:
                self.printMessage(response, message_from="gpt")
            
            if "---output---" in response:
                self.printMessage(f"Output: {response.split('---output---')[1]}", message_from="gpt")
    
    def fact_check(self, prompt, response):
        
        if self.DEBUG:
            self.printMessage("We got an initial response from GPT, will now check it against Bing", message_from="debug")
            
        attempted_prompts = []
        bing_results = None
        while bing_results == None or bing_results == "":
            
            if not attempted_prompts:    
                bing_prompt = f"""
                I just asked you {prompt} and you said {response}. \n 
                I'm going to do a Bing search to double check that.
                First, review the response and pull out any facts that you think are important. \n
                Second, compose a search query that you think will find a fact check for the response. \n
                Third, remove and quotes from the query \n
                Fourth, output the query as a string, one query per line. \n
                Do not output any other text. \n
                \n
                
                """
                
            else:
                bing_prompt = f"""
                I just asked you {prompt} and you said {response}. \n 
                I'm going to do a Bing search to double check that.
                First, review the response and pull out any facts that you think are important. \n
                Second, compose a search query that you think will find a fact check for the response. \n
                Third, remove and quotes from the query \n
                Fourth, output the query as a string, one query per line. \n
                Do not output any other text. \n
                I tried the following search queries and they did not work: {attempted_prompts}
                \n
                """
            
            fact_check_queries = self.query_chat_gpt(prompt = bing_prompt, model = "gpt-3.5-turbo")
            
            if self.DEBUG:
                self.printMessage(f"Fact check queries: {fact_check_queries.splitlines()}", message_from="debug")
            
            
            summary = ""
            for fact_check_query in fact_check_queries.splitlines():
                
                if self.DEBUG:
                    self.printMessage(f"Bing query: {fact_check_query}", message_from="debug")
            
                bing_results = self.search_bing(fact_check_query)
                
                if not bing_results:
                    attempted_prompts.append(bing_prompt)

                num_result = 1
                
                for result in bing_results:
                    if num_result <= self.NumFactchecks:
                        if self.DEBUG:
                            self.printMessage(f"Fact checking result {num_result}: {result}", message_from="debug")
                            
                        result_information = self.extract_relevant_text(result)
                    
                        if self.DEBUG:
                            self.printMessage(f"Result information: {result_information} \n \n", message_from="debug")
                    
                        response_words = result_information.split(" ")
                        word_count = len(response_words)
                        
                        if self.DEBUG:
                            self.printMessage(f"Word count: {word_count}", message_from="debug")
                        
                        # This section breaks up the response into 2000 word chunks, and then summarizes each chunk
                        # This is necessary because GPT-3 has a token limit of 4096, or roughly 3000 words. That includes both the prompt and the response
                        # You can change the 2000 to a lower number if you want to summarize more frequently, but it will take longer
                        # Or change it to a higher number when we have a model that accepts more tokens
                        if word_count > 2000:
                            while word_count > 2000:
                                if self.DEBUG:
                                    self.printMessage(f"Word count was too high, splitting up, the section we are summarizing is: {response_words[:2000]}", message_from="debug")
                                
                                split_information = response_words[:2000]
                                response_words = response_words[2000:]
                                
                                summarize_prompt = f"We just ran a bing search, and this is what the first search item had in it: {split_information} \n Please summarize the information in the result. Keep all the information, but make it shorter, except code blocks."
                                summary_response = self.query_chat_gpt(summarize_prompt, model = "gpt-3.5-turbo")
                                word_count = len(response_words)
                        else:   
                            summarize_prompt = f"We just ran a bing search, and this is what the first search item had in it: {result_information} \n Please summarize the information in the result. Keep all the information, but make it shorter, except code blocks."
                            summary_response = self.query_chat_gpt(summarize_prompt, model = "gpt-3.5-turbo")
                        
                        if self.DEBUG:
                            self.printMessage(f"Summary response from ChatGPT: {summary_response}", message_from="debug")
                        
                        # Check if the summary is relevant to the response
                        # Bing search results are often not al,ways relevant to the response, so we want to make sure that the summary is relevant
                        # For instance, when asking for an essay on the events of 1776 in the United States Bing may return results from Brexit, based on the
                        # search query ChatGPT generated. (This is a real example)
                        relevant_prompt = f"I decided to fact check your last response with a bing search. Your response was {response} \n\n Here is the summary of the result: {summary_response} \n Is this relevant to the response? If so, please say 'yes'. If not, please say 'no'. Do not say anything else."
                        relevant_response = self.query_chat_gpt(relevant_prompt, model = "gpt-3.5-turbo")
                        
                        if "yes" in relevant_response.lower():
                            summary = summary + f"\n {summary_response}"
                        
                        num_result += 1
        
        if self.DEBUG:
            self.printMessage(f"Summary: {summary}", message_from="debug")
        
        fact_check_prompt = f"I did a Bing search to double check that, here are the results: {summary} \n update your last response, but only if it matters. If it doesn't matter, just say 'no changes'."
        fact_check_response = self.chat(fact_check_prompt)
        
        if self.DEBUG:
            self.printMessage(f"Fact checked response: {fact_check_response}", message_from="debug")
        
        if "no changes" in fact_check_response.lower():
            return response
            
        else:
            self.save_chat(fact_check_prompt, fact_check_response)
            return fact_check_response
                
    def AskForInput(self, hint = ""):
        """
        Ask the user for input until two blank lines are entered.
        
        :return: The user input as a single string
        """
        
        if not hint:
            hint = f'Ask me anything! (Enter two consecutive empty lines to submit, quit or exit to exit). You are using ChatGPT {self.Model} \n'
        
        while True:
            # Initialize an empty list to hold the user inputs
            self.printMessage(hint)
            user_inputs = []
            
            # Keep accepting input until two consecutive empty lines are entered
            while len(user_inputs) < 2 or user_inputs[-2:] != ["", ""]:
                user_input = input()
                
                if "/metabetter" in user_input:
                    self.metaBetter()
                
                if user_input == "```":
                    while user_input != "```":
                        user_input = input()
                        user_inputs.append(user_input)
                
                    if user_input.lower() == "exit" or user_input.lower() == "quit":
                        exit(0)
                        
                elif user_input.startswith("/reset chat"):
                    name = user_input.replace("/reset chat", "").strip()
                    if name:
                        self.Chatname = name
                        NewName = self.ResetChat(chatname = self.Chatname)
                    else:
                        NewName = self.ResetChat()
                    self.printMessage(f'New chat started with name {NewName}')
                    continue
                
                elif user_input.startswith("/delete chat"):
                    delete_name = user_input.replace("/delete chat", "").strip()
                    if delete_name:
                        conn = sqlite3.connect(self.history_file)
                        c = conn.cursor()
                        c.execute(f"DELETE FROM chat WHERE chatname='{delete_name}'")
                        conn.commit()
                        conn.close()
                        self.printMessage(f"Chat {delete_name} deleted")
                    else:
                        NewName = self.ResetChat()
                        self.printMessage(f'You must specify a chat name to delete. Your current chat name is {self.Chatname}')
  
                elif user_input.startswith("/delete allchats"):
                    conn = sqlite3.connect(self.history_file)
                    c = conn.cursor()
                    c.execute("DELETE FROM chat")
                    conn.commit()
                    conn.close()
                    self.printMessage(f'All chats deleted')

                    
                elif user_input.startswith("/model"):
                    self.Model = user_input.split(" ")[1].strip()
                    self.printMessage(f"Model changed to {self.Model}\n")
                    
                elif user_input.startswith("/debug on"):
                    self.DEBUG = True
                    self.printMessage("Debug mode on")
                    
                elif user_input.startswith("/debug off"):
                    self.DEBUG = True
                    self.printMessage("Debug mode off")
                    
                elif user_input.startswith("/fact check on"):
                    self.FactCheck = True
                    num_checks = user_input.replace("/fact check on", "").strip()
                    
                    if num_checks:
                        self.NumFactChecks = int(num_checks)
                        
                    self.printMessage(f"Fact check on, will check up to {self.NumFactChecks} Bing results")
                                        
                elif user_input.startswith("/fact check off"):
                    self.FactCheck = False
                    self.printMessage("Fact check off")
                    
                elif user_input.startswith("/list chats"):
                    conn = sqlite3.connect(self.history_file)
                    chat_names = conn.execute("SELECT DISTINCT chatname FROM chat").fetchall()
                    
                    for name in chat_names:
                        self.printMessage(name[0])
                        
                elif user_input.startswith("/history"):
                    conn = sqlite3.connect(self.history_file)
                    entries = conn.execute(f"SELECT prompt, message, timestamp from chat WHERE chatname='{self.Chatname}' ORDER BY timestamp ASC").fetchall()
                    
                    for entry in entries:
                        timestamp = entry[2]
                        self.printMessage(f"You: {entry[0]} ({timestamp})", message_from="prompt")
                        self.printMessage("")
                        self.printMessage(f"GPT: {entry[1]} ({timestamp})", message_from="gpt")

                        
                elif user_input == "exit" or user_input == "quit":
                    exit(0)
                
                # Only add non-commands to the input list
                else:    
                    user_inputs.append(user_input)
                
            # Insert a new line so it looks cleaner    
            print("")    
            # Remove the two consecutive empty lines from the user inputs
            user_inputs = user_inputs[:-2]
            
            # Combine the individual lines into a single string
            prompt = "\n".join(user_inputs)
            
            if not prompt.strip():
                self.printMessage("You didn't enter a prompt. Please try again.")
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