# --- START OF FILE: app/main.py (Final Version) ---
from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path
from contextlib import asynccontextmanager
import logging

# [แก้ไข] Import config เข้ามาใช้งาน
from app import config

# ตั้งค่า Logging (ถูกต้องแล้ว)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# [แก้ไข] Import library และ service ทั้งหมดที่เราต้องการ
import vertexai
from google.cloud import texttospeech
from vertexai.preview.vision_models import ImageGenerationModel
from vertexai.generative_models import GenerativeModel # <-- เพิ่ม
from app.services import tts_service, image_generation_service, gemini_service # <-- เพิ่ม gemini_service
from app.api import endpoints

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("--- Application Startup: Initializing Google Cloud services... ---")
    try:
        project_id = os.environ["GCP_PROJECT_ID"]
        location = os.environ.get("GCP_LOCATION", "us-central1")
        
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            raise ValueError("CRITICAL: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        
        logging.info(f"--- [STARTUP] Project: {project_id}, Location: {location} ---")
        logging.info("--- [STARTUP] Initializing Vertex AI... ---")
        vertexai.init(project=project_id, location=location)
        
        logging.info("--- [STARTUP] Creating API clients and models... ---")
        google_tts_client = texttospeech.TextToSpeechClient()
        imagen_model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")
        gemini_model = GenerativeModel("gemini-2.5-pro") # <-- เพิ่ม
        
        logging.info("--- [STARTUP] Injecting dependencies into services... ---")
        tts_service.set_tts_client(google_tts_client)
        image_generation_service.set_image_model(imagen_model)
        gemini_service.set_gemini_model(gemini_model) # <-- เพิ่ม
        
        logging.info("--- [SUCCESS] All services initialized and injected. ---")

    except (KeyError, ValueError, Exception) as e:
        logging.exception("CRITICAL STARTUP ERROR: Failed to initialize Google Cloud services.")
    
    yield 
    logging.info("--- Application Shutdown ---")

app = FastAPI(title="Story Factory API", lifespan=lifespan)

# [แก้ไข] ใช้ app.mount แค่บรรทัดเดียว โดยอ้างอิงจาก config
app.mount("/content", StaticFiles(directory=config.CONTENT_DIR), name="content")

# [แก้ไข] ลบบรรทัดที่ซ้ำซ้อนและประกาศตัวแปรที่ไม่จำเป็นออก
# STATIC_CONTENT_DIR = Path(__file__).parent / "generated_content" <-- ลบ
# app.mount("/content", StaticFiles(directory=STATIC_CONTENT_DIR), name="content") <-- ลบ

app.include_router(endpoints.router, prefix="/api")

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Story Factory! Visit /docs to try the API."}

# --- END OF FILE: app/main.py ---