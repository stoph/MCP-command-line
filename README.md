# Universal MCP Client

A Python-based client for testing and interacting with any Model Context Protocol (MCP) server. This tool provides a flexible command-line interface to discover server capabilities, execute tools, and explore MCP server functionality.

## Features

- 🔧 **Universal compatibility**: Works with any STDIO-based MCP server
- 📋 **Tool discovery**: Automatically lists available tools, resources, and prompts
- 🎯 **Interactive mode**: Browse and select tools with guided parameter input
- ⚙️ **Configuration files**: Store server settings, environment variables, and tools in JSON
- 🔀 **Flexible execution**: Run single tools, multiple tools, or batch operations
- 🎨 **Beautiful output**: Color-coded results with JSON formatting
- 🔐 **Environment support**: Pass API keys and configuration via environment variables

## Installation

No additional dependencies required - uses Python standard library only.

```bash
# Clone or download mcp.py
python3 mcp.py --help
```

## Quick Start

### Basic Usage

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

### Using Configuration Files

Create a `config.json` file:
```json
{
  "server": "npx -y @modelcontextprotocol/server-google-maps",
  "env": {
    "GOOGLE_MAPS_API_KEY": "your-api-key-here",
    "DEBUG": "true"
  },
  "tools": [
    {
      "name": "maps_search_places",
      "arguments": {
        "query": "Golden Gate Bridge"
      }
    }
  ],
  "options": {
    "verbose": false,
    "interactive": false,
    "list_only": false
  }
}
```

Run with config file:
```bash
python3 mcp.py --config-file config.json
```

## Command Line Options

### Server Configuration
- `--server`: MCP server command to execute (required if not in config)
- `--config-file`: JSON configuration file path

### Environment Variables
- `--env`: Environment variables as JSON object or KEY=VALUE pairs
- `--env-file`: Load environment variables from file

### Tool Execution
- `--tool`: Execute specific tool (JSON format). Can be used multiple times.
- `--interactive`: Interactive tool selection mode

### Operation Modes
- `--list-only`: Only discover and list server capabilities
- `--verbose`: Show detailed JSON-RPC message traffic

## Configuration File Format

The configuration file supports four main sections:

### Server
```json
{
  "server": "npx -y @modelcontextprotocol/server-name"
}
```

### Environment Variables
```json
{
  "env": {
    "API_KEY": "your-key-here",
    "DEBUG": "true"
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

- **Environment variables** (`env` section): Passed to the MCP server process itself
  - `DEBUG`: Server-side debugging/logging
  - `API_KEY`: Authentication credentials for the server
  
- **Options** (`options` section): Control the client behavior
  - `verbose`: Show JSON-RPC message traffic in the client
  - `interactive`: Enable interactive tool selection
  - `list_only`: Only list capabilities, don't execute tools

## Examples

### GitHub Server
```bash
# List GitHub server capabilities
python3 mcp.py --server "npx -y @modelcontextprotocol/server-github" --list-only

# Search repositories interactively
python3 mcp.py --server "npx -y @modelcontextprotocol/server-github" --interactive

# Search with specific query
python3 mcp.py --server "npx -y @modelcontextprotocol/server-github" \
  --tool '{"name": "search_repositories", "arguments": {"query": "typescript", "language": "TypeScript"}}'
```

### Google Maps Server
```bash
# With environment variables
python3 mcp.py --server "npx -y @modelcontextprotocol/server-google-maps" \
  --env "GOOGLE_MAPS_API_KEY=your-key-here" \
  --tool '{"name": "maps_search_places", "arguments": {"query": "restaurants near me"}}'
```

### Filesystem Server
```bash
# List files
python3 mcp.py --server "npx -y @modelcontextprotocol/server-filesystem" \
  --env "ALLOWED_DIRECTORIES=/Users/username/Documents" \
  --interactive
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

### Environment Variables
```
✗ Tool execution failed: Authentication required
```
- Verify API keys are correctly set in `env` section
- Check the MCP server documentation for required environment variables

### JSON Parsing Errors
```
✗ Invalid JSON in tool specification
```
- Validate JSON syntax using a JSON validator
- Ensure proper escaping of quotes in command line arguments

## Protocol Support

- **Protocol Version**: 2025-06-18 (latest MCP specification)
- **Transport**: STDIO (HTTP transport planned for future versions)
- **Capabilities**: Tools, Resources, Prompts, Logging

## Contributing

This is a development tool for exploring MCP servers. Feel free to extend it with additional features like:
- HTTP transport support
- Resource and prompt execution
- Configuration templates for popular servers
- Batch testing capabilities

## License

This project is provided as-is for educational and development purposes. 