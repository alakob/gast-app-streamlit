import pandas as pd
import pickle
import sqlalchemy
from sqlalchemy import create_engine, text
import sys

# Load the DataFrame
try:
    pickle_file = "/Users/alakob/projects/gast-app-streamlit/datasets/antibiotic_df.pkl"
    print(f"Loading DataFrame from: {pickle_file}")
    with open(pickle_file, 'rb') as f:
        antibiotic_df = pickle.load(f)
    
    print(f"DataFrame loaded successfully. Shape: {antibiotic_df.shape}")
    
    # Clean up column names (remove any trailing spaces)
    antibiotic_df.columns = [col.strip() if isinstance(col, str) else col for col in antibiotic_df.columns]
    print(f"Cleaned column names: {antibiotic_df.columns.tolist()}")
    
    # Database connection parameters (based on docker-compose.yml)
    DB_HOST = "localhost"  # or "postgres" if running from within a container
    DB_PORT = "5432"
    DB_USER = "postgres"
    DB_PASS = "postgres"
    DB_NAME = "amr_predictor_dev"  # or test/prod depending on environment
    TABLE_NAME = "amr_dsm_antibiotics"
    
    # Create SQLAlchemy engine
    db_uri = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    print(f"Connecting to database: {DB_NAME} at {DB_HOST}:{DB_PORT}")
    
    engine = create_engine(db_uri)
    
    # First, check if the table exists and drop it if it does
    with engine.connect() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {TABLE_NAME}"))
        connection.commit()
        print(f"Dropped table {TABLE_NAME} if it existed")
    
    # Store DataFrame to PostgreSQL
    print(f"Storing DataFrame to PostgreSQL table: {TABLE_NAME}")
    antibiotic_df.to_sql(
        name=TABLE_NAME,
        con=engine,
        index=False,
        if_exists='replace',  # 'replace' will drop the table if it exists
        method='multi',  # Efficiently insert in batches
        schema='public'
    )
    
    # Verify the data was inserted correctly
    with engine.connect() as connection:
        result = connection.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}"))
        count = result.fetchone()[0]
        print(f"Successfully inserted {count} rows into {TABLE_NAME}")
        
        # Get the column names from the database
        columns_result = connection.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{TABLE_NAME}'"))
        columns = [row[0] for row in columns_result]
        print(f"Table columns: {columns}")
        
        # Sample data
        sample_result = connection.execute(text(f"SELECT * FROM {TABLE_NAME} LIMIT 5"))
        print("\nSample data:")
        for row in sample_result:
            print(row)
    
    print("\nSuccess! Antibiotic data has been stored in the PostgreSQL database.")
    
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
