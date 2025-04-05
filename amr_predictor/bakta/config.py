#!/usr/bin/env python3
"""
Configuration module for Bakta API client.

This module provides default configuration values and helper
functions for configuring Bakta API interactions.
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dotenv import load_dotenv

from amr_predictor.bakta.exceptions import BaktaException

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Default configuration for Bakta annotation jobs
DEFAULT_CONFIG = {
    "completeGenome": False,
    "compliant": True,
    "dermType": None,
    "genus": "Unspecified",
    "hasReplicons": False,
    "keepContigHeaders": True,
    "locus": "LOCUS",
    "locusTag": "LOCUS",
    "minContigLength": 0,
    "plasmid": "",
    "prodigalTrainingFile": None,
    "species": "Unspecified",
    "strain": "STRAIN",
    "translationTable": 11
}

# Environment-specific API URLs
API_URLS = {
    "prod": os.environ.get("BAKTA_API_URL_PROD", "https://api.bakta.computational.bio/api/v1"),
    "staging": os.environ.get("BAKTA_API_URL_STAGING", "https://api.staging.bakta.computational.bio/api/v1"),
    "dev": os.environ.get("BAKTA_API_URL_DEV", "https://api.dev.bakta.computational.bio/api/v1"),
    "local": os.environ.get("BAKTA_API_URL_LOCAL", "http://localhost:8000/api/v1")
}

# Default API key (from environment)
DEFAULT_API_KEY = os.environ.get("BAKTA_API_KEY", "")

# Common configuration presets for different types of organisms
CONFIGURATION_PRESETS = {
    "default": DEFAULT_CONFIG,
    
    "gram_positive": {
        **DEFAULT_CONFIG,
        "dermType": "MONODERM"
    },
    
    "gram_negative": {
        **DEFAULT_CONFIG,
        "dermType": "DIDERM"
    },
    
    "complete_genome": {
        **DEFAULT_CONFIG,
        "completeGenome": True
    },
    
    "draft_genome": {
        **DEFAULT_CONFIG,
        "completeGenome": False
    },
    
    "escherichia_coli": {
        **DEFAULT_CONFIG,
        "genus": "Escherichia",
        "species": "coli",
        "dermType": "DIDERM",
        "translationTable": 11
    },
    
    "staphylococcus_aureus": {
        **DEFAULT_CONFIG,
        "genus": "Staphylococcus",
        "species": "aureus",
        "dermType": "MONODERM",
        "translationTable": 11
    }
}

def get_api_url(environment: str = "prod") -> str:
    """
    Get the API URL for the specified environment
    
    Args:
        environment: Environment name ('prod', 'staging', 'dev', or 'local')
        
    Returns:
        API URL for the specified environment
        
    Raises:
        BaktaException: If the environment is not recognized
    """
    # First check for environment-specific override from environment variables
    env_var_name = f"BAKTA_API_URL_{environment.upper()}"
    env_override = os.environ.get(env_var_name)
    if env_override:
        return env_override
    
    # Otherwise check the API_URLS dictionary
    if environment not in API_URLS:
        valid_envs = ", ".join(API_URLS.keys())
        raise BaktaException(f"Invalid environment: {environment}. Must be one of: {valid_envs}")
    
    return API_URLS[environment]

def get_bakta_api_config(environment: str = "prod") -> Dict[str, Any]:
    """
    Get the Bakta API configuration for the specified environment
    
    Args:
        environment: Environment name ('prod', 'staging', 'dev', or 'local')
        
    Returns:
        Dictionary with API configuration including URL and key
    """
    url = get_api_url(environment)
    api_key = os.environ.get(f"BAKTA_API_KEY_{environment.upper()}", DEFAULT_API_KEY)
    
    return {
        "url": url,
        "api_key": api_key,
        "environment": environment
    }

def set_bakta_api_url(url: str, environment: str = "prod") -> None:
    """
    Set the Bakta API URL for the specified environment
    
    Args:
        url: API URL to set
        environment: Environment name ('prod', 'staging', 'dev', or 'local')
    """
    global API_URLS
    API_URLS[environment] = url
    
    # Also set in environment for this session
    os.environ[f"BAKTA_API_URL_{environment.upper()}"] = url
    logger.info(f"Set Bakta API URL for {environment} environment to {url}")

def set_bakta_api_key(api_key: str, environment: str = "prod") -> None:
    """
    Set the Bakta API key for the specified environment
    
    Args:
        api_key: API key to set
        environment: Environment name ('prod', 'staging', 'dev', or 'local')
    """
    global DEFAULT_API_KEY
    if environment == "prod":
        DEFAULT_API_KEY = api_key
    
    # Set in environment for this session
    os.environ[f"BAKTA_API_KEY_{environment.upper()}"] = api_key
    logger.info(f"Set Bakta API key for {environment} environment")

def get_bakta_job_config(preset: str = None, **kwargs) -> Dict[str, Any]:
    """
    Get a job configuration for Bakta annotation
    
    Args:
        preset: Preset configuration name (optional)
        **kwargs: Additional configuration parameters
        
    Returns:
        Job configuration dictionary
    """
    return create_config(preset=preset, **kwargs)

def create_config(
    genus: str = None,
    species: str = None,
    strain: str = None,
    locus: str = None,
    locus_tag: str = None,
    complete_genome: bool = None,
    keep_contig_headers: bool = None,
    min_contig_length: int = None,
    translation_table: int = None,
    derm_type: str = None,
    preset: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a configuration dictionary with the provided values, using defaults for missing values
    
    Args:
        genus: Genus name
        species: Species name
        strain: Strain name
        locus: Locus name
        locus_tag: Locus tag
        complete_genome: Whether the genome is complete
        keep_contig_headers: Whether to keep contig headers
        min_contig_length: Minimum contig length
        translation_table: Translation table number
        derm_type: Type of cell membrane ('UNKNOWN', 'MONODERM', or 'DIDERM')
        preset: Name of a configuration preset to use as base
        **kwargs: Additional configuration parameters
        
    Returns:
        Configuration dictionary
        
    Raises:
        BaktaException: If the preset is not found
    """
    # Start with the preset if specified, otherwise use default config
    if preset:
        if preset in CONFIGURATION_PRESETS:
            config = CONFIGURATION_PRESETS[preset].copy()
        else:
            valid_presets = ", ".join(CONFIGURATION_PRESETS.keys())
            raise BaktaException(f"Invalid preset: {preset}. Must be one of: {valid_presets}")
    else:
        config = DEFAULT_CONFIG.copy()
    
    # Update with provided values if not None
    if genus is not None:
        config["genus"] = genus
    if species is not None:
        config["species"] = species
    if strain is not None:
        config["strain"] = strain
    if locus is not None:
        config["locus"] = locus
    if locus_tag is not None:
        config["locusTag"] = locus_tag
    if complete_genome is not None:
        config["completeGenome"] = complete_genome
    if keep_contig_headers is not None:
        config["keepContigHeaders"] = keep_contig_headers
    if min_contig_length is not None:
        config["minContigLength"] = min_contig_length
    if translation_table is not None:
        config["translationTable"] = translation_table
    if derm_type is not None:
        config["dermType"] = derm_type
    
    # Update with any additional parameters
    for key, value in kwargs.items():
        if value is not None:
            # Convert snake_case to camelCase for API compatibility
            api_key = key
            if "_" in key:
                parts = key.split("_")
                api_key = parts[0] + "".join(p.capitalize() for p in parts[1:])
            config[api_key] = value
    
    return config

