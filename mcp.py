import subprocess
import json
import time
import os
import argparse
import shlex
import sys
from urllib.parse import urlparse

# MCP Protocol Configuration
MCP_PROTOCOL_VERSION = "2025-06-18"

# Try to import requests, install if not available
try:
    import requests
except ImportError:
    print("Installing requests library...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
    import requests

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

class HttpMcpClient:
    """Simple HTTP-based MCP client using requests"""
    
    def __init__(self, base_url, headers=None, verbose=False):
        self.base_url = base_url.rstrip('/')
        self.headers = headers or {}
        self.verbose = verbose
        self.session_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            **self.headers
        }
        
    def send_request(self, message):
        """Send HTTP request to MCP server"""
        try:
            if self.verbose:
                print(f"→ HTTP POST {self.base_url}")
                print(f"→ Headers: {json.dumps(self.session_headers, indent=2)}")
                print(f"→ Body: {json.dumps(message, indent=2)}")
            
            # Use the URL exactly as provided - don't append /mcp
            response = requests.post(
                self.base_url,
                json=message,
                headers=self.session_headers,
                timeout=30
            )
            
            if self.verbose:
                print(f"← HTTP {response.status_code}")
                print(f"← {response.text}")
            
            response.raise_for_status()  # Raise exception for bad status codes
            return response.json()
                
        except requests.exceptions.RequestException as e:
            print(f"✗ HTTP Request Error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON response: {e}")
            return None
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            return None

def is_http_server(server_command):
    """Check if server command is an HTTP URL"""
    try:
        parsed = urlparse(server_command)
        return parsed.scheme in ('http', 'https') and parsed.netloc
    except:
        return False

def create_mcp_client(server_command, env_vars=None, verbose=False):
    """Create MCP client - automatically detects STDIO vs HTTP"""
    if is_http_server(server_command):
        return create_http_client(server_command, env_vars, verbose)
    else:
        return create_stdio_client(server_command, env_vars, verbose)

def create_http_client(base_url, env_vars=None, verbose=False):
    """Create HTTP-based MCP client"""
    if verbose:
        print(f"Creating HTTP MCP client for: {base_url}")
    
    # Convert env_vars to HTTP headers if provided
    headers = {}
    if env_vars:
        # Common patterns for API keys in headers
        for key, value in env_vars.items():
            if key.upper().endswith('_API_KEY'):
                headers[f'X-API-Key'] = value
            elif key.upper() == 'AUTHORIZATION':
                headers['Authorization'] = value
            elif key.upper().startswith('X-'):
                headers[key] = value
    
    client = HttpMcpClient(base_url, headers, verbose)
    return client, verbose

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

def send_message(client, message, verbose=False):
    """Send message to MCP server (works with both STDIO and HTTP clients)"""
    if hasattr(client, 'send_request'):
        # HTTP client - no separate send needed, handled in send_request
        pass  
    else:
        # STDIO client
        message_json = json.dumps(message) + '\n'
        if verbose:
            print(f"→ {json.dumps(message, indent=2)}")
        client.stdin.write(message_json)
        client.stdin.flush()

def read_response(client, verbose=False):
    """Read response from MCP server (works with both STDIO and HTTP clients)"""
    if hasattr(client, 'send_request'):
        # HTTP client - response already handled in send_request
        return None  # HTTP responses are handled synchronously
    else:
        # STDIO client
        try:
            line = client.stdout.readline()
            if not line:
                return None
            response = json.loads(line.strip())
            if verbose:
                print(f"← {json.dumps(response, indent=2)}")
            return response
        except json.JSONDecodeError:
            return None
        except Exception:
            return None

def send_and_receive(client, message, verbose=False):
    """Send message and receive response (unified interface for STDIO and HTTP)"""
    if hasattr(client, 'send_request'):
        # HTTP client
        return client.send_request(message)
    else:
        # STDIO client  
        send_message(client, message, verbose)
        return read_response(client, verbose)

def run_mcp_session(client, verbose, tools_to_test, list_only, interactive):
    """Run an MCP session with capability discovery and tool execution"""
    message_id = 1
    
    # Initialize the session
    print("🔗 Initializing MCP session...")
    
    # Send initialization message
    init_message = {
        "jsonrpc": "2.0",
        "id": message_id,
        "method": "initialize",
        "params": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "universal-mcp-client",
                "version": "1.0.0"
            }
        }
    }

    init_response = send_and_receive(client, init_message, verbose)
    message_id += 1

    if not init_response or "result" not in init_response:
        print("✗ Failed to initialize MCP session")
        return False

    print("✓ MCP session initialized")

    # Send initialized notification
    initialized_message = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    send_message(client, initialized_message, verbose)  # Notifications don't expect responses

    # Only discover capabilities in list-only mode
    available_tools = []
    if list_only:
        # List capabilities
        print("\n🔍 Discovering server capabilities...")

        # List tools
        list_tools_message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "tools/list"
        }
        tools_response = send_and_receive(client, list_tools_message, verbose)
        message_id += 1

        if tools_response and "result" in tools_response:
            available_tools = tools_response["result"]["tools"]
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
        resources_response = send_and_receive(client, list_resources_message, verbose)
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
        prompts_response = send_and_receive(client, list_prompts_message, verbose)
        message_id += 1

        if prompts_response and "result" in prompts_response:
            prompts = prompts_response["result"]["prompts"]
            if prompts:
                print("✓ Available prompts:", [prompt["name"] for prompt in prompts])
            else:
                print("✓ No prompts available")
        else:
            print("✗ Failed to list prompts")

    # Interactive tool selection (only if not list_only and interactive)
    elif interactive:
        # Need to get tools for interactive mode
        list_tools_message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "tools/list"
        }
        tools_response = send_and_receive(client, list_tools_message, verbose)
        message_id += 1

        if tools_response and "result" in tools_response:
            available_tools = tools_response["result"]["tools"]
            if available_tools:
                tools_to_test = interactive_tool_selection(available_tools)
            else:
                print("✓ No tools available for interactive selection")
        else:
            print("✗ Failed to list tools for interactive mode")

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
            
            tool_response = send_and_receive(client, tool_message, verbose)
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
    
    client = None
    # Create MCP client
    try:
        client, verbose = create_mcp_client(
            config['server'], 
            config['env_vars'], 
            config['options']['verbose']
        )
        
        print(f"🚀 Universal MCP Client")
        print(f"📡 Server: {config['server']}")
        if config['env_vars']:
            if is_http_server(config['server']):
                print(f"🔐 HTTP Headers: {list(getattr(client, 'headers', {}).keys())}")
            else:
                print(f"🔐 Environment variables: {list(config['env_vars'].keys())}")
        
        # Run the session
        success = run_mcp_session(
            client, 
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
        if client:
            try:
                # Only terminate STDIO processes (HTTP clients don't need cleanup)
                if hasattr(client, 'terminate'):
                    client.terminate()
                    client.wait(timeout=5)
            except:
                try:
                    if hasattr(client, 'kill'):
                        client.kill()
                except:
                    pass

if __name__ == "__main__":
    main()