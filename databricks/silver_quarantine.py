# databricks/silver_quarantine.py
"""
SILVER LAYER DATA QUALITY & QUARANTINE
Purpose: Cleanse Bronze data, enforce business rules, and execute idempotent upserts.

Theoretical Principles Applied:
- The Quarantine Pattern: Isolates invalid records (bots, missing emails) to prevent OOM 
  crashes downstream and maintain dashboard accuracy.
- Idempotency: Uses DeltaTable MERGE to ensure running the script multiple times 
  yields the exact same state without duplicating records.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp
from delta.tables import DeltaTable

spark = SparkSession.builder.getOrCreate()

def process_telemetry_silver():
    print("Reading Bronze Telemetry...")
    bronze_df = spark.table("bronze_telemetry_sessions")
    
    # 1. Apply Business Rules for Data Quality
    # A session is VALID if it has an email and passed the CAPTCHA threshold
    valid_condition = col("user_email").isNotNull() & (col("human_validation_score") >= 0.7)
    
    clean_df = bronze_df.filter(valid_condition)
    quarantine_df = bronze_df.filter(~valid_condition)
    
    # 2. Add Silver metadata
    clean_df = clean_df.withColumn("_silver_processed_at", current_timestamp())
    quarantine_df = quarantine_df.withColumn("_quarantine_reason", col("human_validation_score"))

    # 3. Idempotent Upsert (MERGE) for Clean Data
    upsert_silver_table(clean_df, "silver_telemetry_sessions", "session_id")
    
    # 4. Idempotent Upsert (MERGE) for Quarantine Data
    upsert_silver_table(quarantine_df, "silver_quarantine_sessions", "session_id")
    
    print(f"Processed {clean_df.count()} clean records and {quarantine_df.count()} quarantined records.")

def upsert_silver_table(df, table_name, primary_key):
    """
    Executes a distributed MERGE operation. If the table doesn't exist, it creates it.
    If it does, it updates existing records and inserts new ones, achieving idempotency.
    """
    if not spark.catalog.tableExists(table_name):
        print(f"Creating new Delta table: {table_name}")
        df.write.format("delta").saveAsTable(table_name)
    else:
        print(f"Merging updates into existing Delta table: {table_name}")
        delta_table = DeltaTable.forName(spark, table_name)
        
        # This prevents duplication if the pipeline is triggered twice
        delta_table.alias("target").merge(
            df.alias("source"),
            f"target.{primary_key} = source.{primary_key}"
        ) \
        .whenMatchedUpdateAll() \
        .whenNotMatchedInsertAll() \
        .execute()

if __name__ == "__main__":
    process_telemetry_silver()