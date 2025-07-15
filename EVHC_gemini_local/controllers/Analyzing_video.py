import logging
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
import json
import os
from fastapi import HTTPException, File, UploadFile
from google.cloud import storage, bigquery
from dotenv import load_dotenv
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
storage_client = storage.Client()
bigquery_client = bigquery.Client()
project_id = os.environ["PROJECT_ID"]
bucket_id = os.environ["BUCKET_ID"]
table_id = os.environ["BIGQUERY_TABLE_ID"]
bucket_folder = os.environ["BUCKET_FOLDER"]


def insert_into_bigquery(data_to_insert):
    logger.info(f"Final JSON response with video URL: {data_to_insert}")
    try:
        query = f"""
            INSERT INTO `{project_id}.{table_id}` 
            (filename, car_type, service_related_video, sound_and_image, show_license_plate,
             car_on_ramp, service_advisor_or_technician_name, DealershipName,
             special_tools_tyres, customer_name, special_tools_brake_pad,
             Special_tools_disc, attached_offer_mentioned, correct_ending,
             show_license_plate_eval, car_on_ramp_eval, service_advisor_or_technician_name_eval,
             DealershipName_eval, customer_name_eval, special_tools_tyres_eval,
             special_tools_brake_pad_eval, Special_tools_disc_eval,
             attached_offer_mentioned_eval, approve_offer_mentioned_eval, correct_ending_eval,
             total_points_eval, percentage, battery_checked_eval, wind_screen_checked_eval,
             summary, video_url)
            VALUES (@filename, @car_type, @service_related_video, @sound_and_image, @show_license_plate,
                    @car_on_ramp, @service_advisor_or_technician_name, @DealershipName,
                    @special_tools_tyres, @customer_name, @special_tools_brake_pad,
                    @Special_tools_disc, @attached_offer_mentioned, @correct_ending,
                    @show_license_plate_eval, @car_on_ramp_eval, @service_advisor_or_technician_name_eval,
                    @DealershipName_eval, @customer_name_eval, @special_tools_tyres_eval,
                    @special_tools_brake_pad_eval, @Special_tools_disc_eval,
                    @attached_offer_mentioned_eval, @approve_offer_mentioned_eval, @correct_ending_eval,
                    @total_points_eval, @percentage, @battery_checked_eval, @wind_screen_checked_eval,
                    @summary, @video_url)
        """

        # Define the job configuration with parameters
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("filename", "STRING", data_to_insert["filename"]),
                bigquery.ScalarQueryParameter("car_type", "STRING", data_to_insert["car_type"]),
                bigquery.ScalarQueryParameter("service_related_video", "STRING", data_to_insert["service_related_video"]),
                bigquery.ScalarQueryParameter("sound_and_image", "STRING", data_to_insert["sound_and_image"]),
                bigquery.ScalarQueryParameter("show_license_plate", "STRING", data_to_insert["show_license_plate"]),
                bigquery.ScalarQueryParameter("car_on_ramp", "STRING", data_to_insert["car_on_ramp"]),
                bigquery.ScalarQueryParameter("service_advisor_or_technician_name", "STRING",
                                              data_to_insert["service_advisor_or_technician_name"]),
                bigquery.ScalarQueryParameter("DealershipName", "STRING", data_to_insert["DealershipName"]),
                bigquery.ScalarQueryParameter("special_tools_tyres", "STRING", data_to_insert["special_tools_tyres"]),
                bigquery.ScalarQueryParameter("customer_name", "STRING", data_to_insert["customer_name"]),
                bigquery.ScalarQueryParameter("special_tools_brake_pad", "STRING",
                                              data_to_insert["special_tools_brake_pad"]),
                bigquery.ScalarQueryParameter("Special_tools_disc", "STRING", data_to_insert["Special_tools_disc"]),
                bigquery.ScalarQueryParameter("attached_offer_mentioned", "STRING",
                                              data_to_insert["attached_offer_mentioned"]),
                bigquery.ScalarQueryParameter("correct_ending", "STRING", data_to_insert["correct_ending"]),
                bigquery.ScalarQueryParameter("show_license_plate_eval", "STRING",
                                              data_to_insert["show_license_plate_eval"]),
                bigquery.ScalarQueryParameter("car_on_ramp_eval", "STRING", data_to_insert["car_on_ramp_eval"]),
                bigquery.ScalarQueryParameter("service_advisor_or_technician_name_eval", "STRING",
                                              data_to_insert["service_advisor_or_technician_name_eval"]),
                bigquery.ScalarQueryParameter("DealershipName_eval", "STRING", data_to_insert["DealershipName_eval"]),
                bigquery.ScalarQueryParameter("customer_name_eval", "STRING", data_to_insert["customer_name_eval"]),
                bigquery.ScalarQueryParameter("special_tools_tyres_eval", "STRING",
                                              data_to_insert["special_tools_tyres_eval"]),
                bigquery.ScalarQueryParameter("special_tools_brake_pad_eval", "STRING",
                                              data_to_insert["special_tools_brake_pad_eval"]),
                bigquery.ScalarQueryParameter("Special_tools_disc_eval", "STRING",
                                              data_to_insert["Special_tools_disc_eval"]),
                bigquery.ScalarQueryParameter("attached_offer_mentioned_eval", "STRING",
                                              data_to_insert["attached_offer_mentioned_eval"]),
                bigquery.ScalarQueryParameter("approve_offer_mentioned_eval", "STRING",
                                              data_to_insert["approve_offer_mentioned_eval"]),
                bigquery.ScalarQueryParameter("correct_ending_eval", "STRING", data_to_insert["correct_ending_eval"]),
                bigquery.ScalarQueryParameter("total_points_eval", "STRING", data_to_insert["total_points_eval"]),
                bigquery.ScalarQueryParameter("percentage", "STRING", data_to_insert["percentage"]),
                bigquery.ScalarQueryParameter("battery_checked_eval", "STRING", data_to_insert["battery_checked_eval"]),
                bigquery.ScalarQueryParameter("wind_screen_checked_eval", "STRING",
                                              data_to_insert["wind_screen_checked_eval"]),
                bigquery.ScalarQueryParameter("summary", "STRING", data_to_insert["summary"]),
                bigquery.ScalarQueryParameter("video_url", "STRING", data_to_insert["video_url"]),
            ]
        )
        # Execute the query
        query_job = bigquery_client.query(query, job_config=job_config)
        query_job.result()  # Wait for the job to complete
    except Exception as e:
        print(e)

    logging.info(f"Data inserted into BigQuery for filename: {data_to_insert['filename']}")


