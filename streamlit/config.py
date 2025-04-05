"""
Configuration settings for the AMR Streamlit app.
"""
import os
from pathlib import Path

# Base project directory
BASE_DIR = Path(__file__).parent.parent

# API URLs and Keys
AMR_API_URL = os.environ.get("AMR_API_URL", "http://localhost:8000")
AMR_API_KEY = os.environ.get("AMR_API_KEY", "")

# Bakta configuration
BAKTA_API_URL = os.environ.get("BAKTA_API_URL", "https://api.bakta.computational.bio")
BAKTA_API_KEY = os.environ.get("BAKTA_API_KEY", "")
BAKTA_ENVIRONMENT = os.environ.get("BAKTA_ENVIRONMENT", "prod")

# Default parameters
DEFAULT_TRANSLATION_TABLE = 11
DEFAULT_GENUS = "Escherichia"
DEFAULT_SPECIES = "coli"
DEFAULT_TIMEOUT = 300  # seconds

# UI Configuration
APP_TITLE = "AMR Prediction & Genome Annotation"
APP_DESCRIPTION = "Predict antimicrobial resistance and annotate bacterial genomes"
MAX_UPLOAD_SIZE = 50  # MB

# Sample data
SAMPLE_SEQUENCE_PATH = os.path.join(BASE_DIR, "datasets", "test.fasta")
