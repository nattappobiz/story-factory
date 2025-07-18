# --- START OF FILE: app/services/gemini_service.py (เวอร์ชัน Final) ---
import logging
import json
from typing import Optional, Dict

# [แก้ไข] Import library ที่ถูกต้องจาก Vertex AI SDK
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

# [ใหม่] Import Persona ที่เราสร้างขึ้น
from app.agents.personas import PERSONA_FOR_AGES_5_TO_7

# [แก้ไข] เราจะใช้ Dependency Injection เหมือน service อื่นๆ
# สร้างตัวแปร Global ไว้รอรับ Model จาก main.py
GEMINI_MODEL: Optional[GenerativeModel] = None

def set_gemini_model(model: GenerativeModel):
    """ฟังก์ชันนี้จะถูกเรียกโดย main.py ตอน Startup เพื่อตั้งค่า Model"""
    global GEMINI_MODEL
    GEMINI_MODEL = model
    logging.info("✅ Gemini 1.5 Pro Model has been successfully injected.")

def create_story_plan_with_persona(idea: str, age_group: str, image_style: str = "3D animated movie style") -> Dict:
    """
    สร้าง Story Plan ทั้งหมดโดยใช้ Persona ที่กำหนดไว้ (ฟังก์ชันหลักของเรา)
    """
    if not GEMINI_MODEL:
        raise Exception("Gemini Model has not been set. Call set_gemini_model() during application startup.")
        
    logging.info(f"Gemini Service: Creating story plan for age group {age_group} with idea: '{idea}'")

    # เลือก Persona ตามกลุ่มอายุ
    if age_group in ["3-5", "5-7", "8-10"]: # ทำให้รองรับกลุ่มอายุทั้งหมดที่เรามี
        system_prompt = PERSONA_FOR_AGES_5_TO_7 # ตอนนี้ยังใช้ Persona เดียวกันไปก่อน
    else:
        system_prompt = PERSONA_FOR_AGES_5_TO_7

    user_prompt = f"""
Here is the user's story idea: "{idea}"
The visual style for the images should be: "{image_style}"

Now, generate the complete JSON story plan according to the principles I provided.
"""

    # --- การเรียก Gemini API (Vertex AI SDK) ---
    generation_config = GenerationConfig(
        temperature=0.8,
        top_p=1.0,
        max_output_tokens=4096,
        response_mime_type="application/json", # บังคับให้ Gemini ตอบเป็น JSON
    )
    
    # สร้าง Prompt ที่สมบูรณ์
    full_prompt_parts = [
        Part.from_text(system_prompt),
        Part.from_text(user_prompt)
    ]

    try:
        response = GEMINI_MODEL.generate_content(
            full_prompt_parts,
            generation_config=generation_config,
        )
        
        logging.info("--- Gemini Raw Response (JSON Mode) ---")
        logging.info(response.text)
        logging.info("---------------------------------------")

        json_response = json.loads(response.text)
        
        # ตรวจสอบโครงสร้างพื้นฐานของ JSON ที่ได้กลับมา
        if not all(k in json_response for k in ["story_script", "image_prompts"]):
            raise ValueError("The AI response is missing required keys: 'story_script' or 'image_prompts'.")

        logging.info("Gemini Service: Story plan generated successfully via Persona.")
        return json_response

    except Exception as e:
        logging.exception("Gemini Service Error: Failed to generate or parse story plan.")
        raise e

# [เก็บไว้/ปรับปรุง] ฟังก์ชันเก่า สำหรับโหมด Manual
# เราจะทำให้มันเรียกใช้ฟังก์ชันใหม่ เพื่อลดความซ้ำซ้อน
def generate_full_script(user_prompt: str, image_style: str) -> Dict:
    """
    ฟังก์ชันสำหรับโหมด Manual จะเรียกใช้ Persona หลักด้วยกลุ่มอายุที่เป็นกลาง
    """
    logging.warning("Using legacy function 'generate_full_script'. Consider switching to persona-based generation.")
    return create_story_plan_with_persona(
        idea=user_prompt,
        age_group="5-7", # ใช้เป็นค่าเริ่มต้นสำหรับโหมด manual
        image_style=image_style
    )

# --- END OF FILE ---