def clean_json_data(input_data):
    logger.info("Cleaning the JSON response data")
    cleaned_data = input_data.replace('```json', '').replace('```', '').replace('\n', ' ').strip()
    return cleaned_data


def generate_content_from_url(url, system_instructions):
    model = GenerativeModel("gemini-1.5-flash-002", system_instruction=system_instructions)
    video_file = Part.from_uri(
        uri=url,
        mime_type="video/mp4",
    )
    file_name = url.split("/")[-1]
    example_output = """[
    {
        "filename": "example_file.mp4",
        "car_type": "passenger",
        "service_related_video": "Yes",
        "sound_and_image": "Yes",
        "show_license_plate": "Yes",
        "car_on_ramp": "Yes",
        "service_advisor_or_technician_name": "Shane",
        "DealershipName": "Yes",
        "special_tools_tyres": "Yes",
        "customer_name": "Yes",
        "special_tools_brake_pad": "Yes",
        "Special_tools_disc": "Yes",
        "attached_offer_mentioned": "Yes",
        "correct_ending": "Yes",
        "show_license_plate_eval": "5",
        "car_on_ramp_eval": "5",
        "service_advisor_or_technician_name_eval": "10",
        "DealershipName_eval": "1",
        "customer_name_eval": "1",
        "special_tools_tyres_eval": "20",
        "special_tools_brake_pad_eval": "20",
        "Special_tools_disc_eval": "20",
        "attached_offer_mentioned_eval": "10",
        "approve_offer_mentioned_eval": "10",
        "correct_ending_eval": "5",
        "total_points_eval": "100",
        "percentage": "100%",
        "battery_checked_eval": "100%",
        "wind_screen_checked_eval": "100%",
        "summary": "description of the video"
    }
]"""
    prompt = f"""
                You are an advanced EU Service Video Analysis your task is to Analyze the provided Video and filename is "{file_name}",

                **Output format**: Provide only valid JSON as an output response and every value should be a string or an empty string (null)
                
                **Example output format**:
                {example_output}
                In output you should not include any other format other than JSON.
                """
    contents = [video_file, prompt]

    response = model.generate_content(contents)
    print(response.text)
    cleaned_response = clean_json_data(response.text)
    json_response = json.loads(cleaned_response)
    if isinstance(json_response, dict) and "data" in json_response:
        logger.error("Error in response data in uploaded file")
        raise HTTPException(status_code=400, detail=str(json_response["data"]))
    else:
        return json_response


def analyzing_videos(url, system_instructions, file_public_url):
    try:
        generated_result = generate_content_from_url(url, system_instructions)
        for item in generated_result:
            item["video_url"] = file_public_url
        insert_into_bigquery(generated_result[0])
        summary = [generated_result[0]['summary']]

        return {
            "response": generated_result,
            "summary": summary
        }
    except Exception as e:
        pass


def upload_to_gcs(file: UploadFile, bucket_name: str, folder_name: str):
    """Uploads a file to a specified folder in GCS and returns the gs:// URL."""
    try:
        bucket = storage_client.get_bucket(bucket_name)

        # Construct the full path for the file inside the folder
        blob_name = f"{folder_name}/{file.filename}"
        blob = bucket.blob(blob_name)

        # Upload the file to the specified folder in the bucket
        blob.upload_from_file(file.file, content_type=file.content_type)

        # Return the gs:// URL for the file
        return {"gcs_url": f"gs://{bucket_name}/{blob.name}", "file_public_url": f"https://storage.cloud.google.com/{bucket_name}/{blob.name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def upload_to_cloud_storage(file, system_instructions):
    if file.content_type not in ["video/mp4", "video/mkv", "video/avi"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only MP4, MKV, and AVI files are allowed.")
    bucket_name = bucket_id
    # Upload file to the specific folder in GCS
    url_result = upload_to_gcs(file, bucket_name, bucket_folder)
    result = analyzing_videos(url_result["gcs_url"], system_instructions, url_result["file_public_url"])
    return result
