# Bakta Integration Action Plan

## Overview

This document outlines a detailed action plan for integrating the Bakta API with our application. The plan details how to retrieve annotation results from the Bakta API for a given FASTA sequence, store this data in a SQLite database, and structure the implementation process into distinct phases. Each phase includes verification guidelines to ensure correctness before moving to the next phase.

## Phase 1: API Integration Layer

### 1.1 API Client Setup

- Create a dedicated `BaktaClient` class that encapsulates all API interactions
- Implement the following methods based on the existing proof-of-concept script:
  - `initialize_job()`: Initialize a new annotation job
  - `upload_fasta(upload_link, sequence)`: Upload a FASTA sequence
  - `start_job(job_id, secret, config)`: Start the annotation job
  - `check_job_status(job_id, secret)`: Check the status of an annotation job
  - `get_job_logs(job_id, secret)`: Retrieve job logs
  - `get_job_results(job_id, secret)`: Get results of a completed job
  - `download_result_file(url, output_path)`: Download a specific result file
  - `poll_job_status(job_id, secret)`: Monitor job status until completion

### 1.2 Error Handling and Validation

- Implement proper exception handling for network errors, API errors, and validation failures
- Add input validation for:
  - FASTA format validation
  - Configuration parameter validation
  - Response validation to ensure expected data is received
- Create custom exception classes for different error types

### 1.3 Configuration Management

- Implement a configuration system for Bakta API parameters
- Allow for customization of all job configuration parameters (genus, species, etc.)
- Support environment-specific configurations (dev, test, prod)

### 1.4 Phase 1 Testing Guidelines

- Create unit tests for the `BaktaClient` class, mocking API responses
- Test error handling with simulated failures
- Create integration tests using a small test FASTA sequence
- Verify the client can:
  - Initialize a job
  - Upload a sequence
  - Start a job
  - Poll for completion
  - Retrieve results
- Success Criteria: All API interactions work correctly and handle errors appropriately

## Phase 2: Database Schema and Storage Layer

### 2.1 SQLite Database Schema Design

- Design a database schema to store:
  - Job metadata (ID, secret, status, timestamps)
  - Job configuration parameters
  - Result file locations
  - Annotation data from result files (parsed from JSON/TSV/GFF3)
- Create tables for:
  - `bakta_jobs`: Store job metadata and configuration
  - `bakta_result_files`: Store paths to downloaded result files
  - `bakta_annotations`: Store parsed annotation data
  - `bakta_sequences`: Store the submitted sequences

### 2.2 Database Connection Manager

