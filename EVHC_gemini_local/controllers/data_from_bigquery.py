import os
from fastapi import HTTPException
from google.cloud import storage, bigquery
import logging
storage_client = storage.Client()
bigquery_client = bigquery.Client()

bucket_id = os.environ["BUCKET_ID"]
table_id = os.environ["BIGQUERY_TABLE_ID"]
bucket_folder = os.environ["BUCKET_FOLDER"]
project_id = os.environ["PROJECT_ID"]
# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_data_from_bigquery():

    # Execute a simple query to retrieve data
    query = f"SELECT * FROM `{project_id}.{table_id}`"  # Modify this query as needed

    try:
        query_job = bigquery_client.query(query)  # Make an API request
        results = query_job.result()  # Wait for the job to complete

        data = [dict(row) for row in results]  # Convert results to a list of dictionaries

        return data

    except Exception as e:
        logger.error(f"Error fetching data from BigQuery: {e}")
        raise HTTPException(status_code=500, detail=str(e))