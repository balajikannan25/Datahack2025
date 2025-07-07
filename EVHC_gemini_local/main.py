import asyncio
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import uvicorn
from typing import Optional
from dotenv import load_dotenv
import logging
from pydantic import BaseModel

from controllers.Analyzing_video import analyzing_videos, upload_to_cloud_storage
from controllers.data_from_bigquery import get_data_from_bigquery
from controllers.delete_file import delete_from_gcs, delete_from_bigquery
from controllers.get_files_from_bucket import get_all_files
from controllers.get_video_file_data import get_video_file_data

load_dotenv()


# Initialize FastAPI app
app = FastAPI()

# CORS configuration
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Serve static files from "assets" folder
app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")


# Pydantic model for input validation
class FilenameRequest(BaseModel):
    filename: str


system_instructions = """You are an advanced EU Service Video Analysis model. Your task is to analyze the provided video. Follow the instructions below:

                1. **Conditions**: You must first verify below conditions before proceeding:
                   - Identify if the video is **related to Ford cars**.
                   - Identify if the video contains **audio**.
                   - Identify the **car** present in the Video.
                   - Identify if the car in the video is confirmed as a **Ford model**.
                   - Identify if the video is **clear enough** to analyze.

                2. Even one condition **failed** (i.e., the vehicle is not a Ford or the video has no sound or the car is not confirmed as a Ford model, or the video is not clear), respond with the following output format:\n
                   
                3. Analysis Process: If all initial conditions are satisfied (i.e., the vehicle is a Ford, the video has sound, the car is confirmed to be a Ford model, and the video is clear):

                       - Proceed with populating the following fields in the JSON format.
                       - Provide a summary and relevant evaluations as specified (e.g., license plate visibility, car on ramp, etc.).
                4. Output Format: Provide the following JSON structure as the output 
                    -if all conditions **passed**:
                        output response:

                            [
                                {
                                    "filename": "[name of the file]",
                                    "car_type": "passenger" or "Commercial Car",
                                    "service_related_video": "Yes" or "No",
                                    "sound_and_image": "Yes" or "No",
                                    "show_license_plate": "Yes" or "No",
                                    "car_on_ramp": "Yes" or "No" or "N/A",
                                    "service_advisor_or_technician_name": "name if available or No",
                                    "DealershipName": "Yes" or "No",
                                    "special_tools_tyres": "Yes" or "No" or "N/A",
                                    "customer_name": "Yes" or "No",
                                    "special_tools_brake_pad": "Yes" or "No" or "N/A",
                                    "Special_tools_disc": "Yes" or "No" or "N/A",
                                    "attached_offer_mentioned": "Yes" or "No",
                                    "correct_ending": "Yes" or "No",
                                    "show_license_plate_eval": "Out of 5 based on show_license_plate column",  
                                    "car_on_ramp_eval": "Out of 5 based on car_on_ramp column",  
                                    "service_advisor_or_technician_name_eval": "Out of 10 based on service_advisor_or_technician_name column",  
                                    "DealershipName_eval": "either 0 or 1 based on DealershipName column",  
                                    "customer_name_eval": "either 0 or 1 based on customer_name column",  
                                    "special_tools_tyres_eval": "Out of 20 based on special tools for tyres",  
                                    "special_tools_brake_pad_eval": "Out of 20 based on special tools for brake pad",  
                                    "Special_tools_disc_eval": "Out of 20 based on special tools for disc brakes",  
                                    "attached_offer_mentioned_eval": "Out of 10 based on attached_offer_mentioned column",  
                                    "approve_offer_mentioned_eval": "Out of 10",  
                                    "correct_ending_eval": "Out of 5 based on correct_ending column",  
                                    "total_points_eval": "Out of 100",  
                                    "percentage": "Percentage based on the points retrieved Out of 100%",  
                                    "battery_checked_eval": "Out of 100%",  
                                    "wind_screen_checked_eval": "Out of 100%", 
                                    "summary": "Generate a summary based on the given video"
                                }
                            ]

                        - if any condition **failed**:
                            output response:

                                [
                                {
                                    "filename": "[name of the file]",
                                    "car_type": "Non Ford",
                                    "service_related_video": "",
                                    "sound_and_image": "",
                                    "show_license_plate": "",
                                    "car_on_ramp": "",
                                    "service_advisor_or_technician_name": "",
                                    "DealershipName": "",
                                    "special_tools_tyres": "",
                                    "customer_name": "",
                                    "special_tools_brake_pad": "",
                                    "Special_tools_disc": "",
                                    "attached_offer_mentioned": "",
                                    "correct_ending": "",
                                    "show_license_plate_eval": "",  
                                    "car_on_ramp_eval": "",  
                                    "service_advisor_or_technician_name_eval": "",  
                                    "DealershipName_eval": "",  
                                    "customer_name_eval": "",  
                                    "special_tools_tyres_eval": "",  
                                    "special_tools_brake_pad_eval": "",  
                                    "Special_tools_disc_eval": "",  
                                    "attached_offer_mentioned_eval": "",  
                                    "approve_offer_mentioned_eval": "",  
                                    "correct_ending_eval": "",  
                                    "total_points_eval": "",  
                                    "percentage": "",  
                                    "battery_checked_eval": "",  
                                    "wind_screen_checked_eval": "", 
                                    "summary": ""
                                }
                            ]

                5. Output Constraints: Ensure every value is either a valid string or an empty string (null), and the response must always be in valid JSON format.

                Important Note: If conditions are failed or passed then respond with provided respective formats only. mainly if conditions failed then respond with  particular format and strictly follow the conditions. The main condition you should follow is, the ford car should be visible. If it is not visible then you must treat it as a failed condition.\n 
                 """


@app.post("/api/analyze-video")
async def analyze_video(
        url: Optional[str] = Form(None),  # Optional URL input
        file: Optional[UploadFile] = File(None),
):
    logger.info(f"API called: analyze_video with url={url}, file={file.filename if file else None}")

    if url and file:
        logger.error("Both 'url' and 'file' provided; raising exception.")
        raise HTTPException(status_code=422, detail="Provide only one of 'url' or 'file', not both.")
    if url:
        if url.startswith("gs://"):
            result = analyzing_videos(url, system_instructions, file_public_url=None)
            return result
        else:
            raise HTTPException(status_code=400, detail="Please provide only gcs url")
    else:
        result = upload_to_cloud_storage(file, system_instructions)
        return result


# Get the all the cloud storage files
@app.get("/api/get-file-urls")
async def get_urls():

    try:
        result = get_all_files()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get-video-data")
async def get_video_data():
    try:
        data = get_data_from_bigquery()
        return {"data": data}

    except HTTPException as e:
        raise e  # Re-raise the exception for the FastAPI response


@app.post("/api/single-record")
async def get_records(request: FilenameRequest):

    try:
        result = get_video_file_data(request.filename)
        return result
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/delete-data")
async def delete_data(request: FilenameRequest):
    filename = request.filename
    logger.info(f"Received request to delete file: {filename}")

    # Gather deletion tasks
    gcs_task = delete_from_gcs(filename)
    bigquery_task = delete_from_bigquery(filename)
    # Run both deletion tasks concurrently
    await asyncio.gather(gcs_task, bigquery_task)

    return {"message": f"Data for file '{filename}' successfully deleted from both GCS and BigQuery."}


@app.get("/{path:path}")
async def get_index(request: Request, path: str):
    return FileResponse("dist/index.html")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
