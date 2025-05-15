
import os
import json
import requests
from langchain_openai import ChatOpenAI

# Set your OpenAI API key
os.environ["OPENAI_API_KEY"] = "your-api-key-here"

# MCP Client to discover and call tools
class MCPClient:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.manifest = self._fetch_manifest()

    def _fetch_manifest(self):
        response = requests.get(f"{self.base_url}/manifest")
        return response.json()

    def get_tool_names(self):
        return [tool["name"] for tool in self.manifest.get("tools", [])]

    def get_tool_info(self, name):
        for tool in self.manifest.get("tools", []):
            if tool["name"] == name:
                return tool
        return None

    def call_tool(self, name, params):
        response = requests.post(f"{self.base_url}/tools/{name}", json=params)
        return response.json()

# Main logic
def run():
    llm = ChatOpenAI(temperature=0, model="gpt-4")
    client = MCPClient()

    # Describe all available tools to the LLM
    tool_descriptions = []
    for tool in client.manifest.get("tools", []):
        tool_descriptions.append({
            "name": tool["name"],
            "description": tool.get("description", ""),
            "params": tool.get("input_schema", {}).get("properties", {})
        })

    print("MCP Zero Agent Interface Ready!")
    print("Ask anything and GPT-4 will decide which tool to use.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ("quit", "exit"):
            break

        system_prompt = f"""
        You are an assistant with access to the following tools:
        {json.dumps(tool_descriptions, indent=2)}

        Based on the user input, respond ONLY with a JSON object like:
        {{
          "tool": "<tool_name>",
          "params": {{
            "param1": "value1",
            ...
          }}
        }}

        Do NOT add commentary or explanations. ONLY output the JSON.
        """

        try:
            response = llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ])

            response_text = response.content.strip()
            print(f"LLM Response:\n{response_text}")

            tool_call = json.loads(response_text)
            result = client.call_tool(tool_call["tool"], tool_call["params"])

            print("\n✅ Tool result:")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    run()
