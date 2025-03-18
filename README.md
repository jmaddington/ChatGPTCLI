# ARCHIVED

This is no longer maintained because Simon Willison has such a great tool at https://github.com/simonw/llm

# ASKGPTCLI

A command line interface to ChatGPT, for when you have questions and don't want to switch to Chrome.

## Install
Either clone the repository or download the code as a zip and save it to a directory of your choice.

Install python. On macOS you can use homebrew

```shell
brew install python
source myenv/bin/activate

python pip install -r requirements.txt
```

Next, edit your .bashrc or .zshrc file to include your OpenAI API key:
```bash
export OPENAI_API_KEY="XXX"
```

Exit the terminal and reopen to the same directory.

You can use it right from the command line in this directory. If you want it to be available everywhere then add 
this alias to your .bashrc or .zshrc file:

```bash
GPTDIR="~/path/to/where/you/installed/this"
alias askgpt='source $GPTDIR/env/bin/activate && python3 $GPTDIR/askgpt.py "$@" && deactivate'
```

## Usage
If you added the alias, then just use `askgpt` from your terminal.

__There are three things you need to know about input__

- Input does not enter until you enter two blank lines
- If you start code with \`\`\` then it will accept input until you enter \`\`\` and two blank lines
- `exit` or `quit` will gracefully close the program

### Reset the chat
Sometimes GPT gets confused with too much background information. You can reset the
chat by typing `reset chat`
You can name your new chat with `reset chat=myName`, although that change only matters
to the SQLite file.

This effectively lets you switch between chats if you want as well.

### See Chat History
`/history` will output the entire history of the currently named chat.
This may include entries that are not sent to ChatGPT in the current context because
they are over the token limit.

### Delete a chat history
```/delete chat <chatname>```

### Delete all chats
```/delete allchats```

### ChatGPT model
This script defaults to `gpt-4`. If you do not have access to it or would like to use another version
edit this line as needed:
```python
    Model = "gpt-4"
```

The script will fall back to `gpt-3.5-turbo` if there is an API error:
```python
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
                self.chat(prompt, model = "gpt-3.5-turbo")
            else:
                # if it's another kind of error, raise the error
                raise error
```

Edit `self.chat(prompt, model = "gpt-3.5-turbo")` as needed to create a fallback for yourself.
Or, you can replace the entire section to to:

```python
    response = None
        response = openai.ChatCompletion.create(
            model = self.Model,
            messages = messages
        )
```


### Change models during chat
You can change GPT models during you chat with:
```python
/model <your preferred model>
```

## History
Chat history is saved in a sqlite file in your home directory, this is required for the chat to work correctly.
If history is not saved, then every message restarts the chat and ChatGPT doesn't have any context from previous 
chat entries.
