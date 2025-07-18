# --- START OF FILE: app/services/google_drive_service.py ---
import os
from pathlib import Path
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# ระบุ Path ไปยังไฟล์ credentials ที่รากของโปรเจกต์
# เราจะตั้งค่า Working Directory ให้ถูกต้องเพื่อให้ PyDrive2 หาไฟล์เจอ
SETTINGS_YAML_PATH = Path(__file__).parent.parent.parent / "settings.yaml"

def authenticate_gdrive():
    """จัดการการ Authentication และคืนค่า Drive object"""
    gauth = GoogleAuth(settings_file=str(SETTINGS_YAML_PATH))
    
    # พยายามโหลด credentials ที่เคยบันทึกไว้ ถ้าไม่มีจะเปิดเบราว์เซอร์
    gauth.LocalWebserverAuth()
    
    drive = GoogleDrive(gauth)
    return drive

def upload_video_to_drive(local_video_path: str, remote_folder_id: str) -> str:
    """
    อัปโหลดไฟล์วิดีโอไปยัง Google Drive และคืนค่า Shareable Link
    
    :param local_video_path: Path ของไฟล์วิดีโอในเครื่อง
    :param remote_folder_id: ID ของโฟลเดอร์ใน Google Drive ที่จะอัปโหลดไป
    :return: ลิงก์สำหรับแชร์ไฟล์
    """
    print(f"Google Drive Service: Authenticating...")
    try:
        drive = authenticate_gdrive()
        video_filename = os.path.basename(local_video_path)
        print(f"Google Drive Service: Uploading '{video_filename}' to folder ID '{remote_folder_id}'...")

        file_drive = drive.CreateFile({
            'title': video_filename,
            'parents': [{'id': remote_folder_id}],
            'mimeType': 'video/mp4'
        })
        
        file_drive.SetContentFile(local_video_path)
        file_drive.Upload()
        
        # ทำให้ไฟล์แชร์ได้แบบ "anyone with the link can view"
        file_drive.InsertPermission({'type': 'anyone', 'role': 'reader', 'withLink': True})
        
        shareable_link = file_drive['alternateLink']
        print(f"Google Drive Service: Upload complete! Shareable link: {shareable_link}")
        
        return shareable_link

    except Exception as e:
        print(f"Google Drive Service: An error occurred during upload: {e}")
        # อาจจะคืนค่าเป็น None หรือ re-raise exception ขึ้นไป
        raise e