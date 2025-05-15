import os
import json
from pathlib import Path
import traceback
from flask import Flask, render_template, request, jsonify
from langchain_core.messages import HumanMessage, AIMessage

from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from advanced_mcp_client import AdvancedMCPClient

app = Flask(__name__)

# Initialize MCP client
mcp_client = AdvancedMCPClient()
tools = mcp_client.get_tools()

# Create memory
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

os.environ["OPENAI_API_KEY"] = ""

# Create LLM
if not os.environ.get("OPENAI_API_KEY"):
    raise EnvironmentError("OPENAI_API_KEY not set. Please configure it before running.")
llm = ChatOpenAI(temperature=0, model="gpt-4")

# Create agent prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an intelligent assistant with access to various tools through the Model Context Protocol (MCP).
Use these tools to help the user with their requests.
Always think step by step and use the appropriate tool when needed.

Available tools:
{tool_names}

When using tools:
1. Consider which tool is appropriate for the task
2. Format the input as valid JSON based on the tool's requirements
3. Analyze the tool's response to provide useful information to the user
"""),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create the agent
tool_names = "\n".join([f"- {tool.name}" for tool in tools])
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt.partial(tool_names=tool_names, tools=tools)
)

# Create agent executor
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True,
    handle_parsing_errors=True,
)

@app.route('/')
def index():
    return render_template('index.html', tools=tools)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message', '')

    try:
        print(f"Received user input: {user_input}")
        response = agent_executor.invoke({
            "input": user_input,
            "chat_history": [],  # Empty list for now
            "agent_scratchpad": []  # Must be a list of LangChain messages
        })
        print(f"LLM response: {response}")
        return jsonify({"response": response.get("output", "[No output]")})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/tools', methods=['GET'])
def get_tools():
    tool_info = []
    for tool in tools:
        tool_info.append({
            "name": tool.name,
            "description": str(tool.description).splitlines()[0]
        })
    return jsonify(tool_info)

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    index_path = Path('templates/index.html')
    if not index_path.exists():
        print("⚠️  Writing default HTML to templates/index.html. Custom changes will be overwritten.")
        index_path.write_text("""<!DOCTYPE html>
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

            fetch('/api/tools')
                .then(response => response.json())
                .then(tools => {
                    tools.forEach(tool => {
                        const toolCard = document.createElement('div');
                        toolCard.className = 'tool-card';
                        toolCard.innerHTML = `<strong>${tool.name}</strong>: ${tool.description}`;
                        toolsList.appendChild(toolCard);
                    });
                });

            function sendMessage() {
                const message = messageInput.value.trim();
                if (!message) return;

                const userMessageDiv = document.createElement('div');
                userMessageDiv.className = 'user-message';
                userMessageDiv.textContent = message;
                chatContainer.appendChild(userMessageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
                messageInput.value = '';

                fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                })
                .then(response => response.json())
                .then(data => {
                    const botMessageDiv = document.createElement('div');
                    botMessageDiv.className = 'bot-message';
                    botMessageDiv.textContent = data.response || '[No response]';
                    chatContainer.appendChild(botMessageDiv);
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                });
            }

            sendButton.addEventListener('click', sendMessage);
            messageInput.addEventListener('keypress', function(event) {
                if (event.key === 'Enter') {
                    sendMessage();
                }
            });
        });
    </script>
</body>
</html>""")

    app.run(debug=True, port=5000)
