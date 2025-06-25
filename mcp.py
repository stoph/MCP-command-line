import subprocess
import json
import time
import os
import argparse
import shlex
import sys

def display_mcp_result(response, title="Result"):
    """Display MCP tool response in a nicely formatted way"""
    if not response or "result" not in response:
        print(f"✗ {title}: No valid response")
        return
    
    result = response["result"]
    
    # Check if it's an error
    is_error = result.get("isError", False)
    status_color = "\033[31m" if is_error else "\033[32m"  # Red for error, green for success
    status_symbol = "✗" if is_error else "✓"
    
    print(f"{status_color}{status_symbol} {title}:\033[0m")
    
    # Process content array
    if "content" in result:
        for i, content_item in enumerate(result["content"]):
            content_type = content_item.get("type", "unknown")
            
            if content_type == "text":
                text_content = content_item.get("text", "")
                
                # Try to parse as JSON first
                try:
                    parsed_json = json.loads(text_content)
                    print(f"  \033[36mContent {i+1} (text):\033[0m")
                    print(json.dumps(parsed_json, indent=4))
                except json.JSONDecodeError:
                    # Not JSON, display as formatted text
                    print(f"  \033[36mContent {i+1} (text):\033[0m")
                    # Replace \n with actual newlines and clean up
                    formatted_text = text_content.replace('\\n', '\n').replace('\\"', '"')
                    for line in formatted_text.split('\n'):
                        if line.strip():  # Skip empty lines
                            print(f"    {line}")
            
            elif content_type == "image":
                print(f"  \033[33mContent {i+1} (image):\033[0m")
                print(f"    Image data available (type: {content_item.get('mimeType', 'unknown')})")
            
            elif content_type == "resource":
                print(f"  \033[34mContent {i+1} (resource):\033[0m")
                print(f"    Resource: {content_item.get('resource', {}).get('uri', 'unknown')}")
            
            else:
                print(f"  \033[37m❓ Content {i+1} (type: {content_type}):\033[0m")
                print(f"    {content_item}")
    
    else:
        print("  \033[37mNo content in response\033[0m")
    
    print()  # Add spacing after result

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Universal MCP Client - Test any MCP server')
    
    # Configuration file
    parser.add_argument(
        '--config-file',
        help='JSON configuration file with server, env, tools, and options'
    )
    
    # Server specification
    parser.add_argument('--server', 
                       help='MCP server command (e.g., "npx -y @modelcontextprotocol/server-google-maps")')
    
    # Environment variables
    parser.add_argument('--env', action='append', 
                       help='Environment variable as KEY=VALUE or JSON string')
    parser.add_argument('--env-file',
                       help='Load environment variables from file')
    
    # Tool execution
    parser.add_argument(
        '--tool',
        action='append',
        help='Execute specific tool (JSON format). Can be used multiple times.'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive tool selection'
    )
    
    # Operation modes
    parser.add_argument('--list-only', action='store_true',
                       help='Only list capabilities, do not execute tools')
    parser.add_argument('--verbose', action='store_true',
                       help='Show all protocol messages')

    return parser.parse_args()

