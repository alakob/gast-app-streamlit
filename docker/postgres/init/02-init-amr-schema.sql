-- PostgreSQL Schema Initialization for AMR Predictor
-- This script sets up the database schema for the AMR Predictor application
-- It will be executed automatically when the PostgreSQL container starts

-- Create users table (if needed by your application)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Create amr_jobs table
CREATE TABLE IF NOT EXISTS amr_jobs (
    id VARCHAR(255) PRIMARY KEY,
    status VARCHAR(50) NOT NULL,
    progress FLOAT DEFAULT 0,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    result_file VARCHAR(255),
    aggregated_result_file VARCHAR(255),
    error TEXT,
    additional_info JSONB,
    -- Bakta integration fields
    bakta_job_id VARCHAR(255),
    bakta_job_secret VARCHAR(255),
    bakta_status VARCHAR(50),
    bakta_result_url TEXT,
    bakta_start_time TIMESTAMP,
    bakta_end_time TIMESTAMP,
    bakta_error TEXT
);

-- Create amr_job_parameters table
CREATE TABLE IF NOT EXISTS amr_job_parameters (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) REFERENCES amr_jobs(id) ON DELETE CASCADE,
    param_name VARCHAR(255) NOT NULL,
    param_value TEXT,
    UNIQUE(job_id, param_name)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_job_status ON amr_jobs(status);
CREATE INDEX IF NOT EXISTS idx_job_parameters ON amr_job_parameters(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_job_id ON amr_jobs(bakta_job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_status ON amr_jobs(bakta_status);
