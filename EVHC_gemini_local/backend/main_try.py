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
import time
import io
import requests
from starlette.datastructures import UploadFile as StarletteUploadFile
from pytubefix import YouTube
from pytubefix.cli import on_progress
# Load environment variables first
load_dotenv()

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detect Cloud Run environment
def is_cloud_run():
    """Detect if running in Google Cloud Run"""
    return os.getenv('K_SERVICE') is not None

def is_production():
    """Determine if running in production environment"""
    return (
        os.getenv("ENVIRONMENT") == "production" or
        is_cloud_run() or
        os.getenv('GAE_ENV') == 'standard'
    )

# Configure Ford proxy settings
def setup_ford_proxy():
    """Setup Ford corporate proxy settings - ONLY for local development"""
    if is_production():
        logger.info("Production/Cloud environment detected - skipping proxy configuration")
        return {}
    
    proxy_settings = {
        'http_proxy': "http://internet.ford.com:83",
        'https_proxy': "http://internet.ford.com:83",
        'HTTP_PROXY': "http://internet.ford.com:83",
        'HTTPS_PROXY': "http://internet.ford.com:83",
        'NO_PROXY': ".ford.com,localhost,127.0.0.1,19.*",
        'no_proxy': ".ford.com,localhost,127.0.0.1,19.*"
    }
    
    for key, value in proxy_settings.items():
        os.environ[key] = value
        
    logger.info("Ford proxy settings configured for local development")
    return proxy_settings

# Setup proxy at startup
PROXY_SETTINGS = setup_ford_proxy()

from controllers.Analyzing_video import analyzing_videos, upload_to_cloud_storage
from controllers.data_from_bigquery import get_data_from_bigquery
from controllers.delete_file import delete_from_gcs, delete_from_bigquery
from controllers.get_files_from_bucket import get_all_files
from controllers.get_video_file_data import get_video_file_data

# Custom UploadFile class with content_type support
class CustomUploadFile(StarletteUploadFile):
    def __init__(self, filename: str, file: io.BytesIO, content_type: str):
        super().__init__(filename=filename, file=file)
        self._content_type = content_type

    @property
    def content_type(self):
        return self._content_type

# Initialize FastAPI app
app = FastAPI(
    title="AI EVHC Video Analyzer",
    description="Hyundai Service Video Analysis Platform",
    version="1.0.0"
)