def parse_env_variables(args):
    """Parse environment variables from arguments"""
    env_vars = {}
    
    # Load from file if specified
    if args.env_file:
        try:
            with open(args.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except FileNotFoundError:
            print(f"✗ Environment file not found: {args.env_file}")
            sys.exit(1)
    
    # Parse --env arguments
    if args.env:
        for env_arg in args.env:
            # Try to parse as JSON first
            try:
                json_env = json.loads(env_arg)
                if isinstance(json_env, dict):
                    env_vars.update(json_env)
                    continue
            except json.JSONDecodeError:
                pass
            
            # Parse as KEY=VALUE
            if '=' in env_arg:
                key, value = env_arg.split('=', 1)
                env_vars[key.strip()] = value.strip()
            else:
                print(f"✗ Invalid environment variable format: {env_arg}")
                sys.exit(1)
    
    return env_vars

def parse_tools(args):
    """Parse tool specifications from command line arguments"""
    tools = []
    
    if args.tool:
        for tool_str in args.tool:
            try:
                tool_data = json.loads(tool_str)
                if isinstance(tool_data, list):
                    tools.extend(tool_data)
                else:
                    tools.append(tool_data)
            except json.JSONDecodeError as e:
                print(f"✗ Invalid JSON in tool specification: {e}")
                sys.exit(1)
    
    return tools

def interactive_tool_selection(available_tools):
    """Interactive tool selection using numbered menu"""
    if not available_tools:
        print("No tools available for interactive selection.")
        return []
    
    print("\n🎯 Interactive Tool Selection")
    print("=" * 50)
    
    # Display numbered list of tools
    for i, tool in enumerate(available_tools, 1):
        tool_name = f"\033[36m{tool['name']}\033[0m"
        description = f"\033[37m{tool.get('description', 'No description')}\033[0m"
        print(f"{i:2d}. {tool_name}")
        print(f"    {description}")
    
    print("\nSelect tools by entering numbers (e.g., '1,3,5' or '1-3' or 'all'):")
    print("Press ENTER with no input to skip tool execution")
    
    while True:
        try:
            selection = input("Tools to run > ").strip()
            
            if not selection:
                print("No tools selected.")
                return []
            
            selected_indices = []
            
            if selection.lower() == 'all':
                selected_indices = list(range(len(available_tools)))
            else:
                # Parse selection (support commas and ranges)
                parts = selection.split(',')
                for part in parts:
                    part = part.strip()
                    if '-' in part:
                        # Range like "1-3"
                        start, end = map(int, part.split('-'))
                        selected_indices.extend(range(start-1, end))
                    else:
                        # Single number
                        selected_indices.append(int(part) - 1)
            
            # Validate indices
            selected_indices = [i for i in selected_indices if 0 <= i < len(available_tools)]
            if not selected_indices:
                print("No valid tools selected. Please try again.")
                continue
                
            break
            
        except ValueError:
            print("Invalid selection. Please use numbers, ranges (1-3), or 'all'.")
            continue
    
    # Get arguments for selected tools
    selected_tools = []
    for index in selected_indices:
        tool = available_tools[index]
        tool_name = tool['name']
        
        print(f"\n📝 Configure tool: \033[36m{tool_name}\033[0m")
        schema = tool.get('inputSchema', {})
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        # Show schema help
        if properties:
            print("Required parameters:")
            for param in required:
                param_info = properties.get(param, {})
                param_desc = param_info.get('description', 'No description')
                print(f"  • {param}: {param_desc}")
            
            optional = [p for p in properties.keys() if p not in required]
            if optional:
                print("Optional parameters:")
                for param in optional:
                    param_info = properties.get(param, {})
                    param_desc = param_info.get('description', 'No description')
                    print(f"  • {param}: {param_desc}")
        
        print("\nEnter arguments as JSON (or press ENTER for empty arguments):")
        print("Example: {\"query\": \"Golden Gate Bridge\"}")
        
        while True:
            try:
                args_input = input("> ").strip()
                if not args_input:
                    arguments = {}
                else:
                    arguments = json.loads(args_input)
                
                selected_tools.append({
                    "name": tool_name,
                    "arguments": arguments
                })
                break
            except json.JSONDecodeError as e:
                print(f"Invalid JSON: {e}. Please try again:")
    
    return selected_tools

def create_mcp_client(server_command, env_vars=None, verbose=False):
    """Create MCP client - extensible for future HTTP support"""
    
    # Auto-detect transport type (future-proofing)
    if server_command.startswith(('http://', 'https://')):
        raise NotImplementedError("HTTP transport not yet supported")
    
    # STDIO transport
    return create_stdio_client(server_command, env_vars, verbose)

def create_stdio_client(server_command, env_vars=None, verbose=False):
    """Create STDIO-based MCP client"""
    
    # Parse server command
    try:
        cmd_parts = shlex.split(server_command)
    except ValueError as e:
        print(f"✗ Invalid server command: {e}")
        sys.exit(1)
    
    # Prepare environment
    full_env = {**os.environ}
    if env_vars:
        full_env.update(env_vars)
    
    if verbose:
        print(f"🔧 Starting server: {' '.join(cmd_parts)}")
        if env_vars:
            print(f"🔧 Environment variables: {list(env_vars.keys())}")
    
    # Start subprocess
    try:
        proc = subprocess.Popen(
            cmd_parts,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=full_env
        )
        return proc, verbose
    except FileNotFoundError as e:
        print(f"✗ Failed to start server: {e}")
        sys.exit(1)

def send_message(proc, message, verbose=False):
    """Send a JSON-RPC message to the MCP server"""
    json_msg = json.dumps(message)
    if verbose:
        print(f"📤 Sending: {json_msg}")
    proc.stdin.write(json_msg + '\n')
    proc.stdin.flush()

def read_response(proc, verbose=False):
    """Read and parse a response from the MCP server"""
    line = proc.stdout.readline()
    if line.strip():
        response = json.loads(line.strip())
        if verbose:
            print(f"📥 Received: {response}")
        return response
    return None

def run_mcp_session(proc, verbose, tools_to_test, list_only, interactive):
    """Run the MCP session with the given parameters"""
    message_id = 1
    
    # Initialize the MCP server
    init_message = {
        "jsonrpc": "2.0",
        "id": message_id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "universal-mcp-client",
                "version": "1.0.0"
            }
        }
    }

    send_message(proc, init_message, verbose)
    init_response = read_response(proc, verbose)

    if not init_response or "result" not in init_response:
        print("✗ Failed to initialize MCP server")
        error_output = proc.stderr.read()
        if error_output:
            print("Error output:", error_output)
        return False

    print("✓ MCP server initialized successfully")
    message_id += 1
    
    # Send initialized notification
    initialized_message = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    send_message(proc, initialized_message, verbose)
    
    # List capabilities
    print("\n🔍 Discovering server capabilities...")
    
    # List tools
    list_tools_message = {
        "jsonrpc": "2.0",
        "id": message_id,
        "method": "tools/list"
    }
    send_message(proc, list_tools_message, verbose)
    tools_response = read_response(proc, verbose)
    message_id += 1

    available_tools = []
    if tools_response and "result" in tools_response:
        available_tools = tools_response["result"]["tools"]
        if not interactive:
            if available_tools:
                print("✓ Available tools:")
                for tool in available_tools:
                    tool_name = f"\033[36m{tool['name']}\033[0m"  # Cyan
                    description = f"\033[35m{tool.get('description', 'No description available')}\033[0m"  # Magenta
                    print(f"  • {tool_name}: {description}")
            else:
                print("✓ No tools available")
    else:
        print("✗ Failed to list tools")

    # List resources
    list_resources_message = {
        "jsonrpc": "2.0",
        "id": message_id,
        "method": "resources/list"
    }
    send_message(proc, list_resources_message, verbose)
    resources_response = read_response(proc, verbose)
    message_id += 1

    if resources_response and "result" in resources_response:
        resources = resources_response["result"]["resources"]
        if resources:
            print("✓ Available resources:", [resource["name"] for resource in resources])
        else:
            print("✓ No resources available")
    else:
        print("✗ Failed to list resources")

    # List prompts
    list_prompts_message = {
        "jsonrpc": "2.0",
        "id": message_id,
        "method": "prompts/list"
    }
    send_message(proc, list_prompts_message, verbose)
    prompts_response = read_response(proc, verbose)
    message_id += 1

    if prompts_response and "result" in prompts_response:
        prompts = prompts_response["result"]["prompts"]
        if prompts:
            print("✓ Available prompts:", [prompt["name"] for prompt in prompts])
        else:
            print("✓ No prompts available")
    else:
        print("✗ Failed to list prompts")

    # Interactive tool selection
    if interactive and available_tools and not list_only:
        tools_to_test = interactive_tool_selection(available_tools)

    # Execute tools if requested and not list_only
    if not list_only and tools_to_test:
        print("\n🔧 Executing requested tools...")
        
        for i, tool_spec in enumerate(tools_to_test):
            tool_name = tool_spec.get("name", "unknown")
            print(f"\n📋 Testing tool: {tool_name}")
            
            tool_message = {
                "jsonrpc": "2.0",
                "id": message_id,
                "method": "tools/call",
                "params": tool_spec
            }
            
            send_message(proc, tool_message, verbose)
            tool_response = read_response(proc, verbose)
            message_id += 1
            
            display_mcp_result(tool_response, f"Tool: {tool_name}")

    return True

