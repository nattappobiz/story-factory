# --- START OF FILE: app/services/image_generation_service.py (เวอร์ชัน Dependency Injection) ---
import os
import time
from vertexai.preview.vision_models import ImageGenerationModel
from pathlib import Path
from typing import List, Optional
from app import config

# [แก้ไข] สร้างตัวแปร Global ไว้รอรับ Model แต่ยังไม่สร้าง
IMAGE_MODEL: Optional[ImageGenerationModel] = None

# [แก้ไข] สร้างฟังก์ชันสำหรับ "รับ" Model จากภายนอก
def set_image_model(model: ImageGenerationModel):
    """ฟังก์ชันนี้จะถูกเรียกโดย main.py ตอน Startup เพื่อตั้งค่า Model"""
    global IMAGE_MODEL
    IMAGE_MODEL = model
    print("✅ Vertex AI Image Generation Model has been successfully injected.")


def generate_images_from_prompts(
    prompts: List[str],
    story_id: str,
    aspect_ratio: str = "1:1"
) -> List[str]:
    """
    สร้างภาพจาก Prompts โดยใช้ Vertex AI พร้อมกลยุทธ์ Retry with Exponential Backoff
    """
    # [แก้ไข] ตรวจสอบ Model ที่ถูก set ไว้
    if not IMAGE_MODEL:
        raise Exception("Image Generation Model has not been set. Call set_image_model() during application startup.")
        
    print(f"Image Generation Service: Generating {len(prompts)} images with aspect ratio {aspect_ratio}...")
    
    image_paths = []
    job_output_dir = config.UPLOADS_DIR / story_id
    job_output_dir.mkdir(parents=True, exist_ok=True)

    for i, prompt in enumerate(prompts):
        print(f"  - Generating image {i+1}/{len(prompts)} for prompt: '{prompt[:70]}...'")
        
        max_retries = 3
        base_delay = 15

        for attempt in range(max_retries):
            try:
                images = IMAGE_MODEL.generate_images(
                    prompt=prompt,
                    number_of_images=1,
                    aspect_ratio=aspect_ratio
                )

                image_bytes = images[0]._image_bytes
                if not image_bytes:
                    raise ValueError("API returned an empty image.")

                file_path = job_output_dir / f"image_{i}.png"
                with open(file_path, "wb") as f:
                    f.write(image_bytes)
                image_paths.append(str(file_path))
                print(f"  - ✅ Image saved to -> {file_path}")
                break 

            except Exception as e:
                print(f"  - ⚠️ Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"  - Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print(f"  - ❌ All retries failed for prompt.")
                    raise Exception(f"Failed to generate image after {max_retries} attempts.") from e
            
    print("Image Generation Service: All images generated successfully.")
    return image_paths