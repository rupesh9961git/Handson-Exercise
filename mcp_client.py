from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
      "mcp-abap-explorer": {
            "transport": "stdio",
            "command": "python",
            "args": ["/Users/I559384/Desktop/AI/MCP-Server/mcp-abap-explorer/server.py"],

    }
    }
)