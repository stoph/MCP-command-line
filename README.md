# Universal MCP Client

A Python-based client for testing and interacting with any Model Context Protocol (MCP) server. This tool provides a flexible command-line interface to discover server capabilities, execute tools, and explore MCP server functionality over both STDIO and HTTP transports.

## Features

- 🔧 **Universal compatibility**: Works with any STDIO-based or HTTP-based MCP server
- 🌐 **Automatic transport detection**: Detects HTTP vs STDIO servers automatically
- 📋 **Tool discovery**: Automatically lists available tools, resources, and prompts
- 🎯 **Interactive mode**: Browse and select tools with guided parameter input
- ⚙️ **Configuration files**: Store server settings, environment variables, and tools in JSON
- 🔀 **Flexible execution**: Run single tools, multiple tools, or batch operations
- 🎨 **Beautiful output**: Color-coded results with JSON formatting
- 🔐 **Smart authentication**: Environment variables → HTTP headers or subprocess environment
- 🚀 **Simple HTTPS**: Uses requests library for seamless SSL/TLS support
- 🔍 **Debug support**: Verbose mode shows HTTP headers and JSON-RPC messages

## Installation

Minimal dependencies - automatically installs `requests` library if needed for HTTP support.

```bash
# Clone or download mcp.py
python3 mcp.py --help
```

## Quick Start

### STDIO Servers

List server capabilities:
```bash
python3 mcp.py --server "npx -y @modelcontextprotocol/server-github" --list-only
```

Execute a specific tool:
```bash
python3 mcp.py --server "npx -y @modelcontextprotocol/server-github" \
  --tool '{"name": "search_repositories", "arguments": {"query": "MCP"}}'
```

Interactive mode:
```bash
python3 mcp.py --server "npx -y @modelcontextprotocol/server-github" --interactive
```

### HTTP Servers

Connect to HTTP MCP server:
```bash
python3 mcp.py --server "https://api.example.com/mcp" --list-only
```

With authentication:
```bash
python3 mcp.py --server "https://api.example.com/mcp" \
  --env '{"AUTHORIZATION": "Bearer your-token-here"}' \
  --interactive
```

### Using Configuration Files

Create a `config.json` file:
```json
{
  "server": "https://api.example.com/mcp/v1",
  "env": {
    "AUTHORIZATION": "Bearer your-token-here",
    "X-API-KEY": "your-api-key"
  },
  "tools": [
    {
      "name": "search_data",
      "arguments": {
        "query": "example search"
      }
    }
  ],
  "options": {
    "verbose": true,
    "interactive": false,
    "list_only": false
  }
}
```

Run with config file:
```bash
python3 mcp.py --config-file config.json
```

## Transport Support

The client automatically detects the transport type based on the server specification:

### STDIO Transport
- **Detection**: Any server command that doesn't start with `http://` or `https://`
- **Usage**: Subprocess communication via stdin/stdout
- **Environment**: Variables passed to subprocess environment
- **Examples**: `npx -y @modelcontextprotocol/server-github`, `./my-mcp-server`

### HTTP Transport  
- **Detection**: Server URLs starting with `http://` or `https://`
- **Usage**: HTTP POST requests to the exact URL provided
- **Authentication**: Environment variables converted to HTTP headers
- **SSL/TLS**: Automatic HTTPS support using requests library
- **Examples**: `https://api.example.com/mcp`, `http://localhost:3000/mcp/v1`

### Authentication Mapping

For HTTP servers, environment variables are automatically converted to HTTP headers:

| Environment Variable | HTTP Header | Example |
|---------------------|-------------|---------|
| `AUTHORIZATION` | `Authorization` | `Bearer token123` |
| `*_API_KEY` | `X-API-Key` | `your-api-key` |
| `X-*` | Direct passthrough | `X-Custom-Header: value` |

## Command Line Options

### Server Configuration
- `--server`: MCP server command or HTTP URL (required if not in config)
- `--config-file`: JSON configuration file path

### Environment Variables
- `--env`: Environment variables as JSON object or KEY=VALUE pairs
- `--env-file`: Load environment variables from file

### Tool Execution
- `--tool`: Execute specific tool (JSON format). Can be used multiple times.
- `--interactive`: Interactive tool selection mode

### Operation Modes
- `--list-only`: Only discover and list server capabilities
- `--verbose`: Show detailed HTTP headers and JSON-RPC message traffic

## Configuration File Format

The configuration file supports four main sections:

### Server
```json
{
  "server": "https://api.example.com/mcp/v1"
}
```