def load_config_from_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load configuration from a JSON or YAML file
    
    Args:
        file_path: Path to the configuration file (JSON or YAML)
        
    Returns:
        Configuration dictionary
        
    Raises:
        BaktaException: If the file does not exist, format is not recognized, or content is invalid
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise BaktaException(f"Configuration file not found: {file_path}")
    
    # Determine file format from extension
    if file_path.suffix.lower() in ['.json']:
        with open(file_path, 'r') as f:
            try:
                config_data = json.load(f)
            except json.JSONDecodeError as e:
                raise BaktaException(f"Invalid JSON in configuration file: {str(e)}")
    elif file_path.suffix.lower() in ['.yaml', '.yml']:
        with open(file_path, 'r') as f:
            try:
                config_data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise BaktaException(f"Invalid YAML in configuration file: {str(e)}")
    else:
        raise BaktaException(f"Unsupported configuration file format: {file_path.suffix}. Use .json, .yaml, or .yml")
    
    # Validate the loaded configuration
    if not isinstance(config_data, dict):
        raise BaktaException("Configuration file must contain a JSON/YAML object (dictionary)")
    
    # Merge with default configuration
    config = DEFAULT_CONFIG.copy()
    config.update(config_data)
    
    return config

def save_config_to_file(config: Dict[str, Any], file_path: Union[str, Path], format: str = 'json') -> None:
    """
    Save configuration to a file
    
    Args:
        config: Configuration dictionary to save
        file_path: Path to save the configuration file
        format: Format to save the file in ('json' or 'yaml')
        
    Raises:
        BaktaException: If the format is not supported
    """
    file_path = Path(file_path)
    
    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save in the specified format
    if format.lower() == 'json':
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=2)
    elif format.lower() in ['yaml', 'yml']:
        with open(file_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    else:
        raise BaktaException(f"Unsupported configuration file format: {format}. Use 'json' or 'yaml'")

def get_available_presets() -> List[str]:
    """
    Get a list of available configuration presets
    
    Returns:
        List of preset names
    """
    return list(CONFIGURATION_PRESETS.keys())

def get_preset_config(preset_name: str) -> Dict[str, Any]:
    """
    Get a configuration preset by name
    
    Args:
        preset_name: Name of the preset
        
    Returns:
        Configuration dictionary
        
    Raises:
        BaktaException: If the preset is not found
    """
    if preset_name not in CONFIGURATION_PRESETS:
        valid_presets = ", ".join(CONFIGURATION_PRESETS.keys())
        raise BaktaException(f"Invalid preset: {preset_name}. Must be one of: {valid_presets}")
    
    return CONFIGURATION_PRESETS[preset_name].copy()

def get_environment_config(environment: str = "prod") -> Dict[str, Any]:
    """
    Get environment-specific configuration
    
    Args:
        environment: Environment name ('prod', 'staging', 'dev', or 'local')
        
    Returns:
        Environment configuration dictionary
        
    Raises:
        BaktaException: If the environment is not recognized
    """
    api_url = get_api_url(environment)
    api_key = os.environ.get(f"BAKTA_API_KEY_{environment.upper()}", os.environ.get("BAKTA_API_KEY", ""))
    
    return {
        "environment": environment,
        "api_url": api_url,
        "api_key": api_key
    }

def create_config_from_env() -> Dict[str, Any]:
    """
    Create a job configuration from environment variables
    
    Returns:
        Configuration dictionary based on environment variables
    """
    config = DEFAULT_CONFIG.copy()
    
    # Check for environment variables with BAKTA_CONFIG_ prefix
    for key, value in os.environ.items():
        if key.startswith("BAKTA_CONFIG_"):
            config_key = key[len("BAKTA_CONFIG_"):].lower()
            
            # Convert snake_case to camelCase for API compatibility
            if "_" in config_key:
                parts = config_key.split("_")
                config_key = parts[0] + "".join(p.capitalize() for p in parts[1:])
            
            # Convert value to appropriate type
            if value.lower() in ["true", "yes", "1"]:
                config[config_key] = True
            elif value.lower() in ["false", "no", "0"]:
                config[config_key] = False
            elif value.isdigit():
                config[config_key] = int(value)
            elif value.lower() == "none":
                config[config_key] = None
            else:
                config[config_key] = value
    
    return config 