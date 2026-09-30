# databricks/bronze_ingestion.py
"""
BRONZE LAYER INGESTION
Purpose: Extract raw telemetry sessions and OCR jobs from Supabase Postgres 
via JDBC and write them into Delta Lake format with append-only semantics.

Theoretical Principles Applied:
- Source Preservation: Raw data is ingested as-is, without altering types or scrubbing nulls.
- Schema Enforcement: Delta Lake enforces the tabular contract upon ingestion.
- Idempotency Consideration: In production, incremental watermarks (e.g. created_at)
  or Change Data Capture (CDC) ensure records are not ingested twice.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, input_file_name

# Initialize Spark Session (automatically provided in Databricks notebooks)
spark = SparkSession.builder.getOrCreate()

# Database Connection Parameters
# In Databricks, retrieve credentials using dbutils.secrets.get()
DB_HOST = "db.<your-supabase-project-ref>.supabase.co"
DB_PORT = "5432"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "<your-supabase-db-password>"

JDBC_URL = f"jdbc:postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}"

JDBC_PROPERTIES = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "driver": "org.postgresql.Driver",
    "ssl": "true",
    "sslmode": "require"
}

def ingest_table_to_bronze(source_table: str, target_delta_table: str):
    """
    Reads a table via JDBC and appends to a Delta table, adding ingestion metadata.
    """
    print(f"Reading from {source_table} via JDBC...")
    
    # Pushdown query to extract raw data
    raw_df = spark.read.jdbc(
        url=JDBC_URL,
        table=source_table,
        properties=JDBC_PROPERTIES
    )
    
    # Audit trail: Track ingestion timestamp
    bronze_df = raw_df.withColumn("_ingestion_timestamp", current_timestamp())
    
    # Write to Bronze Delta Table (Append-only)
    print(f"Writing raw data to {target_delta_table}...")
    bronze_df.write \
        .format("delta") \
        .mode("append") \
        .saveAsTable(target_delta_table)
    
    print(f"Ingestion for {target_delta_table} completed successfully.")

if __name__ == "__main__":
    # Ingest telemetry sessions
    ingest_table_to_bronze("telemetry_sessions", "bronze_telemetry_sessions")
    
    # Ingest OCR jobs metadata
    ingest_table_to_bronze("ocr_jobs", "bronze_ocr_jobs")