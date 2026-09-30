# databricks/gold_analytics.py
"""
GOLD LAYER ANALYTICS & MONETIZATION
Purpose: Aggregate Silver layer data into business-ready star schema dimensions 
and fact tables to monitor API usage and paywall limits.

Theoretical Principles Applied:
- Complete Overwrite Pattern: Instead of complex UPSERTS (MERGE), Gold aggregation 
  tables are often completely overwritten during each run. Because they are highly 
  compressed summary tables, overwriting is extremely fast and guarantees 100% 
  accuracy with the underlying Silver data.
- Wide Transformations: Aggregations trigger the Catalyst Optimizer to perform 
  network shuffles, computing results across the cluster.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import count, col, sum, when

spark = SparkSession.builder.getOrCreate()

def build_gold_monetization_metrics():
    print("Reading Silver Telemetry & OCR Jobs...")
    silver_telemetry = spark.table("silver_telemetry_sessions")
    silver_jobs = spark.table("silver_ocr_jobs") # Assuming similar silver creation for jobs

    # Join telemetry with jobs to associate user emails with their document pages
    # Note: We use an inner join here assuming we only want to bill for submitted jobs
    enriched_df = silver_telemetry.join(
        silver_jobs, 
        on="session_id", 
        how="inner"
    )

    # 1. User Paywall Fact Table (How many pages has each user processed?)
    # This is a Wide Transformation (Shuffle) because of groupBy
    user_usage_df = enriched_df.groupBy("user_email").agg(
        count("job_id").alias("total_pages_processed"),
        sum(when(col("status") == "failed", 1).otherwise(0)).alias("total_failures")
    )

    # 2. OS Distribution Dimension (Which platforms drive our traffic?)
    os_metrics_df = silver_telemetry.groupBy("os_version").agg(
        count("session_id").alias("total_sessions")
    )

    # 3. Simulate Materialized Views (Idempotent Overwrite)
    print("Overwriting Gold Aggregation Tables...")
    
    user_usage_df.write \
        .format("delta") \
        .mode("overwrite") \
        .saveAsTable("gold_user_paywall_metrics")

    os_metrics_df.write \
        .format("delta") \
        .mode("overwrite") \
        .saveAsTable("gold_os_distribution")

    print("Gold Layer build complete.")

if __name__ == "__main__":
    build_gold_monetization_metrics()