- Create a `DatabaseManager` class to handle SQLite connections
- Implement methods for:
  - Initializing the database (creating tables if they don't exist)
  - Opening and closing connections with proper context management
  - Basic CRUD operations for each table
  - Transaction management for multi-step operations

### 2.3 Data Models and ORM

- Create data models for the database entities
- Implement mapping between API response data and database models
- Design a lightweight ORM for database interactions

### 2.4 Phase 2 Testing Guidelines

- Create unit tests for the `DatabaseManager` class
- Test database schema creation
- Test CRUD operations for all tables
- Test data model mapping and validation
- Verify data integrity constraints
- Success Criteria: Database schema correctly set up and data operations work as expected

## Phase 3: Parser and Data Transformation Layer

### 3.1 Result File Parsers

- Implement parsers for each Bakta result file format:
  - `GFF3Parser`: Parse GFF3 files
  - `TSVParser`: Parse TSV files
  - `JSONParser`: Parse JSON files
  - Additional parsers for EMBL, GenBank, and FASTA files
- Extract structured data from each file format

### 3.2 Data Normalization and Transformation

- Create transformers to convert parsed data into database models
- Implement data normalization to avoid redundancy
- Design data validation for parsed content

### 3.3 Storage Orchestration

- Create a `BaktaStorageService` to coordinate:
  - Downloading result files
  - Parsing file contents
  - Transforming data
  - Storing in the database
- Implement queuing mechanism for background processing of large files

### 3.4 Phase 3 Testing Guidelines

- Create unit tests for each parser
- Test with sample files from Bakta API
- Test data transformation with various input formats
- Test end-to-end storage process
- Verify correct extraction and storage of annotation data
- Success Criteria: All file formats can be correctly parsed and stored in the database

## Phase 4: Process Orchestration and Job Management

### 4.1 Job Manager Implementation

- Create a `BaktaJobManager` class to coordinate the entire workflow:
  - Job submission
  - Monitoring
  - Result retrieval
  - Data storage
- Implement state management for tracking job progress

### 4.2 Asynchronous Processing

- Design an asynchronous processing system for long-running jobs
- Implement background polling for job status
- Create a notification mechanism for job completion

### 4.3 Retry and Recovery Mechanisms

- Implement retry logic for transient failures
- Design a recovery mechanism for interrupted processes
- Create a job history tracking system

### 4.4 Phase 4 Testing Guidelines

- Test end-to-end job processing
- Simulate failures to test recovery mechanisms
- Test concurrent job submission and processing
- Verify job state transitions are correctly tracked
- Success Criteria: Complete job lifecycle can be managed without manual intervention

## Phase 5: Query Interface and Data Access Layer

### 5.1 Query Interface Design

- Create a query interface for accessing stored annotation data
- Implement filtering, sorting, and pagination
- Design a search mechanism for annotations

### 5.2 Data Access Objects

- Implement Data Access Objects (DAOs) for each entity
- Create methods for common queries
- Design a query builder for complex filters

### 5.3 Performance Optimization

- Add indexes to the database for common query patterns
- Implement caching for frequently accessed data
- Optimize large dataset handling

### 5.4 Phase 5 Testing Guidelines

- Test query performance with large datasets
- Verify correctness of query results
- Test complex filters and search functionality
- Benchmark query performance
- Success Criteria: Queries execute efficiently and return correct results

## Phase 6: Integration and System Testing

### 6.1 System Integration

- Integrate all components:
  - API client
  - Database manager
  - Parsers
  - Job manager
  - Query interface
- Create a unified interface for the entire system

### 6.2 Command-Line Interface

- Implement a CLI for interacting with the system
- Add commands for:
  - Submitting sequences
  - Checking job status
  - Retrieving results
  - Querying stored annotations

### 6.3 Error Reporting and Logging

- Implement comprehensive error reporting
- Create structured logging
- Design user-friendly error messages

### 6.4 Phase 6 Testing Guidelines

- Perform end-to-end testing with real sequences
- Test the CLI with various commands
- Verify error reporting works correctly
- Test with edge cases and unusual inputs
- Success Criteria: Complete system functions correctly and handles all expected use cases

## Implementation Considerations

### Error Handling Strategy

- Network-related errors: Implement retries with exponential backoff
- API errors: Parse error responses and provide meaningful feedback
- Validation errors: Provide clear information about invalid inputs
- Database errors: Implement transactions for atomicity and recovery

### Data Validation

- FASTA sequence validation:
  - Check for valid FASTA format
  - Validate headers
  - Check sequence content for valid characters
- API response validation:
  - Verify expected fields are present
  - Check data types and formats
  - Validate URLs and file paths

### Performance Considerations

- Implement streaming downloads for large result files
- Use background processing for long-running operations
- Optimize database queries with proper indexing
- Consider database connection pooling for concurrent operations

### Security Considerations

- Store job secrets securely
- Validate and sanitize all inputs
- Implement proper file permissions for downloaded results
- Consider encryption for sensitive data

## Conclusion

This action plan provides a structured approach to integrating the Bakta API with a SQLite database. By following the outlined phases and testing guidelines, we can ensure a robust implementation that correctly retrieves, parses, and stores annotation data from the Bakta API.
