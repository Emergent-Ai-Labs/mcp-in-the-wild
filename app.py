import os
import json
from pathlib import Path
import traceback
from flask import Flask, render_template, request, jsonify
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from advanced_mcp_client import AdvancedMCPClient

app = Flask(__name__)

# Set your OpenAI API key
os.environ["OPENAI_API_KEY"] = ""

# Load LLM
llm = ChatOpenAI(model="gpt-4", temperature=0)

# MCP tools
mcp_client = AdvancedMCPClient()
tools = mcp_client.get_tools()
tool_funcs = {tool.name: tool.func for tool in tools}

@app.route('/')
def index():
    """
    Renders the main page (index.html), passing the available tools to the template.
    """
    return render_template('index.html', tools=tools)

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handles chat requests.  It receives a user message, uses the LLM to select
    an appropriate tool, calls the tool, and returns the result.
    """
    data = request.json
    user_input = data.get('message', '')

    try:
        print(f"User: {user_input}")

        # Ask GPT to pick a tool
        tool_selection_prompt = (
            "You have access to the following tools:\n" +
            "\n".join([f"- {t.name}: {t.description}" for t in tools]) +
            "\n\nBased on the user's question, respond ONLY with a JSON object like:\n" +
            '{ "tool": "tool_name", "params": { "key": "value" } }\n\n' +
            f"User's question: {user_input}"
        )

        result = llm.invoke([HumanMessage(content=tool_selection_prompt)])
        print("LLM Response:", result.content)

        parsed = json.loads(result.content)
        tool_name = parsed.get("tool")
        params = parsed.get("params", {})

        if tool_name not in tool_funcs:
            fallback_message = parsed.get("params", {}).get("message") or \
                            "Sorry, I couldn't understand your request. Try asking a specific question!"
            return jsonify({"response": fallback_message}), 200

        tool_result = tool_funcs[tool_name](params)

        try:
            result_data = json.loads(tool_result)
            pretty_result = json.dumps(result_data, indent=2)
        except:
            pretty_result = tool_result

        return jsonify({"response": pretty_result})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/tools', methods=['GET'])
def get_tools():
    """
    Returns a list of available tools, formatted for display in the UI.
    """
    return jsonify([
        {"name": tool.name, "description": str(tool.description).splitlines()[0]}
        for tool in tools
    ])

if __name__ == '__main__':
    """
    Main entry point for the Flask application.  It ensures the 'templates'
    directory and 'index.html' file exist, and then starts the Flask
    development server.
    """
    # Create the templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)

    # Define the path for the index.html file
    index_path = Path('templates/index.html')

    # Check if the index.html file exists
    if not index_path.exists():
        # If it doesn't exist, write the HTML content to the file
        print("⚠️  Writing default HTML to templates/index.html.")
        index_path.write_text('''
<!DOCTYPE html>
<html>
<head>
    <title>MCP-Powered LangChain Agent</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        #chat-container { height: 400px; border: 1px solid #ccc; overflow-y: auto; padding: 10px; margin-bottom: 10px; }
        #message-input { width: 80%; padding: 8px; }
        #send-button { padding: 8px 15px; }
        .user-message { text-align: right; margin: 5px; padding: 8px; background-color: #e3f2fd; border-radius: 8px; }
        .bot-message { text-align: left; margin: 5px; padding: 8px; background-color: #f1f1f1; border-radius: 8px; }
        .tools-section { margin-top: 20px; }
        .tool-card { border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>MCP-Powered LangChain Agent</h1>
    <div id="chat-container"></div>
    <div>
        <input type="text" id="message-input" placeholder="Type your message here...">
        <button id="send-button">Send</button>
    </div>

    <div class="tools-section">
        <h2>Available MCP Tools</h2>
        <div id="tools-list"></div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const chatContainer = document.getElementById('chat-container');
            const messageInput = document.getElementById('message-input');
            const sendButton = document.getElementById('send-button');
            const toolsList = document.getElementById('tools-list');

            // Fetch the list of tools from the server
            fetch('/api/tools')
                .then(response => response.json())
                .then(tools => {
                    // Iterate over the tools and create a card for each
                    tools.forEach(tool => {
                        const toolCard = document.createElement('div');
                        toolCard.className = 'tool-card';
                        toolCard.innerHTML = `<strong>${tool.name}</strong>: ${tool.description}`;
                        toolsList.appendChild(toolCard); // Append the card to the tools list
                    });
                });

            // Function to send a message to the server
            function sendMessage() {
                const message = messageInput.value.trim(); // Get the message from the input
                if (!message) return; // If the message is empty, do nothing

                // Create a div for the user's message
                const userMessageDiv = document.createElement('div');
                userMessageDiv.className = 'user-message'; // Assign the user-message class
                userMessageDiv.textContent = message; // Set the text content
                chatContainer.appendChild(userMessageDiv); // Append to the chat container
                chatContainer.scrollTop = chatContainer.scrollHeight; // Scroll to the bottom
                messageInput.value = ''; // Clear the input field

                // Send the message to the server's /api/chat endpoint
                fetch('/api/chat', {
                    method: 'POST', // Use the POST method
                    headers: { 'Content-Type': 'application/json' }, // Set the content type
                    body: JSON.stringify({ message }) // Convert the message to JSON
                })
                .then(response => response.json()) // Parse the JSON response
                .then(data => {
                    // Create a div for the bot's message
                    const botMessageDiv = document.createElement('div');
                    botMessageDiv.className = 'bot-message'; // Assign the bot-message class
                    // Set the text content of the bot's message.  Handle both string
                    // and object responses.  If it's an object, pretty-print it as JSON.
                    botMessageDiv.textContent = typeof data.response === 'object'
                        ? JSON.stringify(data.response, null, 2) // Pretty print JSON
                        : data.response || '[No response]'; // Default text
                    chatContainer.appendChild(botMessageDiv); // Append to the chat container
                    chatContainer.scrollTop = chatContainer.scrollHeight; // Scroll to bottom
                });
            }

            // Event listener for the send button
            sendButton.addEventListener('click', sendMessage);

            // Event listener for the message input (Enter key)
            messageInput.addEventListener('keypress', function(event) {
                if (event.key === 'Enter') {
                    sendMessage(); // Call sendMessage when Enter is pressed
                }
            });
        });
    </script>
</body>
</html>
        ''')

    # Run the Flask application in debug mode on port 5000
    app.run(debug=True, port=5000)
