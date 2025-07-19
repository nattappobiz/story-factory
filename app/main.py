# =========================================================
#  1. Imports (จัดเรียงไว้ด้านบนทั้งหมด)
# =========================================================
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# .env file loader
from dotenv import load_dotenv

# FastAPI and Middleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Google Cloud & Vertex AI
import vertexai
from google.cloud import texttospeech
from vertexai.preview.vision_models import ImageGenerationModel
from vertexai.generative_models import GenerativeModel

# Application-specific imports
from app.services import tts_service, image_generation_service, gemini_service
from app.api import endpoints
from app import config # สมมติว่ามีการใช้ไฟล์ config

# =========================================================
#  2. Initial Setup
# =========================================================
# โหลด Environment Variables จากไฟล์ .env
load_dotenv()

# ตั้งค่า Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# =========================================================
#  3. Lifespan Manager (สำหรับ Startup/Shutdown Events)
# =========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    จัดการการเชื่อมต่อกับ Service ภายนอกตอนเปิดและปิดแอปพลิเคชัน
    """
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
        gemini_model = GenerativeModel("gemini-1.5-pro") # อัปเดตเป็นโมเดลที่แนะนำ

        logging.info("--- [STARTUP] Injecting dependencies into services... ---")
        tts_service.set_tts_client(google_tts_client)
        image_generation_service.set_image_model(imagen_model)
        gemini_service.set_gemini_model(gemini_model)

        logging.info("--- [SUCCESS] All services initialized and injected. ---")

    except (KeyError, ValueError) as e:
        logging.exception(f"CRITICAL STARTUP ERROR: {e}")

    yield
    
    logging.info("--- Application Shutdown ---")

# =========================================================
#  4. FastAPI App Instantiation and Middleware
# =========================================================
app = FastAPI(
    title="✨ AI Story Factory API ✨",
    description="API to turn ideas into animated stories.",
    version="1.0.0",
    lifespan=lifespan
