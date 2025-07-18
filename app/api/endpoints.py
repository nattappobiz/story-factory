# --- START OF FILE: app/api/endpoints.py (เวอร์ชันแก้ไข read of closed file) ---
from fastapi import APIRouter, HTTPException, BackgroundTasks, Form, File, UploadFile
from pydantic import BaseModel
from typing import List
import shelve
from filelock import FileLock
import uuid
import json
from pathlib import Path # [ใหม่] Import Pathlib
import shutil # [ใหม่] Import shutil

from app.services import agent_service, gemini_service

router = APIRouter()
DB_PATH = "job_statuses.db"
LOCK_PATH = "job_statuses.db.lock"

# === Endpoint หลักสำหรับ Workflow อัตโนมัติ (Magic Button) ===
class AgentCreateRequest(BaseModel):
    prompt: str
    age_group: str = "5-7"
    voice_name: str = "en-US-Wavenet-C"
    music_filename: str = "calm.mp3"
    aspect_ratio: str = "9:16"
    music_volume: float = 0.3
    transition_style: str = "fade"

@router.post("/agent/create-video", status_code=202)
async def agent_create_video_endpoint(request: AgentCreateRequest, background_tasks: BackgroundTasks):
    try:
        job_id = agent_service.start_video_creation_job(
            background_tasks=background_tasks, prompt=request.prompt, age_group=request.age_group,
            voice_name=request.voice_name, music_filename=request.music_filename,
            aspect_ratio=request.aspect_ratio, music_volume=request.music_volume,
            transition_style=request.transition_style
        )
        return {"message": "Video creation process started.", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start agent job: {str(e)}")

# === Endpoint กลางสำหรับตรวจสอบสถานะ ===
@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    with FileLock(LOCK_PATH, timeout=10):
        with shelve.open(DB_PATH, flag='r') as job_statuses:
            status = job_statuses.get(job_id)
            if not status: raise HTTPException(status_code=404, detail="Job ID not found.")
            return status

# === Endpoint สำหรับ Workflow แบบ Manual ===
class ManualScriptRequest(BaseModel):
    prompt: str
    image_style: str

@router.post("/manual/generate-script", status_code=200)
async def manual_generate_script_endpoint(request: ManualScriptRequest):
    try:
        return gemini_service.generate_full_script(request.prompt, request.image_style)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/manual/compile-video", status_code=202)
async def manual_compile_video_endpoint(
    background_tasks: BackgroundTasks, 
    story_script_json: str = Form(...), 
    voice_name: str = Form(...),
    music_filename: str = Form(...), 
    aspect_ratio: str = Form(...), 
    music_volume: float = Form(...),
    transition_style: str = Form(...),
    images: List[UploadFile] = File(...)
):
    """
    Endpoint สำหรับการ Compile วิดีโอ (โหมด Manual) ที่แก้ไขแล้ว
    """
    job_id = str(uuid.uuid4())
    
    # --- [แก้ไข] บันทึกไฟล์ที่อัปโหลดลง Disk ทันที ---
    upload_dir = Path("generated_content") / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    temp_image_paths = []
    for image in images:
        file_path = upload_dir / image.filename
        try:
            # อ่านข้อมูลจากไฟล์ที่ยังเปิดอยู่ แล้วเขียนลงไฟล์ใหม่ของเรา
            with open(file_path, "wb") as buffer:
                content = await image.read() 
                buffer.write(content)
            temp_image_paths.append(str(file_path))
        finally:
            await image.close()
    # -----------------------------------------------

    # [แก้ไข] เรียกใช้ service โดยส่ง "List ของ Path" แทน "List ของ UploadFile"
    job_id_from_service = agent_service.start_manual_compilation_job(
        background_tasks=background_tasks,
        job_id=job_id,
        story_script_json=story_script_json,
        image_paths=temp_image_paths, # <-- ส่งเป็น Path
        voice_name=voice_name,
        music_filename=music_filename,
        aspect_ratio=aspect_ratio,
        music_volume=music_volume,
        transition_style=transition_style
    )
    return {"message": "Manual video compilation started.", "job_id": job_id_from_service}

# --- END OF FILE ---