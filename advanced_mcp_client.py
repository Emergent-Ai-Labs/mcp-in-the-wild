
import os
import json
import asyncio
import aiohttp
import requests
from typing import List, Dict, Any
from langchain_core.tools import Tool

class AdvancedMCPClient:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.manifest = self._fetch_manifest()
        self.tools_cache = {}

    def _fetch_manifest(self):
        response = requests.get(f"{self.base_url}/manifest")
        return response.json() if response.status_code == 200 else {"tools": []}

    async def batch_invoke_tools(self, tool_requests):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for req in tool_requests:
                tool_name = req.get("tool")
                params = req.get("params", {})
                task = self._async_call_tool(session, tool_name, params)
                tasks.append(task)
            return await asyncio.gather(*tasks)

    async def _async_call_tool(self, session, tool_name, params):
        try:
            async with session.post(f"{self.base_url}/tools/{tool_name}", json=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"status": "error", "message": f"Error {response.status}: {await response.text()}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_tools(self) -> List[Tool]:
        tools = []
        for mcp_tool in self.manifest.get("tools", []):
            tool_name = mcp_tool["name"]
            tool_desc = mcp_tool["description"]
            input_schema = mcp_tool.get("input_schema", {})
            self.tools_cache[tool_name] = {
                "schema": input_schema,
                "description": tool_desc
            }

            def create_tool_func(tool_name=tool_name):
                def tool_func(tool_input: str) -> str:
                    try:
                        if isinstance(tool_input, str):
                            try:
                                params = json.loads(tool_input)
                            except json.JSONDecodeError:
                                first_required = self.tools_cache[tool_name]["schema"].get("required", [])
                                if first_required:
                                    params = {first_required[0]: tool_input}
                                else:
                                    props = self.tools_cache[tool_name]["schema"].get("properties", {})
                                    if props:
                                        first_prop = list(props.keys())[0]
                                        params = {first_prop: tool_input}
                                    else:
                                        params = {"query": tool_input}
                        else:
                            params = tool_input
                        response = requests.post(f"{self.base_url}/tools/{tool_name}", json=params)
                        if response.status_code == 200:
                            result = response.json()
                            return json.dumps(result, indent=2)
                        else:
                            return f"Error: {response.status_code} - {response.text}"
                    except Exception as e:
                        return f"Error calling tool {tool_name}: {str(e)}"
                return tool_func

            arg_schema = ""
            if input_schema.get("properties"):
                arg_schema = "Arguments (in JSON format):\n"
                for prop_name, prop_details in input_schema["properties"].items():
                    required = "REQUIRED" if prop_name in input_schema.get("required", []) else "optional"
                    prop_type = prop_details.get("type", "any")
                    description = prop_details.get("description", "")
                    default = f", default: {prop_details['default']}" if "default" in prop_details else ""
                    arg_schema += f"- {prop_name} ({prop_type}, {required}{default}): {description}\n"

            enhanced_description = f"{tool_desc}\n\n{arg_schema}"
            tool = Tool(name=tool_name, description=enhanced_description, func=create_tool_func())
            tools.append(tool)
        return tools

async def run_batch_example():
    client = AdvancedMCPClient()
    results = await client.batch_invoke_tools([
        {"tool": "math", "params": {"operation": "add", "a": 5, "b": 7}},
        {"tool": "weather", "params": {"location": "tokyo"}},
        {"tool": "datetime", "params": {"format": "%Y-%m-%d"}}
    ])
    print("Batch results:")
    for result in results:
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(run_batch_example())
