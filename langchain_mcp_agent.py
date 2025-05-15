import os
import json
import requests
from typing import List

# Optional: if you want to still show LLM response (not required for tool tests)
from langchain_openai import ChatOpenAI

# Set your OpenAI API key if needed
os.environ["OPENAI_API_KEY"] = "your-api-key-here"

class MCPClient:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.manifest = self._fetch_manifest()

    def _fetch_manifest(self):
        response = requests.get(f"{self.base_url}/manifest")
        return response.json()

    def list_tools(self) -> List[str]:
        return [tool["name"] for tool in self.manifest.get("tools", [])]

    def get_tool_schema(self, tool_name: str):
        for tool in self.manifest.get("tools", []):
            if tool["name"] == tool_name:
                return tool
        return None

    def call_tool(self, tool_name: str, params: dict):
        response = requests.post(f"{self.base_url}/tools/{tool_name}", json=params)
        return response.json()


if __name__ == "__main__":
    client = MCPClient()
    tools = client.list_tools()

    print("Available MCP Tools:")
    for idx, tool in enumerate(tools):
        print(f"{idx+1}. {tool}")

    while True:
        try:
            tool_index = int(input("\nSelect a tool by number (or 0 to quit): "))
            if tool_index == 0:
                break
            tool_name = tools[tool_index - 1]
        except (ValueError, IndexError):
            print("Invalid selection. Try again.")
            continue

        tool_info = client.get_tool_schema(tool_name)
        print(f"\n→ Selected: {tool_name}")
        print("Description:", tool_info.get("description", ""))
        input_schema = tool_info.get("input_schema", {}).get("properties", {})

        payload = {}
        for param, meta in input_schema.items():
            default = meta.get("default", "")
            description = meta.get("description", "")
            user_input = input(f"{param} ({description}) [{default}]: ").strip()
            if not user_input and default:
                user_input = default
            payload[param] = user_input

        result = client.call_tool(tool_name, payload)
        print("\n✅ Tool response:")
        print(json.dumps(result, indent=2))