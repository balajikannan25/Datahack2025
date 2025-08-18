# Electronic Vehicle Health Check (eVHC) – AI-Powered Video Assessment

## 📌 Project Overview

This project is an **AI-driven electronic vehicle health check (eVHC)** system that automates vehicle inspection video assessments using **Google Vertex AI (gemini-2.5-pro)**.
The solution replaces manual quality checks with **Generative AI–powered automation**, delivering faster, more accurate evaluations, structured insights, and score generation.

---

## 🔎 Background

Traditionally, in the **Dealer Incentive Program**, technicians recorded repair videos which were manually checked for quality before providing quotes. This process was:

* Time-consuming
* Prone to human errors
* Difficult to scale

With this solution, video assessments are automated using **Generative AI**, making the process more **efficient, reliable, and scalable**.

---

## 🚀 Solution Overview

### ✨ Features

* **AI-Powered Analysis** → Automated inspection and diagnostic video analysis
* **Streamlined Insights** → Generates structured summaries and scores
* **Automation at Scale** → Reduces manual review effort, improves turnaround time

---

### 🔧 Capabilities

* **Video Management**

  * URL extraction & video downloading
  * Video type classification

* **AI-Powered Content Analysis**

  * Object recognition
  * Vehicle condition assessment
  * Speech-to-text transcription

* **Data Handling**

  * Data extraction & validation
  * Integration with **Google BigQuery** & **Cloud Storage**
  * Error handling & logging

* **Results**

  * Structured summary generation
  * Insights for Dealer Incentive programs

---

## 📂 Project Structure

```
EVHC_gemini_local/
│── controllers/
│    ├── analyzing_video.py        # Analyze videos using Vertex AI LLM
│    ├── data_from_bigquery.py     # Fetch data from BigQuery
│    ├── delete_file.py            # Delete files from GCP bucket or BigQuery
│    ├── get_files_from_bucket.py  # Fetch data from Cloud Storage
│    ├── get_video_file_data.py    # Fetch video details from BigQuery
│
│── dist/                          # Frontend UI
│── main.py                        # Main entry point
│── requirements.txt               # Python dependencies
│── Dockerfile                     # Container setup
```

---

## ⚙️ Installation & Setup

### ✅ Prerequisites

1. **Python 3.10+**
2. **Google Cloud SDK** (for authentication)
3. **Docker** (if running containerized version)
4. Clone the repository:

   ```bash
   git clone https://github.com/vignesh-ds/Datahack2025.git
   cd Datahack2025/EVHC_gemini_local
   ```

---

### 🔑 Authentication

Before running the script, authenticate with Google Cloud:

```bash
gcloud auth application-default login
```

This allows access to:

* **GCP Cloud Storage** (for video files)
* **BigQuery** (for data storage & queries)
* **Vertex AI** (for Generative AI model gemini-2.5-pro)

---

### ▶️ Running with Python (Non-Docker Setup)

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
2. Run the main script:

   ```bash
   python main.py
   ```

---

### 🐳 Running with Docker

1. Build the Docker image:

   ```bash
   docker build -t evhc_gemini_local .
   ```
2. Run the container:

   ```bash
   docker run -d -p 8080:8080 evhc_gemini_local
   ```

---

## 🏃 Running the Application

1. **Provide Input** → Supply video URLs for processing
2. **Execution** → System automatically downloads, analyzes, classifies, and extracts data
3. **Output** → Review structured insights, scores, and summaries

---

## 🔗 Tech Stack

* **Google Vertex AI (gemini-2.5-pro)** → Generative AI model for analysis
* **Google BigQuery** → Data storage & querying
* **Google Cloud Storage** → Video storage
* **Python 3.10+** → Core development
* **Docker** → Containerization
* **FastAPI (optional for API layer)**
