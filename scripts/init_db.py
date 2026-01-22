"""Initialize the database - create the database and tables"""
import subprocess
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings

settings = get_settings()


def create_database():
    """Create the autosaas database if it doesn't exist"""
    # Parse the database URL to get connection info
    # Format: postgresql://user:password@host:port/dbname
    db_url = settings.database_url
    
    # Extract parts
    parts = db_url.replace("postgresql://", "").split("@")
    user_pass = parts[0].split(":")
    host_db = parts[1].split("/")
    host_port = host_db[0].split(":")
    
    user = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else ""
    host = host_port[0]
    port = host_port[1] if len(host_port) > 1 else "5432"
    dbname = host_db[1]
    
    print(f"Database configuration:")
    print(f"  Host: {host}:{port}")
    print(f"  User: {user}")
    print(f"  Database: {dbname}")
    print()
    
    # Set PGPASSWORD environment variable
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    
    # Check if database exists
    print("Checking if database exists...")
    try:
        result = subprocess.run(
            ["psql", "-h", host, "-p", port, "-U", user, "-d", "postgres", "-tAc",
             f"SELECT 1 FROM pg_database WHERE datname='{dbname}'"],
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.returncode != 0:
            print(f"Error connecting to PostgreSQL: {result.stderr}")
            print("\nMake sure PostgreSQL is running and credentials are correct.")
            print(f"Current DATABASE_URL: {db_url}")
            return False
        
        if "1" in result.stdout:
            print(f"Database '{dbname}' already exists.")
        else:
            print(f"Creating database '{dbname}'...")
            result = subprocess.run(
                ["psql", "-h", host, "-p", port, "-U", user, "-d", "postgres", "-c",
                 f"CREATE DATABASE {dbname}"],
                capture_output=True,
                text=True,
                env=env
            )
            if result.returncode != 0:
                print(f"Error creating database: {result.stderr}")
                return False
            print(f"Database '{dbname}' created successfully!")
        
        return True
        
    except FileNotFoundError:
        print("psql command not found. Make sure PostgreSQL is installed and in PATH.")
        print("You can also create the database manually:")
        print(f"  CREATE DATABASE {dbname};")
        return False


def create_tables():
    """Create all tables"""
    print("\nCreating tables...")
    
    from app.db.base import Base
    from app.db.session import engine
    import app.models  # Import to register models
    
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nCreated tables: {', '.join(tables)}")
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("AutoSaaS Database Initialization")
    print("=" * 50)
    print()
    
    if create_database():
        create_tables()
    
    print()
    print("=" * 50)
    print("Done!")
    print("=" * 50)
