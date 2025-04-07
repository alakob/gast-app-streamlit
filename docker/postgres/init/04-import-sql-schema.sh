#!/bin/bash

set -e
set -u

# List of databases to initialize
databases=("amr_predictor_dev" "amr_predictor_test" "amr_predictor_prod")

for db in "${databases[@]}"; do
    echo "Initializing database: $db"
    
    # Import AMR schema
    echo "Importing AMR schema..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" -f /docker-entrypoint-initdb.d/02-init-amr-schema.sql
    
    # Import Bakta schema (continue on error since it might already exist)
    echo "Importing Bakta schema..."
    psql --username "$POSTGRES_USER" --dbname "$db" -f /docker-entrypoint-initdb.d/02a-create-bakta-schema.sql || true
    
    # Import AMR antibiotic data
    echo "Importing AMR antibiotic data..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" -f /docker-entrypoint-initdb.d/03-init-amr-antibiotic.sql
    
    echo "Database $db initialized successfully"
done

echo "Schema initialization complete"
