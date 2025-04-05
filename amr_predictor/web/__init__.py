"""
Web package for AMR Predictor.

This package provides web interfaces for the AMR Predictor functionality,
including REST API endpoints for integration with web applications.
"""

from .api import app

__all__ = ["app"]
