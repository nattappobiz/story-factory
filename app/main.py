from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path
from contextlib import asynccontextmanager
import logging
from fastapi.middleware.cors import CORSMiddleware

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
from vertexai.generative_models import GenerativeModel
from app.services import tts_service, image_generation_service, gemini_service
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
        gemini_model = GenerativeModel("gemini-2.5-pro")

        logging.info("--- [STARTUP] Injecting dependencies into services... ---")
        tts_service.set_tts_client(google_tts_client)
        image_generation_service.set_image_model(imagen_model)
        gemini_service.set_gemini_model(gemini_model)

        logging.info("--- [SUCCESS] All services initialized and injected. ---")

    except (KeyError, ValueError, Exception) as e:
        logging.exception("CRITICAL STARTUP ERROR: Failed to initialize Google Cloud services.")

    yield 
    logging.info("--- Application Shutdown ---")

app = FastAPI(title="Story Factory API", lifespan=lifespan)

# แนะนำให้ใส่ origin เป็นแบบไม่มี '/' ท้าย และควรใส่ตามจริงเท่านั้น