def load_config_file(config_path):
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"✗ Configuration file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in configuration file: {e}")
        sys.exit(1)

def merge_config_with_args(args):
    """Merge configuration file with command line arguments - config file takes precedence"""
    config = {}
    
    # Load config file if specified
    if args.config_file:
        config = load_config_file(args.config_file)
    
    # Config file overrides CLI arguments
    # Server: config file first, then CLI
    server = config.get('server') or args.server
    if not server:
        print("✗ Server must be specified via --server or config file")
        sys.exit(1)
    
    # Environment variables: config file overrides CLI
    env_vars = {}
    if args.env or args.env_file:
        env_vars = parse_env_variables(args)
    if 'env' in config:
        env_vars = config['env']  # Config file completely replaces CLI env
    
    # Tools: config file overrides CLI
    tools = []
    if args.tool:
        tools = parse_tools(args)
    if 'tools' in config:
        tools = config['tools']  # Config file completely replaces CLI tools
    
    # Options: config file overrides CLI
    options = config.get('options', {})
    merged_options = {
        'verbose': options.get('verbose', args.verbose),
        'list_only': options.get('list_only', args.list_only),
        'interactive': options.get('interactive', args.interactive),
    }
    
    return {
        'server': server,
        'env_vars': env_vars,
        'tools': tools,
        'options': merged_options
    }

def main():
    args = parse_arguments()
    
    # Merge config file with CLI arguments
    config = merge_config_with_args(args)
    
    if not config['server']:
        print("✗ Server must be specified")
        sys.exit(1)
    
    # Use merged options (config + CLI args)
    if config['options']['verbose']:
        print(f"Starting MCP server: {config['server']}")
        if config['env_vars']:
            print(f"Environment variables: {config['env_vars']}")
    
    proc = None
    # Create MCP client
    try:
        proc, verbose = create_mcp_client(
            config['server'], 
            config['env_vars'], 
            config['options']['verbose']
        )
        
        print(f"🚀 Universal MCP Client")
        print(f"📡 Server: {config['server']}")
        if config['env_vars']:
            print(f"🔐 Environment variables: {list(config['env_vars'].keys())}")
        
        # Run the session
        success = run_mcp_session(
            proc, 
            config['options']['verbose'], 
            config['tools'], 
            config['options']['list_only'], 
            config['options']['interactive']
        )
        
        if not success:
            print("❌ Session failed")
        else:
            print("\n✅ Session completed successfully")
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        # Clean up
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                try:
                    proc.kill()
                except:
                    pass

if __name__ == "__main__":
    main()