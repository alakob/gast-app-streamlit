#!/usr/bin/env python
"""
Script to run the AMR Predictor FastAPI server.
"""
import os
import sys
import logging
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("amr-server")

def main():
    """
    Main function to start the AMR FastAPI server.
    """
    logger.info("Starting AMR Predictor FastAPI server")
    
    # Ensure the module can be found in the Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Set host and port
    host = os.environ.get("AMR_API_HOST", "0.0.0.0")
    port = int(os.environ.get("AMR_API_PORT", "8000"))
    
    logger.info(f"Server will be available at http://{host}:{port}")
    logger.info("Press Ctrl+C to stop the server")
    
    # Start the FastAPI server
    uvicorn.run(
        "amr_predictor.web.api:app",
        host=host,
        port=port,
        reload=True  # Enable auto-reload for development
    )

if __name__ == "__main__":
    main()
