#!/usr/bin/env python3
"""
Command-line interface for the Bakta annotation service.

This module provides a CLI for submitting jobs to Bakta,
retrieving results, and querying annotations.
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from amr_predictor.bakta import (
    get_interface,
    BaktaUnifiedInterface,
    QueryOptions,
    SortOrder,
    FilterOperator,
    LogicalOperator
)
from amr_predictor.bakta.models import JobStatus
from amr_predictor.bakta.exceptions import BaktaException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bakta-cli")

def setup_submit_parser(subparsers):
    """Add submit command parser."""
    parser = subparsers.add_parser(
        "submit",
        help="Submit a new annotation job to Bakta"
    )
    parser.add_argument(
        "fasta_file",
        type=str,
        help="Path to the FASTA file to annotate"
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Job name (defaults to filename)"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for job completion"
    )
    parser.add_argument(
        "--polling-interval",
        type=int,
        default=30,
        help="Polling interval in seconds when waiting (default: 30)"
    )
    return parser

def setup_status_parser(subparsers):
    """Add status command parser."""
    parser = subparsers.add_parser(
        "status",
        help="Check the status of a Bakta job"
    )
    parser.add_argument(
        "job_id",
        type=str,
        help="Job ID to check"
    )
    return parser

def setup_download_parser(subparsers):
    """Add download command parser."""
    parser = subparsers.add_parser(
        "download",
        help="Download results from a completed Bakta job"
    )
    parser.add_argument(
        "job_id",
        type=str,
        help="Job ID to download results from"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Directory to save results (default: current directory)"
    )
    parser.add_argument(
        "--import",
        dest="import_results",
        action="store_true",
        help="Import results into the database after download"
    )
    return parser

def setup_import_parser(subparsers):
    """Add import command parser."""
    parser = subparsers.add_parser(
        "import",
        help="Import Bakta results into the database"
    )
    parser.add_argument(
        "job_id",
        type=str,
        help="Job ID for the results"
    )
    parser.add_argument(
        "--gff",
        type=str,
        required=True,
        help="Path to the GFF3 file"
    )
    parser.add_argument(
        "--json",
        type=str,
        required=True,
        help="Path to the JSON file"
    )
    return parser

def setup_query_parser(subparsers):
    """Add query command parser."""
    parser = subparsers.add_parser(
        "query",
        help="Query annotations in the database"
    )
    parser.add_argument(
        "job_id",
        type=str,
        help="Job ID to query"
    )
    parser.add_argument(
        "--feature-type",
        type=str,
        help="Filter by feature type (e.g., CDS, tRNA)"
    )
    parser.add_argument(
        "--contig",
        type=str,
        help="Filter by contig name"
    )
    parser.add_argument(
        "--region",
        type=str,
        help="Query by genomic region (format: start-end)"
    )
    parser.add_argument(
        "--attribute",
        type=str,
        action="append",
        help="Filter by attribute (format: name=value)"
    )
    parser.add_argument(
        "--sort-by",
        type=str,
        choices=["start", "end", "strand", "feature_type", "feature_id"],
        default="start",
        help="Sort results by field (default: start)"
    )
    parser.add_argument(
        "--sort-order",
        type=str,
        choices=["asc", "desc"],
        default="asc",
        help="Sort order (default: asc)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)"
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Result offset for pagination (default: 0)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "table"],
        default="table",
        help="Output format (default: table)"
    )
    return parser

def setup_list_jobs_parser(subparsers):
    """Add list-jobs command parser."""
    parser = subparsers.add_parser(
        "list-jobs",
        help="List jobs in the database"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of jobs to list (default: 10)"
    )
    return parser

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Bakta genome annotation command-line interface"
    )
    
    # Global options
    parser.add_argument(
        "--api-key",
        type=str,
        help="Bakta API key (can also use BAKTA_API_KEY env var)"
    )
    parser.add_argument(
        "--database",
        type=str,
        help="Path to the SQLite database (can also use BAKTA_DB_PATH env var)"
    )
    parser.add_argument(
        "--environment",
        type=str,
        choices=["dev", "test", "prod"],
        default="prod",
        help="Environment to use (default: prod)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Setup command parsers
    setup_submit_parser(subparsers)
    setup_status_parser(subparsers)
    setup_download_parser(subparsers)
    setup_import_parser(subparsers)
    setup_query_parser(subparsers)
    setup_list_jobs_parser(subparsers)
    
    return parser.parse_args()

async def handle_submit(args, interface: BaktaUnifiedInterface):
    """Handle submit command."""
    fasta_path = Path(args.fasta_file)
    if not fasta_path.exists():
        logger.error(f"FASTA file not found: {fasta_path}")
        return 1
    
    job_name = args.name if args.name else fasta_path.stem
    
    try:
        job_id = await interface.submit_job(
            fasta_file=fasta_path,
            job_name=job_name
        )
        print(f"Job submitted successfully with ID: {job_id}")
        
        if args.wait:
            print(f"Waiting for job completion (polling every {args.polling_interval} seconds)...")
            status = await interface.wait_for_job(
                job_id=job_id,
                polling_interval=args.polling_interval
            )
            print(f"Job completed with status: {status}")
        
        return 0
    except BaktaException as e:
        logger.error(f"Failed to submit job: {e}")
        return 1

async def handle_status(args, interface: BaktaUnifiedInterface):
    """Handle status command."""
    try:
        status = await interface.get_job_status(args.job_id)
        print(f"Job {args.job_id} status: {status}")
        
        if status == JobStatus.COMPLETED:
            job = await interface.get_job(args.job_id)
            if job and job.completed_at:
                print(f"Completed at: {job.completed_at}")
        elif status == JobStatus.RUNNING:
            job = await interface.get_job(args.job_id)
            if job and job.started_at:
                print(f"Started at: {job.started_at}")
        
        return 0
    except BaktaException as e:
        logger.error(f"Failed to get job status: {e}")
        return 1

async def handle_download(args, interface: BaktaUnifiedInterface):
    """Handle download command."""
    try:
        output_dir = Path(args.output_dir)
        if not output_dir.exists():
            output_dir.mkdir(parents=True)
        
        print(f"Downloading results for job {args.job_id} to {output_dir}...")
        result_files = await interface.download_results(
            job_id=args.job_id,
            output_dir=str(output_dir)
        )
        
        print("Downloaded files:")
        for file_type, file_path in result_files.items():
            print(f"  - {file_type}: {file_path}")
        
        if args.import_results and "gff3" in result_files and "json" in result_files:
            print("Importing results into database...")
            count = await interface.import_results(
                job_id=args.job_id,
                gff_file=result_files["gff3"],
                json_file=result_files["json"]
            )
            print(f"Imported {count} annotations")
        
        return 0
    except BaktaException as e:
        logger.error(f"Failed to download results: {e}")
        return 1

async def handle_import(args, interface: BaktaUnifiedInterface):
    """Handle import command."""
    try:
        gff_path = Path(args.gff)
        json_path = Path(args.json)
        
        if not gff_path.exists():
            logger.error(f"GFF file not found: {gff_path}")
            return 1
        
        if not json_path.exists():
            logger.error(f"JSON file not found: {json_path}")
            return 1
        
        print(f"Importing results for job {args.job_id}...")
        count = await interface.import_results(
            job_id=args.job_id,
            gff_file=str(gff_path),
            json_file=str(json_path)
        )
        
        print(f"Successfully imported {count} annotations")
        return 0
    except BaktaException as e:
        logger.error(f"Failed to import results: {e}")
        return 1

def format_annotation_table(annotations):
    """Format annotations as a table."""
    if not annotations:
        return "No annotations found"
    
    # Define columns
    columns = ["feature_id", "feature_type", "contig", "start", "end", "strand"]
    
    # Get max width for each column
    widths = {col: len(col) for col in columns}
    for ann in annotations:
        for col in columns:
            val = str(getattr(ann, col))
            widths[col] = max(widths[col], len(val))
    
    # Create header
    header = " | ".join(f"{col:{widths[col]}}" for col in columns)
    separator = "-+-".join("-" * widths[col] for col in columns)
    
    # Format rows
    rows = []
    for ann in annotations:
        row = " | ".join(f"{str(getattr(ann, col)):{widths[col]}}" for col in columns)
        rows.append(row)
    
    return "\n".join([header, separator] + rows)

async def handle_query(args, interface: BaktaUnifiedInterface):
    """Handle query command."""
    try:
        # Build query options
        sort_order = SortOrder.ASC if args.sort_order == "asc" else SortOrder.DESC
        options = interface.create_query_options(
            limit=args.limit,
            offset=args.offset,
            sort_by=args.sort_by,
            sort_order=sort_order
        )
        
        # Add filters if provided
        if args.feature_type or args.contig or args.attribute:
            builder = interface.create_query_builder(LogicalOperator.AND)
            
            if args.feature_type:
                builder.add_condition("feature_type", FilterOperator.EQUALS, args.feature_type)
            
            if args.contig:
                builder.add_condition("contig", FilterOperator.EQUALS, args.contig)
            
            if args.attribute:
                for attr in args.attribute:
                    if "=" in attr:
                        name, value = attr.split("=", 1)
                        builder.add_condition(f"attributes.{name}", FilterOperator.EQUALS, value)
            
            options.filters = builder.conditions
        
        # Handle region query
        if args.region:
            if "-" in args.region:
                start, end = map(int, args.region.split("-"))
                if not args.contig:
                    logger.error("Contig must be specified for region queries")
                    return 1
                
                results = interface.get_annotations_in_range(
                    job_id=args.job_id,
                    contig=args.contig,
                    start=start,
                    end=end
                )
            else:
                logger.error("Region must be in format 'start-end'")
                return 1
        else:
            # Regular query
            results = interface.get_annotations(job_id=args.job_id, options=options)
            
        # Output results
        if args.format == "json":
            annotations = [ann.dict() for ann in results.items]
            print(json.dumps(annotations, indent=2))
        else:
            print(f"Total annotations: {results.total}")
            print(f"Showing {len(results.items)} annotations (offset: {args.offset})")
            print()
            print(format_annotation_table(results.items))
        
        return 0
    except BaktaException as e:
        logger.error(f"Failed to query annotations: {e}")
        return 1

async def handle_list_jobs(args, interface: BaktaUnifiedInterface):
    """Handle list-jobs command."""
    try:
        jobs = await interface.list_jobs(limit=args.limit)
        
        if not jobs:
            print("No jobs found in database")
            return 0
        
        print(f"Found {len(jobs)} jobs:")
        print()
        
        # Define columns
        columns = ["id", "name", "status", "created_at"]
        
        # Get max width for each column
        widths = {col: len(col) for col in columns}
        for job in jobs:
            for col in columns:
                val = str(getattr(job, col, ""))
                widths[col] = max(widths[col], len(val))
        
        # Create header
        header = " | ".join(f"{col:{widths[col]}}" for col in columns)
        separator = "-+-".join("-" * widths[col] for col in columns)
        
        # Format rows
        rows = []
        for job in jobs:
            row = " | ".join(f"{str(getattr(job, col, '')):{widths[col]}}" for col in columns)
            rows.append(row)
        
        print("\n".join([header, separator] + rows))
        return 0
    except BaktaException as e:
        logger.error(f"Failed to list jobs: {e}")
        return 1

async def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Configure logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create interface
    try:
        interface = get_interface(
            api_key=args.api_key,
            database_path=args.database,
            environment=args.environment
        )
    except BaktaException as e:
        logger.error(f"Failed to initialize Bakta interface: {e}")
        return 1
    
    try:
        # Handle commands
        if args.command == "submit":
            return await handle_submit(args, interface)
        elif args.command == "status":
            return await handle_status(args, interface)
        elif args.command == "download":
            return await handle_download(args, interface)
        elif args.command == "import":
            return await handle_import(args, interface)
        elif args.command == "query":
            return await handle_query(args, interface)
        elif args.command == "list-jobs":
            return await handle_list_jobs(args, interface)
        else:
            logger.error("No command specified")
            return 1
    finally:
        # Clean up
        interface.close()

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 