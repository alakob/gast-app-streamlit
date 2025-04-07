#!/bin/bash
# Script to rebuild and restart all containers with proper initialization order

echo "=== AMR Predictor - Rebuilding All Containers ==="
echo "This script will rebuild all containers with their dependencies"

# Enable Docker Compose Bake for better build performance
export COMPOSE_BAKE=true
echo "Enabled Compose Bake for improved build performance"

# Stop existing containers and remove volumes to ensure clean state
echo "Stopping existing containers and cleaning up..."
docker-compose down -v

# Build all containers with no cache to ensure fresh dependencies
echo "Rebuilding all containers (this may take a few minutes)..."
docker-compose build --no-cache postgres pgadmin amr-api streamlit

# Start PostgreSQL first and wait for it to be healthy
echo "Starting PostgreSQL database..."
docker-compose up -d postgres

# Wait for PostgreSQL to be healthy
echo "Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U postgres -d amr_predictor_dev; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
done
echo "PostgreSQL is ready!"

# Generate AMR antibiotic table SQL if needed
if [ ! -f docker/postgres/init/init-amr-antibiotic.sql ]; then
    echo "Generating AMR antibiotic table SQL..."
    python3 scripts/create_amr_antibiotic_table.py
fi

# Verify database schema and tables
echo "Verifying database schema and tables..."
docker-compose exec -T postgres psql -U postgres -d amr_predictor_dev << EOF
DO \$\$
BEGIN
    -- Check AMR Predictor tables
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'users') THEN
        RAISE EXCEPTION 'users table not found';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'amr_jobs') THEN
        RAISE EXCEPTION 'amr_jobs table not found';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'amr_job_parameters') THEN
        RAISE EXCEPTION 'amr_job_parameters table not found';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'amr_antibiotic') THEN
        RAISE EXCEPTION 'amr_antibiotic table not found';
    END IF;
    
    -- Check Bakta tables
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'bakta_jobs') THEN
        RAISE EXCEPTION 'bakta_jobs table not found';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'bakta_sequences') THEN
        RAISE EXCEPTION 'bakta_sequences table not found';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'bakta_result_files') THEN
        RAISE EXCEPTION 'bakta_result_files table not found';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'bakta_annotations') THEN
        RAISE EXCEPTION 'bakta_annotations table not found';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'bakta_job_status_history') THEN
        RAISE EXCEPTION 'bakta_job_status_history table not found';
    END IF;
    
    -- Check AMR jobs table columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'amr_jobs' AND column_name = 'bakta_job_id'
    ) THEN
        RAISE EXCEPTION 'bakta_job_id column not found in amr_jobs table';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'amr_jobs' AND column_name = 'bakta_job_secret'
    ) THEN
        RAISE EXCEPTION 'bakta_job_secret column not found in amr_jobs table';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'amr_jobs' AND column_name = 'bakta_status'
    ) THEN
        RAISE EXCEPTION 'bakta_status column not found in amr_jobs table';
    END IF;
    
    -- Check indexes
    IF NOT EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_job_status') THEN
        RAISE EXCEPTION 'idx_job_status index not found';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_job_parameters') THEN
        RAISE EXCEPTION 'idx_job_parameters index not found';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_bakta_job_id') THEN
        RAISE EXCEPTION 'idx_bakta_job_id index not found';
    END IF;
    
    IF NOT EXISTS (SELECT FROM pg_indexes WHERE indexname = 'idx_bakta_status') THEN
        RAISE EXCEPTION 'idx_bakta_status index not found';
    END IF;
    
    RAISE NOTICE 'All tables, columns, and indexes verified successfully';
END \$\$;
EOF

if [ $? -eq 0 ]; then
    echo "Database schema verification successful!"
else
    echo "Error: Database schema verification failed!"
    exit 1
fi

# Start pgAdmin
echo "Starting pgAdmin..."
docker-compose up -d pgadmin

# Start the API service
echo "Starting AMR API..."
docker-compose up -d amr-api

# Start the Streamlit frontend
echo "Starting Streamlit frontend..."
docker-compose up -d streamlit

# Show logs to verify successful startup
echo "Displaying logs to verify startup..."
docker-compose logs -f
