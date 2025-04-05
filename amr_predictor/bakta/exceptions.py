#!/usr/bin/env python3
"""
Exceptions for Bakta integration module.

This module defines custom exceptions for the Bakta integration module.
"""

class BaktaException(Exception):
    """Base exception for Bakta integration errors."""
    pass

class BaktaApiError(BaktaException):
    """Exception raised for errors related to the Bakta API."""
    pass

class BaktaNetworkError(BaktaApiError):
    """Exception raised for network-related errors when interacting with the Bakta API."""
    pass

class BaktaResponseError(BaktaApiError):
    """Exception raised for invalid or error responses from the Bakta API."""
    pass

class BaktaAuthenticationError(BaktaApiError):
    """Exception raised for authentication failures with the Bakta API."""
    pass

class BaktaResourceNotFoundError(BaktaApiError):
    """Exception raised when a requested resource is not found in the Bakta API."""
    pass

class BaktaValidationError(BaktaException):
    """Exception raised for validation errors in Bakta inputs or responses."""
    pass

class BaktaJobError(BaktaException):
    """Exception raised for errors in Bakta job processing."""
    pass

class BaktaDatabaseError(BaktaException):
    """Exception raised for database errors in Bakta integration."""
    pass

class BaktaParseError(BaktaException):
    """Exception raised for errors in parsing Bakta results."""
    pass

class BaktaConfigError(BaktaException):
    """Exception raised for configuration errors in Bakta integration."""
    pass

class BaktaManagerError(BaktaException):
    """Exception raised for errors in the BaktaManager."""
    pass

class BaktaClientError(BaktaException):
    """Exception raised for errors in the BaktaClient."""
    pass

class BaktaParserError(BaktaException):
    """Exception raised for errors in the Bakta parsers."""
    pass

class BaktaStorageError(BaktaException):
    """Exception raised for errors in the BaktaStorageService."""
    pass 