# CORS configuration
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conditionally mount static files
if os.path.exists("dist/assets"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

# Pydantic model for input validation
class FilenameRequest(BaseModel):
    filename: str

def get_proxy_session():
    """Create a requests session with appropriate proxy configuration"""
    session = requests.Session()
    
    # Only configure proxy for local development
    if not is_production():
        proxies = {
            'http': 'http://internet.ford.com:83',
            'https': 'http://internet.ford.com:83'
        }
        session.proxies.update(proxies)
        logger.info("Proxy session configured for local development")
    else:
        logger.info("Direct connection session configured for production")
    
    # Set timeout and retry configuration
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

# System instructions for AI analysis
system_instructions = """You are an advanced EU Service Video Analysis model."""

def youtube_fetch_video_as_file(url: str) -> CustomUploadFile:
    yt = YouTube(url, on_progress_callback=on_progress)
    ys = yt.streams.get_highest_resolution()
    buffer = io.BytesIO()
    ys.stream_to_buffer(buffer)
    buffer.seek(0)
    return CustomUploadFile(filename=ys.default_filename, file=buffer, content_type="video/mp4")


# Health check endpoint for Cloud Run
@app.get("/health")
async def health_check():
    """Health check endpoint for Google Cloud Run"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "environment": "production" if is_production() else "development",
        "cloud_run": is_cloud_run(),
        "project_id": os.getenv("PROJECT_ID"),
        "bucket_id": os.getenv("BUCKET_ID"),
        "table_id": os.getenv("BIGQUERY_TABLE_ID")
    }

@app.post("/api/analyze-video")
async def analyze_video(
        url: Optional[str] = Form(None),
        file: Optional[UploadFile] = File(None),
):
    logger.info(f"API called: analyze_video with url={url}, file={file.filename if file else None}")
    logger.info(f"Environment: {'production' if is_production() else 'development'}, Cloud Run: {is_cloud_run()}")

    if sum(bool(x) for x in [url, file]) != 1:
        logger.error("Invalid number of inputs; raising exception.")
        raise HTTPException(status_code=422, detail="Provide only one of 'url' or 'file'.")

    try:
        if url:
            if url.startswith("gs://"):
                result = analyzing_videos(url, system_instructions, file_public_url=None)
                return result
            elif "youtube.com" in url or "youtu.be" in url:
                logger.info(f"Processing YouTube URL: {url}")
                video_file = youtube_fetch_video_as_file(url)
                result = upload_to_cloud_storage(video_file, system_instructions)
                return result
            else:
                raise HTTPException(status_code=400, detail="URL must be a GCS or YouTube link.")

        if file:
            result = upload_to_cloud_storage(file, system_instructions)
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in analyze_video: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Test YouTube download specifically
@app.post("/api/test-youtube")
async def test_youtube(url: str = Form(...)):
    """Test YouTube download functionality"""
    try:
        logger.info(f"Testing YouTube download for: {url}")
        video_file = youtube_fetch_video_as_file(url)
        
        return {
            "status": "success",
            "filename": video_file.filename,
            "content_type": video_file.content_type,
            "size": len(video_file.file.getvalue()),
            "environment": "production" if is_production() else "development",
            "cloud_run": is_cloud_run()
        }
        
    except Exception as e:
        logger.error(f"YouTube test failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "environment": "production" if is_production() else "development",
            "cloud_run": is_cloud_run()
        }

@app.get("/api/test-connection")
async def test_connection():
    """Test network connectivity"""
    try:
        session = get_proxy_session()
        
        test_urls = ["https://httpbin.org/ip", "https://www.google.com"]
        if not is_production():
            test_urls.append("https://lts.eu.prod.citnow.com")
        
        results = {}
        for test_url in test_urls:
            try:
                response = session.get(test_url, timeout=30)
                results[test_url] = {
                    "status": "success",
                    "status_code": response.status_code,
                    "response_size": len(response.content)
                }
                if "httpbin.org/ip" in test_url:
                    try:
                        results[test_url]["ip_info"] = response.json()
                    except:
                        pass
            except Exception as e:
                results[test_url] = {"status": "failed", "error": str(e)}
        
        return {
            "environment": "production" if is_production() else "development",
            "cloud_run": is_cloud_run(),
            "proxy_configured": not is_production(),
            "test_results": results
        }
        
    except Exception as e:
        return {"error": str(e), "environment": "production" if is_production() else "development"}

@app.get("/api/get-file-urls")
async def get_urls():
    try:
        result = get_all_files()
        return result
    except Exception as e:
        logger.error(f"Error getting file URLs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/get-video-data")
async def get_video_data():
    try:
        data = get_data_from_bigquery()
        return {"data": data}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting video data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/single-record")
async def get_records(request: FilenameRequest):
    try:
        result = get_video_file_data(request.filename)
        return result
    except Exception as e:
        logger.error(f"Error getting single record: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/delete-data")
async def delete_data(request: FilenameRequest):
    filename = request.filename
    logger.info(f"Received request to delete file: {filename}")

    try:
        gcs_task = delete_from_gcs(filename)
        bigquery_task = delete_from_bigquery(filename)
        await asyncio.gather(gcs_task, bigquery_task)

        return {"message": f"Data for file '{filename}' successfully deleted from both GCS and BigQuery."}
    except Exception as e:
        logger.error(f"Error deleting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Serve React app for all other routes
@app.get("/{path:path}")
async def get_index(request: Request, path: str):
    """Serve React app for all routes (SPA routing support)"""
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    index_path = "dist/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"message": "Frontend not available", "path": path}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
