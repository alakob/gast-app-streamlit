#!/usr/bin/env python
"""
Test script to check connectivity to the AMR API.
"""
import requests
import logging
import sys
import os

# Hard-code the API URL for testing
AMR_API_URL = "http://localhost:8000"

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("api-test")

def test_amr_api_connection():
    """Test connection to the AMR API server."""
    print(f"Testing connection to AMR API at: {AMR_API_URL}")
    
    # Test endpoints that might exist
    endpoints = ["", "/", "/health", "/status", "/api", "/docs", "/openapi.json"]
    
    for endpoint in endpoints:
        url = f"{AMR_API_URL}{endpoint}"
        try:
            print(f"Trying endpoint: {url}")
            response = requests.get(url, timeout=5)
            print(f"  Response: {response.status_code}")
            
            if response.status_code < 500:  # Allow 404 but catch server errors
                print(f"  API is responding (status code: {response.status_code})")
                if response.status_code == 200:
                    print("  Endpoint is valid and responding properly!")
                    try:
                        # Try to parse as JSON
                        content_type = response.headers.get('Content-Type', '')
                        if 'application/json' in content_type:
                            data = response.json()
                            print(f"  Response data: {data}")
                    except Exception:
                        # Not JSON or other issue
                        pass
            else:
                print(f"  Server error for this endpoint")
                
        except requests.ConnectionError:
            print(f"  Connection failed - server might be down or unreachable")
        except requests.Timeout:
            print(f"  Request timed out")
        except Exception as e:
            print(f"  Error: {str(e)}")
        
        print()  # Add a blank line between endpoint results
        
    # Test the /predict endpoint with a small payload
    test_predict_endpoint()
    
def test_predict_endpoint():
    """Test the /predict endpoint with a minimal payload."""
    url = f"{AMR_API_URL}/predict"
    print(f"Testing POST to {url}")
    
    # Minimal test payload
    data = {
        "sequence": "ATCG" * 10
    }
    
    try:
        response = requests.post(url, json=data, timeout=5)
        print(f"  Response: {response.status_code}")
        
        if response.status_code < 400:
            print("  Predict endpoint is working!")
            try:
                result = response.json()
                print(f"  Response data: {result}")
                if "job_id" in result:
                    print(f"  Success! Job ID received: {result['job_id']}")
            except Exception as e:
                print(f"  Error parsing response: {str(e)}")
        else:
            print(f"  Predict endpoint error: {response.status_code}")
            try:
                print(f"  Error details: {response.text}")
            except:
                pass
    except Exception as e:
        print(f"  Error testing predict endpoint: {str(e)}")

if __name__ == "__main__":
    test_amr_api_connection()
