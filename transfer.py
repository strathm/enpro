import sqlite3
from sqlalchemy import create_engine, MetaData, Table, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# SQLite connection
sqlite_path = r"C:\Users\User\Desktop\enpro\instance\capitalshop.db"
sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_cursor = sqlite_conn.cursor()

# PostgreSQL connection details
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

# Build PostgreSQL connection URL
postgres_url = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
postgres_engine = create_engine(postgres_url)
PostgresSession = sessionmaker(bind=postgres_engine)
postgres_session = PostgresSession()

# Reflect existing tables from PostgreSQL
postgres_metadata = MetaData()
postgres_metadata.reflect(bind=postgres_engine)

def transfer_table(table_name):
    print(f"\nTransferring table: {table_name}")

    try:
        # Fetch data from SQLite
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
        if not rows:
            print(f"  Skipped: No data found in '{table_name}'")
            return

        sqlite_columns = [desc[0] for desc in sqlite_cursor.description]

        # Load matching PostgreSQL table
        postgres_table = Table(table_name, postgres_metadata, autoload_with=postgres_engine)
        postgres_columns = [col.name for col in postgres_table.columns]

        # Warn on column mismatch
        if set(sqlite_columns) != set(postgres_columns):
            print(f"  Warning: Column mismatch in '{table_name}'")
            print(f"    SQLite columns   : {sqlite_columns}")
            print(f"    PostgreSQL columns: {postgres_columns}")

        # Prepare records
        data = []
        for row in rows:
            row_dict = dict(zip(sqlite_columns, row))
            data.append({col: row_dict.get(col) for col in postgres_columns})

        # Insert data
        with postgres_engine.begin() as connection:
            connection.execute(postgres_table.insert(), data)
        print(f"  Success: Transferred {len(rows)} records.")
    except Exception as e:
        print(f"  Error transferring '{table_name}': {e}")

def main():
    # Skip disabling foreign key checks if the role setting is causing issues
    # with postgres_engine.begin() as conn:
    #     conn.execute(text("SET session_replication_role = 'replica';"))

    tables_to_transfer = [
        "user",
        "category",
        "product",
        "blog_post",
        "blog_image",
        "contact_submission",
        "page",
        "setting"
    ]

    for table in tables_to_transfer:
        transfer_table(table)

    # Re-enable foreign key checks (optional)
    # with postgres_engine.begin() as conn:
    #     conn.execute(text("SET session_replication_role = 'origin';"))

    # Cleanup
    sqlite_conn.close()
    postgres_session.close()
    print("\nAll done. Data transfer complete.")

if __name__ == "__main__":
    main()
