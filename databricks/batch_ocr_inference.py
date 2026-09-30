# databricks/batch_ocr_inference.py
"""
BATCH OCR INFERENCE PIPELINE
Purpose: Distribute deep learning text extraction across Spark worker nodes.

Theoretical Principles Applied:
- Distributed Inference: Uses `foreachPartition` to instantiate the EasyOCR model 
  once per worker node (preventing OOM errors) rather than once per row.
- Row-Level Operational Updates: Spark JDBC is designed for bulk writes. To perform 
  row-level UPDATEs on the Supabase Postgres table, we use `psycopg2` directly from the workers.
"""

from pyspark.sql import SparkSession
import urllib.parse

spark = SparkSession.builder.getOrCreate()

# Supabase Credentials (use dbutils.secrets.get in production)
SUPABASE_URL = "https://<your-project-ref>.supabase.co"
SUPABASE_SERVICE_KEY = "<your-service-role-key>"
DB_HOST = "db.<your-project-ref>.supabase.co"
DB_PASS = "<your-db-password>"

def process_partition(iterator):
    """
    Executes on the worker nodes. Initializes the model once per partition.
    """
    import easyocr
    import psycopg2
    import requests
    from io import BytesIO

    # 1. Initialize the model in RAM once per worker, not once per row
    print("Initializing EasyOCR Model on Worker...")
    reader = easyocr.Reader(['en', 'es'], gpu=False) # CE clusters are CPU-only
    
    # 2. Open a single database connection per worker
    conn = psycopg2.connect(
        host=DB_HOST,
        database="postgres",
        user="postgres",
        password=DB_PASS,
        port="5432"
    )
    cursor = conn.cursor()

    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
    }

    for row in iterator:
        job_id = row['job_id']
        storage_path = row['image_storage_path']
        
        try:
            # 3. Securely fetch the image buffer from the private Supabase bucket
            # We use the REST API here to avoid complex Hadoop S3A configurations
            encoded_path = urllib.parse.quote(storage_path)
            download_url = f"{SUPABASE_URL}/storage/v1/object/ocr_bucket/{encoded_path}"
            
            response = requests.get(download_url, headers=headers)
            response.raise_for_status()
            
            image_bytes = response.content
            
            # 4. Execute ML Inference
            result = reader.readtext(image_bytes, detail=0)
            extracted_text = " ".join(result)
            
            # 5. Write back to PostgreSQL
            update_query = """
                UPDATE ocr_jobs 
                SET status = 'completed', extracted_text = %s, updated_at = NOW()
                WHERE job_id = %s
            """
            cursor.execute(update_query, (extracted_text, job_id))
            conn.commit()
            
        except Exception as e:
            print(f"Failed to process job {job_id}: {str(e)}")
            cursor.execute(
                "UPDATE ocr_jobs SET status = 'failed', updated_at = NOW() WHERE job_id = %s", 
                (job_id,)
            )
            conn.commit()

    cursor.close()
    conn.close()

def run_batch_inference():
    print("Fetching pending OCR jobs...")
    
    # Standard JDBC read to get the pending queue into a Spark DataFrame
    jdbc_url = f"jdbc:postgresql://{DB_HOST}:5432/postgres"
    pending_jobs_df = spark.read.jdbc(
        url=jdbc_url,
        table="(SELECT job_id, image_storage_path FROM ocr_jobs WHERE status = 'pending') AS pending",
        properties={"user": "postgres", "password": DB_PASS, "driver": "org.postgresql.Driver"}
    )
    
    if pending_jobs_df.count() == 0:
        print("No pending jobs found.")
        return
        
    # Distribute the inference workload across the cluster
    pending_jobs_df.rdd.foreachPartition(process_partition)
    print("Batch inference completed.")

if __name__ == "__main__":
    run_batch_inference()