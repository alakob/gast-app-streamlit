-- Create schema for Bakta Annotation in PostgreSQL
-- This script creates tables for storing Bakta annotation data 
-- for genomic sequence annotations

-- Run this script on all databases
\c amr_predictor_dev;
\echo 'Creating Bakta schema in amr_predictor_dev database...'

-- Create enum types for job status
CREATE TYPE bakta_job_status AS ENUM (
    'CREATED',
    'QUEUED',
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'EXPIRED',
    'UNKNOWN'
);

-- Create bakta_jobs table to store job metadata
CREATE TABLE IF NOT EXISTS bakta_jobs (
    id TEXT PRIMARY KEY,                -- Job ID from Bakta API (UUID)
    name TEXT NOT NULL,                 -- User-defined job name
    secret TEXT NOT NULL,               -- Job secret for API authentication
    status bakta_job_status NOT NULL,   -- Job status 
    fasta_path TEXT,                    -- Path to the FASTA file used for the job
    config JSONB NOT NULL,              -- Job configuration as JSONB
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create table for storing the sequences submitted to Bakta
CREATE TABLE IF NOT EXISTS bakta_sequences (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES bakta_jobs(id) ON DELETE CASCADE,
    header TEXT NOT NULL,               -- Sequence header (from FASTA)
    sequence TEXT NOT NULL,             -- The actual sequence
    length INTEGER NOT NULL,            -- Length of the sequence
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create table for storing downloaded result file paths
CREATE TABLE IF NOT EXISTS bakta_result_files (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES bakta_jobs(id) ON DELETE CASCADE,
    file_type TEXT NOT NULL,            -- Type of file (GFF3, JSON, TSV, etc.)
    file_path TEXT NOT NULL,            -- Path to the downloaded file (in Docker volume)
    download_url TEXT,                  -- Original download URL
    downloaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create table for storing annotation data from result files
CREATE TABLE IF NOT EXISTS bakta_annotations (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES bakta_jobs(id) ON DELETE CASCADE,
    feature_id TEXT NOT NULL,           -- Feature ID from annotation
    feature_type TEXT NOT NULL,         -- Feature type (CDS, rRNA, tRNA, etc.)
    contig TEXT NOT NULL,               -- Contig/chromosome name
    start INTEGER NOT NULL,             -- Start position (1-based)
    "end" INTEGER NOT NULL,               -- End position
    strand TEXT NOT NULL,               -- Strand (+, -, or .)
    attributes JSONB NOT NULL,          -- Feature attributes as JSONB
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create table for job status history
CREATE TABLE IF NOT EXISTS bakta_job_status_history (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES bakta_jobs(id) ON DELETE CASCADE,
    status bakta_job_status NOT NULL,   -- Job status
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    message TEXT                        -- Optional message about status change
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_bakta_jobs_status ON bakta_jobs(status);
CREATE INDEX IF NOT EXISTS idx_bakta_sequences_job_id ON bakta_sequences(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_result_files_job_id ON bakta_result_files(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_job_id ON bakta_annotations(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_feature_type ON bakta_annotations(feature_type);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_position ON bakta_annotations(start, "end");
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_job_contig ON bakta_annotations(job_id, contig);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_job_feature_type ON bakta_annotations(job_id, feature_type);
CREATE INDEX IF NOT EXISTS idx_bakta_sequences_header ON bakta_sequences(header);
CREATE INDEX IF NOT EXISTS idx_bakta_job_status_history_job_id ON bakta_job_status_history(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_jobs_created_at ON bakta_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_bakta_jobs_updated_at ON bakta_jobs(updated_at);

-- Apply the same schema to test and prod databases
\c amr_predictor_test;
\echo 'Creating Bakta schema in amr_predictor_test database...'

-- Create the same schema in test database (repeat the CREATE statements above)
CREATE TYPE bakta_job_status AS ENUM (
    'CREATED',
    'QUEUED',
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'EXPIRED',
    'UNKNOWN'
);

CREATE TABLE IF NOT EXISTS bakta_jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    secret TEXT NOT NULL,
    status bakta_job_status NOT NULL,
    fasta_path TEXT,
    config JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS bakta_sequences (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES bakta_jobs(id) ON DELETE CASCADE,
    header TEXT NOT NULL,
    sequence TEXT NOT NULL,
    length INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bakta_result_files (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES bakta_jobs(id) ON DELETE CASCADE,
    file_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    download_url TEXT,
    downloaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bakta_annotations (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES bakta_jobs(id) ON DELETE CASCADE,
    feature_id TEXT NOT NULL,
    feature_type TEXT NOT NULL,
    contig TEXT NOT NULL,
    start INTEGER NOT NULL,
    "end" INTEGER NOT NULL,
    strand TEXT NOT NULL,
    attributes JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bakta_job_status_history (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES bakta_jobs(id) ON DELETE CASCADE,
    status bakta_job_status NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    message TEXT
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_bakta_jobs_status ON bakta_jobs(status);
CREATE INDEX IF NOT EXISTS idx_bakta_sequences_job_id ON bakta_sequences(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_result_files_job_id ON bakta_result_files(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_job_id ON bakta_annotations(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_feature_type ON bakta_annotations(feature_type);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_position ON bakta_annotations(start, "end");
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_job_contig ON bakta_annotations(job_id, contig);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_job_feature_type ON bakta_annotations(job_id, feature_type);
CREATE INDEX IF NOT EXISTS idx_bakta_sequences_header ON bakta_sequences(header);
CREATE INDEX IF NOT EXISTS idx_bakta_job_status_history_job_id ON bakta_job_status_history(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_jobs_created_at ON bakta_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_bakta_jobs_updated_at ON bakta_jobs(updated_at);

\c amr_predictor_prod;
\echo 'Creating Bakta schema in amr_predictor_prod database...'

-- Create the same schema in prod database
CREATE TYPE bakta_job_status AS ENUM (
    'CREATED',
    'QUEUED',
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'EXPIRED',
    'UNKNOWN'
);

CREATE TABLE IF NOT EXISTS bakta_jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    secret TEXT NOT NULL,
    status bakta_job_status NOT NULL,
    fasta_path TEXT,
    config JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS bakta_sequences (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES bakta_jobs(id) ON DELETE CASCADE,
    header TEXT NOT NULL,
    sequence TEXT NOT NULL,
    length INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bakta_result_files (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES bakta_jobs(id) ON DELETE CASCADE,
    file_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    download_url TEXT,
    downloaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bakta_annotations (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES bakta_jobs(id) ON DELETE CASCADE,
    feature_id TEXT NOT NULL,
    feature_type TEXT NOT NULL,
    contig TEXT NOT NULL,
    start INTEGER NOT NULL,
    "end" INTEGER NOT NULL,
    strand TEXT NOT NULL,
    attributes JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bakta_job_status_history (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES bakta_jobs(id) ON DELETE CASCADE,
    status bakta_job_status NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    message TEXT
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_bakta_jobs_status ON bakta_jobs(status);
CREATE INDEX IF NOT EXISTS idx_bakta_sequences_job_id ON bakta_sequences(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_result_files_job_id ON bakta_result_files(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_job_id ON bakta_annotations(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_feature_type ON bakta_annotations(feature_type);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_position ON bakta_annotations(start, "end");
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_job_contig ON bakta_annotations(job_id, contig);
CREATE INDEX IF NOT EXISTS idx_bakta_annotations_job_feature_type ON bakta_annotations(job_id, feature_type);
CREATE INDEX IF NOT EXISTS idx_bakta_sequences_header ON bakta_sequences(header);
CREATE INDEX IF NOT EXISTS idx_bakta_job_status_history_job_id ON bakta_job_status_history(job_id);
CREATE INDEX IF NOT EXISTS idx_bakta_jobs_created_at ON bakta_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_bakta_jobs_updated_at ON bakta_jobs(updated_at);

\echo 'Bakta schema creation completed.'
