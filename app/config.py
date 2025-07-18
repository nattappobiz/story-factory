# --- START OF FILE: app/config.py ---
from pathlib import Path

# นี่คือ "ศูนย์กลาง" ของเรา
# Path(__file__) คือไฟล์ config.py นี้เอง
# .parent คือโฟลเดอร์ app/
# .parent.parent คือโฟลเดอร์รากของโปรเจกต์ (story_factory/)
PROJECT_ROOT = Path(__file__).parent.parent

# กำหนด Path สำคัญทั้งหมดที่นี่ที่เดียว
CONTENT_DIR = PROJECT_ROOT / "generated_content"
ASSETS_DIR = PROJECT_ROOT / "assets"
MUSIC_DIR = ASSETS_DIR / "music"
UPLOADS_DIR = CONTENT_DIR / "uploads"
VIDEO_FPS = 24

# สร้าง Directory ที่จำเป็นทั้งหมดตอนที่โปรแกรมเริ่มทำงาน
CONTENT_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# --- END OF FILE: app/config.py ---