### Environment Variables
```json
{
  "env": {
    "AUTHORIZATION": "Bearer your-token-here",
    "GITHUB_API_KEY": "your-api-key",
    "X-CLIENT-ID": "your-client-id"
  }
}
```

### Tools
```json
{
  "tools": [
    {
      "name": "tool_name",
      "arguments": {
        "param1": "value1",
        "param2": "value2"
      }
    }
  ]
}
```

### Options
```json
{
  "options": {
    "verbose": false,
    "interactive": false,
    "list_only": false
  }
}
```

## Environment Variables vs Options

- **Environment variables** (`env` section): 
  - **STDIO servers**: Passed to the MCP server process environment
  - **HTTP servers**: Converted to HTTP headers for authentication
  - Examples: `DEBUG`, `API_KEY`, `AUTHORIZATION`
  
- **Options** (`options` section): Control the client behavior
  - `verbose`: Show HTTP headers and JSON-RPC message traffic in the client
  - `interactive`: Enable interactive tool selection
  - `list_only`: Only list capabilities, don't execute tools

## Examples

### GitHub Server (STDIO)
```bash
# List GitHub server capabilities
python3 mcp.py --server "npx -y @modelcontextprotocol/server-github" --list-only

# Search repositories interactively
python3 mcp.py --server "npx -y @modelcontextprotocol/server-github" --interactive

# Search with specific query
python3 mcp.py --server "npx -y @modelcontextprotocol/server-github" \
  --tool '{"name": "search_repositories", "arguments": {"query": "typescript", "language": "TypeScript"}}'
```

### Google Maps Server (STDIO)
```bash
# With environment variables
python3 mcp.py --server "npx -y @modelcontextprotocol/server-google-maps" \
  --env "GOOGLE_MAPS_API_KEY=your-key-here" \
  --tool '{"name": "maps_search_places", "arguments": {"query": "restaurants near me"}}'
```

### HTTP API Server
```bash
# Basic HTTP server
python3 mcp.py --server "https://api.example.com/mcp" --list-only

# With Bearer authentication
python3 mcp.py --server "https://api.example.com/mcp/v1" \
  --env '{"AUTHORIZATION": "Bearer your-token-here"}' \
  --verbose --interactive

# With API key authentication
python3 mcp.py --server "https://api.example.com/mcp" \
  --env '{"GITHUB_API_KEY": "your-key-here"}' \
  --tool '{"name": "search", "arguments": {"query": "test"}}'
```

### Custom Headers
```bash
# Multiple authentication methods
python3 mcp.py --server "https://api.example.com/mcp" \
  --env '{"AUTHORIZATION": "Bearer token", "X-CLIENT-ID": "client123", "CUSTOM_API_KEY": "key456"}' \
  --verbose --list-only
```

## Interactive Mode

In interactive mode, the client will:

1. **Discover tools**: List all available tools with descriptions
2. **Tool selection**: Choose tools by number, range, or "all"
   - Single: `1`
   - Multiple: `1,3,5`  
   - Range: `1-3`
   - All: `all`
3. **Parameter input**: Guided JSON parameter entry with schema help
4. **Execution**: Run selected tools and display formatted results

## Troubleshooting

### Server Not Found
```
✗ Failed to start server: [Errno 2] No such file or directory
```
- Ensure the MCP server is installed (e.g., `npm install -g @modelcontextprotocol/server-github`)
- Check the server command syntax

### HTTP Connection Issues
```
✗ HTTP Request Error: Connection refused
```
- Verify the HTTP URL is correct and accessible
- Check if the server is running and accepting connections
- Ensure the URL includes the correct path (no automatic `/mcp` is appended)

### Authentication Errors
```
✗ HTTP Error 401: Unauthorized
```
- Verify API keys are correctly set in `env` section
- Use `--verbose` to inspect HTTP headers being sent
- Check the server documentation for required authentication format

### JSON Parsing Errors
```
✗ Invalid JSON in tool specification
```
- Validate JSON syntax using a JSON validator
- Ensure proper escaping of quotes in command line arguments

## Protocol Support

- **Protocol Version**: 2025-06-18 (latest MCP specification)
- **Transport**: STDIO and HTTP
- **Capabilities**: Tools, Resources, Prompts, Logging
- **Authentication**: Environment variables, HTTP headers, Bearer tokens, API keys

## Contributing

This is a development tool for exploring MCP servers. Feel free to extend it with additional features like:
- WebSocket transport support
- Resource and prompt execution
- Configuration templates for popular servers
- Batch testing capabilities

## License

This project is provided as-is for educational and development purposes. 