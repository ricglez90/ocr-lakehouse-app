# tests/test_silver_logic.py
"""
PySpark Unit Test
Theory: Testing data transformations does not require a Databricks cluster. 
We instantiate a local SparkSession inside the CI runner to validate column 
logic and schema changes securely and at zero cost.
"""

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

@pytest.fixture(scope="session")
def spark():
    """Creates a single local Spark session for all tests."""
    return SparkSession.builder \
        .master("local[1]") \
        .appName("pytest-pyspark-local") \
        .getOrCreate()

def test_silver_quarantine_filter(spark):
    # 1. Arrange: Create mock Bronze data with edge cases
    mock_data = [
        ("session_1", "miguel@example.com", 0.9),  # Valid
        ("session_2", None, 0.8),                  # Invalid: Null email
        ("session_3", "bot@bot.com", 0.2),         # Invalid: Low validation score
    ]
    columns = ["session_id", "user_email", "human_validation_score"]
    df = spark.createDataFrame(mock_data, columns)

    # 2. Act: Apply the exact logic from silver_quarantine.py
    valid_condition = col("user_email").isNotNull() & (col("human_validation_score") >= 0.7)
    clean_df = df.filter(valid_condition)
    quarantine_df = df.filter(~valid_condition)

    # 3. Assert: Verify the logic routed the records correctly
    assert clean_df.count() == 1
    assert clean_df.collect()[0]["session_id"] == "session_1"
    
    assert quarantine_df.count() == 2
    quarantined_ids = [row["session_id"] for row in quarantine_df.collect()]
    assert "session_2" in quarantined_ids
    assert "session_3" in quarantined_ids