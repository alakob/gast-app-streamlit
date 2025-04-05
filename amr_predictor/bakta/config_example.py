#!/usr/bin/env python3
"""
Configuration management example for the Bakta API client.

This script demonstrates how to use the configuration management capabilities
of the Bakta API client.
"""

import os
import sys
import json
from pathlib import Path
from amr_predictor.bakta.config import (
    create_config,
    load_config_from_file,
    save_config_to_file,
    get_api_url,
    get_available_presets,
    get_preset_config,
    get_environment_config,
    create_config_from_env,
    DEFAULT_CONFIG,
    CONFIGURATION_PRESETS
)

def basic_config_example():
    """Basic configuration example"""
    print("\n=== Basic Configuration Example ===")
    
    # Create a simple configuration
    config = create_config(
        genus="Escherichia",
        species="coli",
        strain="K-12",
        locus="ECO",
        locus_tag="ECO",
        translation_table=11
    )
    
    print("Basic configuration:")
    print(json.dumps(config, indent=2))

def preset_config_example():
    """Preset configuration example"""
    print("\n=== Preset Configuration Example ===")
    
    # Get available presets
    presets = get_available_presets()
    print(f"Available presets: {', '.join(presets)}")
    
    # Use a preset configuration
    config = create_config(
        preset="escherichia_coli",
        strain="K-12",
        locus="ECO",
        locus_tag="ECO"
    )
    
    print("Configuration using 'escherichia_coli' preset:")
    print(json.dumps(config, indent=2))

def environment_config_example():
    """Environment-specific configuration example"""
    print("\n=== Environment Configuration Example ===")
    
    # Get API URL for different environments
    environments = ["prod", "staging", "dev", "local"]
    
    print("API URLs for different environments:")
    for env in environments:
        try:
            api_url = get_api_url(env)
            print(f"  {env}: {api_url}")
        except ValueError as e:
            print(f"  {env}: Error - {str(e)}")
    
    # Get environment configuration
    env_config = get_environment_config("prod")
    print("\nEnvironment configuration for 'prod':")
    print(json.dumps(env_config, indent=2))

def file_config_example():
    """File-based configuration example"""
    print("\n=== File-based Configuration Example ===")
    
    # Create a configuration to save
    config = create_config(
        preset="gram_negative",
        genus="Pseudomonas",
        species="aeruginosa",
        strain="PAO1",
        locus="PA",
        locus_tag="PA",
        complete_genome=True
    )
    
    # Save to JSON and YAML files
    examples_dir = Path("bakta_config_examples")
    examples_dir.mkdir(exist_ok=True)
    
    json_path = examples_dir / "pseudomonas.json"
    yaml_path = examples_dir / "pseudomonas.yaml"
    
    save_config_to_file(config, json_path, format='json')
    save_config_to_file(config, yaml_path, format='yaml')
    
    print(f"Saved configuration to {json_path} and {yaml_path}")
    
    # Load from JSON file
    loaded_config = load_config_from_file(json_path)
    print("\nLoaded configuration from JSON file:")
    print(json.dumps(loaded_config, indent=2))

def env_var_config_example():
    """Environment variable configuration example"""
    print("\n=== Environment Variable Configuration Example ===")
    
    # Set some environment variables (for demonstration purposes)
    # In a real application, these would be set in the environment before running the script
    os.environ["BAKTA_GENUS"] = "Salmonella"
    os.environ["BAKTA_SPECIES"] = "enterica"
    os.environ["BAKTA_STRAIN"] = "Typhimurium"
    os.environ["BAKTA_LOCUS"] = "STM"
    os.environ["BAKTA_LOCUS_TAG"] = "STM"
    os.environ["BAKTA_COMPLETE_GENOME"] = "true"
    os.environ["BAKTA_TRANSLATION_TABLE"] = "11"
    
    # Get configuration from environment variables
    config = create_config_from_env()
    
    print("Configuration from environment variables:")
    print(json.dumps(config, indent=2))
    
    # Clean up environment variables
    for var in ["BAKTA_GENUS", "BAKTA_SPECIES", "BAKTA_STRAIN", "BAKTA_LOCUS", 
                "BAKTA_LOCUS_TAG", "BAKTA_COMPLETE_GENOME", "BAKTA_TRANSLATION_TABLE"]:
        if var in os.environ:
            del os.environ[var]

def custom_api_url_example():
    """Custom API URL example"""
    print("\n=== Custom API URL Example ===")
    
    # Set a custom API URL via environment variable
    os.environ["BAKTA_API_URL_CUSTOM"] = "https://my-custom-bakta-api.example.com/api/v1"
    
    # Get the custom API URL
    try:
        custom_url = get_api_url("custom")
        print(f"Custom API URL: {custom_url}")
    except ValueError as e:
        print(f"Error: {str(e)}")
    
    # Clean up environment variable
    del os.environ["BAKTA_API_URL_CUSTOM"]

def combined_config_example():
    """Combined configuration example"""
    print("\n=== Combined Configuration Example ===")
    
    # Set some environment variables
    os.environ["BAKTA_GENUS"] = "Mycobacterium"
    os.environ["BAKTA_SPECIES"] = "tuberculosis"
    
    # Start with environment configuration
    env_config = create_config_from_env()
    
    # Override with preset values
    preset_config = get_preset_config("gram_positive")
    combined_config = {**env_config, **preset_config}
    
    # Override with specific parameters
    final_config = create_config(
        strain="H37Rv",
        locus="Rv",
        locus_tag="Rv",
        complete_genome=True,
        **combined_config
    )
    
    print("Final combined configuration:")
    print(json.dumps(final_config, indent=2))
    
    # Clean up environment variables
    for var in ["BAKTA_GENUS", "BAKTA_SPECIES"]:
        if var in os.environ:
            del os.environ[var]

def main():
    """Run the configuration examples"""
    print("=== Bakta API Client Configuration Examples ===")
    
    try:
        # Run the examples
        basic_config_example()
        preset_config_example()
        environment_config_example()
        file_config_example()
        env_var_config_example()
        custom_api_url_example()
        combined_config_example()
        
        print("\nAll examples completed!")
    except Exception as e:
        print(f"Unexpected error in main: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 