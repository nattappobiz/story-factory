# --- START OF FILE: app/services/agent_service.py (เวอร์ชันแก้ไข SyntaxError) ---

import logging
import uuid
import os
import json
import shutil
import shelve
from filelock import FileLock
from pathlib import Path
from typing import List
from fastapi import BackgroundTasks

from app import config
from . import gemini_service
from . import image_generation_service
from . import video_service
from . import google_drive_service

# --- สวิตช์สำหรับเปิด/ปิดโหมดดีบัก ---
DEBUG_BYPASS_VIDEO_CREATION = False

DB_PATH = "job_statuses.db"
LOCK_PATH = "job_statuses.db.lock"

def update_job_status(job_id: str, status: str, stage: str = "", error: str = "", video_url: str = "", story_text: str = ""):
    with FileLock(LOCK_PATH, timeout=10):
        with shelve.open(DB_PATH, writeback=True) as db:
            if job_id not in db: db[job_id] = {}
            db[job_id]['status'] = status
            if stage: db[job_id]['stage'] = stage
            if error: db[job_id]['error'] = error
            if video_url: db[job_id]['video_url'] = video_url
            if story_text: db[job_id]['story_text'] = story_text

def bypass_video_creation(output_filename: str) -> str:
    logging.warning("!!! BYPASSING VIDEO CREATION (DEBUG MODE IS ON) !!!")
    placeholder_video_path = config.ASSETS_DIR / "placeholder.mp4"
    if not placeholder_video_path.is_file():
        raise FileNotFoundError("Bypass failed: assets/placeholder.mp4 not found.")
    final_video_path = config.CONTENT_DIR / output_filename
    shutil.copy(placeholder_video_path, final_video_path)
    return str(final_video_path)

# === Workflow สำหรับโหมดอัตโนมัติ (Magic Mode) ===
def agent_orchestrator_workflow(
    job_id: str, prompt: str, age_group: str, voice_name: str, music_filename: str,
    aspect_ratio: str, music_volume: float, transition_style: str
):
    final_video_path = None
    try:
        update_job_status(job_id, "processing", "1/5: Generating story plan...")
        logging.info(f"[{job_id}] Orchestrator: Calling Gemini...")
        story_plan = gemini_service.create_story_plan_with_persona(idea=prompt, age_group=age_group)
        story_script = story_plan.get('story_script')
        image_prompts = story_plan.get('image_prompts')
        if not story_script or not image_prompts: raise Exception("Gemini failed.")
        logging.info(f"[{job_id}] Orchestrator: Story plan generated.")

        update_job_status(job_id, "processing", "2/5: Generating images...")
        logging.info(f"[{job_id}] Orchestrator: Calling Imagen...")
        image_paths = image_generation_service.generate_images_from_prompts(
            prompts=image_prompts, story_id=job_id, aspect_ratio=aspect_ratio
        )
        logging.info(f"[{job_id}] Orchestrator: All images generated.")

        update_job_status(job_id, "processing", "3/5: Compiling video...")
        if DEBUG_BYPASS_VIDEO_CREATION:
            final_video_path_str = bypass_video_creation(output_filename=f"{job_id}.mp4")
            logging.info(f"[{job_id}] Orchestrator: Bypassed video creation.")
        else:
            logging.info(f"[{job_id}] Orchestrator: Calling Video Service...")
            final_video_path_str = video_service.create_video_with_music(
                script=story_script, image_paths=image_paths, voice_name=voice_name,
                music_filename=music_filename, aspect_ratio=aspect_ratio,
                music_volume=music_volume, transition_style=transition_style,
                output_filename=f"{job_id}.mp4"
            )
        
        final_video_path = Path(final_video_path_str) if final_video_path_str else None
        if not final_video_path or not final_video_path.is_file(): raise Exception("Video step failed.")
        logging.info(f"[{job_id}] Orchestrator: Video step complete. Path: {final_video_path}")

        update_job_status(job_id, "processing", "4/5: Uploading to Google Drive...")
        logging.info(f"[{job_id}] Orchestrator: Uploading to Google Drive...")
        GOOGLE_DRIVE_FOLDER_ID = "YOUR_GOOGLE_DRIVE_FOLDER_ID_HERE"
        shareable_link = google_drive_service.upload_video_to_drive(
            local_video_path=str(final_video_path), remote_folder_id=GOOGLE_DRIVE_FOLDER_ID
        )

        story_text_for_display = " ".join([line.get("text", "") for line in story_script])
        update_job_status(job_id, "completed", "5/5: Done!", video_url=shareable_link, story_text=story_text_for_display)
        logging.info(f"[{job_id}] Orchestrator: Workflow completed! Video at {shareable_link}")
        
    except Exception as e:
        logging.exception(f"[{job_id}] Orchestrator: Workflow failed.")
        update_job_status(job_id, "failed", error=str(e))
    finally:
        image_temp_dir = config.UPLOADS_DIR / job_id
        if image_temp_dir.exists(): shutil.rmtree(image_temp_dir)
        logging.info(f"[{job_id}] Orchestrator Cleanup complete.")

