#!/bin/bash

set -e
set -u

# Execute SQL initialization scripts
echo "Importing AMR schema to all databases..."

for db in $POSTGRES_MULTIPLE_DATABASES; do
    echo "Applying schema to database: $db"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" -f /docker-entrypoint-initdb.d/init-amr-schema.sql
done

echo "Schema initialization complete"
