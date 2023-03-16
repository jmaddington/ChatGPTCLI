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

## History
Chat history is saved in a sqlite file in your home directory, this is required for the chat to work correctly.
If history is not saved, then every message restarts the chat and ChatGPT doesn't have any context from previous 
chat entries.