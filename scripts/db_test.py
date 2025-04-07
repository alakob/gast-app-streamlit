import sqlalchemy
import sys

try:
    # Create engine (connection string)
    conn_str = 'postgresql://postgres:postgres@postgres:5432/amr_predictor_dev'
    print(f"Attempting to connect to: {conn_str}")
    
    engine = sqlalchemy.create_engine(conn_str)
    
    # Test connection by listing tables
    with engine.connect() as conn:
        result = conn.execute(sqlalchemy.text('SELECT table_name FROM information_schema.tables WHERE table_schema = \'public\''))
        
        print("Tables in database:")
        tables = [row[0] for row in result]
        for table in tables:
            print(f"- {table}")
            
        # Check if our specific table exists
        if 'amr_dsm_antibiotics' in tables:
            print("\nFound amr_dsm_antibiotics table! Testing query:")
            result = conn.execute(sqlalchemy.text('SELECT COUNT(*) FROM amr_dsm_antibiotics'))
            count = result.fetchone()[0]
            print(f"Table contains {count} rows")
            
            # Show sample data
            if count > 0:
                result = conn.execute(sqlalchemy.text('SELECT * FROM amr_dsm_antibiotics LIMIT 3'))
                print("\nSample data:")
                for row in result:
                    print(row)
        else:
            print("\namr_dsm_antibiotics table NOT found!")
    
    print("\nDatabase connection successful!")
    
except Exception as e:
    print(f"Database connection error: {e}", file=sys.stderr)
    sys.exit(1)
