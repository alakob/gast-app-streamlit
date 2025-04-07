#!/bin/bash
set -e
set -u

function apply_schema_to_database() {
    local database=$1
    echo "Applying schema to database '$database'"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$database" -f /docker-entrypoint-initdb.d/init-amr-schema.sql
}

if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
    echo "Applying schema to databases: $POSTGRES_MULTIPLE_DATABASES"
    for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
        apply_schema_to_database $db
    done
    echo "Schema applied to all databases"
fi 