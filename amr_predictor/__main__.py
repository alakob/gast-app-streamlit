"""
Main entry point for AMR Predictor.

This module provides the main entry point for the AMR Predictor package,
allowing it to be run as a module.
"""

import sys
import os
import uvicorn

from .cli.commands import main as cli_main


def main():
    """
    Main entry point for the AMR Predictor package.
    
    This function handles command-line arguments and dispatches to the appropriate
    functionality based on the arguments provided.
    """
    # Check if we're trying to run the web server
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        # Remove the 'web' argument
        sys.argv.pop(1)
        
        # Default values
        host = "127.0.0.1"
        port = 8000
        
        # Process remaining arguments
        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i]
            
            if arg == "--host" and i + 1 < len(sys.argv):
                host = sys.argv[i + 1]
                i += 2
            elif arg == "--port" and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    print(f"Invalid port number: {sys.argv[i + 1]}")
                    sys.exit(1)
                i += 2
            else:
                i += 1
        
        # Import the app only when needed to avoid unnecessary imports
        from .web.api import app
        
        # Run the web server
        uvicorn.run(app, host=host, port=port)
    else:
        # Run the CLI
        cli_main()


if __name__ == "__main__":
    main() 