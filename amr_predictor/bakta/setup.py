"""Setup for the Bakta module."""

from setuptools import setup, find_packages

setup(
    name="amr_predictor_bakta",
    version="1.0.0",
    description="Bakta Annotation Integration for AMR Predictor",
    author="AMR Team",
    packages=["bakta"],
    package_dir={"bakta": "."},
    install_requires=[
        "psycopg2-binary>=2.9.0",
        "pandas>=1.3.0",
        "aiohttp>=3.8.0",
        "biopython>=1.79",
    ],
)