# [แก้ไข] ใส่พารามิเตอร์ทั้งหมดกลับเข้ามา
def start_video_creation_job(
    background_tasks: BackgroundTasks, prompt: str, age_group: str, voice_name: str,
    music_filename: str, aspect_ratio: str, music_volume: float, transition_style: str
) -> str:
    job_id = str(uuid.uuid4())
    logging.info(f"Agent Service: Queuing new MAGIC job with ID: {job_id}")
    update_job_status(job_id, "pending", "0/5: Job queued...")
    background_tasks.add_task(
        agent_orchestrator_workflow, job_id=job_id, prompt=prompt, age_group=age_group,
        voice_name=voice_name, music_filename=music_filename, aspect_ratio=aspect_ratio,
        music_volume=music_volume, transition_style=transition_style
    )
    return job_id

# === Workflow และฟังก์ชันสำหรับโหมด Manual Upload ===
def manual_compilation_workflow(
    job_id: str, story_script: list, image_paths: List[str], voice_name: str,
    music_filename: str, aspect_ratio: str, music_volume: float, transition_style: str
):
    final_video_path = None
    image_temp_dir = Path(image_paths[0]).parent if image_paths else None
    try:
        update_job_status(job_id, "processing", "1/2: Compiling video...")
        if DEBUG_BYPASS_VIDEO_CREATION:
            final_video_path_str = bypass_video_creation(output_filename=f"{job_id}.mp4")
            logging.info(f"[{job_id}] Manual: Bypassed video creation.")
        else:
            logging.info(f"[{job_id}] Manual: Calling Video Service...")
            final_video_path_str = video_service.create_video_with_music(
                script=story_script, image_paths=image_paths, voice_name=voice_name,
                music_filename=music_filename, aspect_ratio=aspect_ratio,
                music_volume=music_volume, transition_style=transition_style,
                output_filename=f"{job_id}.mp4"
            )

        final_video_path = Path(final_video_path_str) if final_video_path_str else None
        if not final_video_path or not final_video_path.is_file(): raise Exception("Manual video compilation failed.")
        logging.info(f"[{job_id}] Manual: Video compiled locally at {final_video_path}")
        
        story_text_for_display = " ".join([line.get("text", "") for line in story_script])
        video_url = f"/content/{job_id}.mp4"
        update_job_status(job_id, "completed", "2/2: Done!", video_url=video_url, story_text=story_text_for_display)
        logging.info(f"[{job_id}] Manual: Workflow completed! Video at {video_url}")
        
    except Exception as e:
        logging.exception(f"[{job_id}] Manual: Workflow failed.")
        update_job_status(job_id, "failed", error=f"Manual compilation error: {str(e)}")
    finally:
        if image_temp_dir and image_temp_dir.exists(): shutil.rmtree(image_temp_dir)
        logging.info(f"[{job_id}] Manual: Cleanup complete.")

# [แก้ไข] ใส่พารามิเตอร์ทั้งหมดกลับเข้ามา
def start_manual_compilation_job(
    background_tasks: BackgroundTasks,
    job_id: str,
    story_script_json: str,
    image_paths: List[str],
    voice_name: str,
    music_filename: str,
    aspect_ratio: str,
    music_volume: float,
    transition_style: str
) -> str:
    logging.info(f"Agent Service: Queuing new MANUAL job with ID: {job_id}")
    update_job_status(job_id, "pending", "0/2: Job queued...")
    try:
        story_script = json.loads(story_script_json)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format for story script.")
    background_tasks.add_task(
        manual_compilation_workflow,
        job_id=job_id, story_script=story_script, image_paths=image_paths,
        voice_name=voice_name, music_filename=music_filename,
        aspect_ratio=aspect_ratio, music_volume=music_volume,
        transition_style=transition_style
    )
    return job_id