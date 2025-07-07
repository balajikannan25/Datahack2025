from google.cloud import storage, bigquery
import os
import logging
from fastapi import HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bigquery_client = bigquery.Client()

table_id = os.environ["BIGQUERY_TABLE_ID"]
bucket_folder = os.environ["BUCKET_FOLDER"]
project_id = os.environ["PROJECT_ID"]

def get_video_file_data(filename):

    try:
        logging.info(f"Received filename: {filename}")

        query = f"""
        SELECT * FROM `{project_id}.{table_id}` 
        WHERE filename = @filename
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("filename", "STRING", filename),
            ]
        )

        query_job = bigquery_client.query(query, job_config=job_config)
        results = query_job.result()

        records = [dict(row) for row in results]
        logging.info(f"Records fetched: {records}")

        if not records:
            raise HTTPException(status_code=404, detail="No records found for the given filename")

        summary_list = [record.pop('summary') for record in records if 'summary' in record]

        return {"records": records, "summary": summary_list}

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))