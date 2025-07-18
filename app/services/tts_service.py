# --- START OF FILE: app/services/tts_service.py (เวอร์ชัน Dependency Injection) ---
import os
from google.cloud import texttospeech
from pathlib import Path
from typing import Optional, List, Dict
from xml.sax.saxutils import escape

# [แก้ไข] สร้างตัวแปร Global ไว้รอรับ Client แต่ยังไม่สร้างมัน
TTS_CLIENT: Optional[texttospeech.TextToSpeechClient] = None

# [แก้ไข] สร้างฟังก์ชันสำหรับ "รับ" Client จากภายนอก
def set_tts_client(client: texttospeech.TextToSpeechClient):
    """ฟังก์ชันนี้จะถูกเรียกโดย main.py ตอน Startup เพื่อตั้งค่า Client"""
    global TTS_CLIENT
    TTS_CLIENT = client
    print("✅ TTS Service: Google Cloud Client has been successfully injected.")

# (ส่วนของ SSML templates และ script_to_ssml เหมือนเดิมทั้งหมด)
SSML_BREAK = '<break time="700ms"/>'
EMOTION_SSML_TEMPLATES = {
    "whispering": f'<prosody rate="slow" pitch="-2st" volume="soft">%s</prosody>{SSML_BREAK}',
    "excited": f'<emphasis level="strong"><prosody rate="fast" pitch="+2st" volume="loud">%s</prosody></emphasis>{SSML_BREAK}',
    "angry": f'<prosody rate="medium" pitch="-1st" volume="x-loud">%s</prosody>{SSML_BREAK}',
    "sleepy": f'<prosody rate="x-slow" pitch="-2st" volume="soft">%s</prosody><break time="1000ms"/>',
    "happy": f'<prosody rate="medium" pitch="+1st">%s</prosody>{SSML_BREAK}',
    "sad": f'<prosody rate="slow" pitch="-1st">%s</prosody>{SSML_BREAK}',
    "mysterious": f'<prosody rate="slow" volume="medium">%s</prosody>{SSML_BREAK}',
    "default": f'<p>%s</p>{SSML_BREAK}'
}
def script_to_ssml(script: List[Dict[str, str]]) -> str:
    ssml_body = ""
    for line in script:
        text = escape(line.get("text", ""))
        emotion = line.get("emotion", "default").lower()
        template = EMOTION_SSML_TEMPLATES.get(emotion, EMOTION_SSML_TEMPLATES["default"])
        ssml_body += template % text + "\n"
    return f'<speak>{ssml_body}</speak>'


def convert_script_to_speech(script: List[Dict[str, str]], full_output_path: str, voice_name: str = "en-US-Wavenet-C") -> Optional[str]:
    print(f"Google TTS Service: Converting script to speech with voice '{voice_name}'...")
    
    if not TTS_CLIENT:
        print("Google TTS Service Error: Client has not been set. Call set_tts_client() during application startup.")
        return None

    try:
        ssml_text = script_to_ssml(script)
        synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
        language_code = "-".join(voice_name.split("-")[:2])
        voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        
        response = TTS_CLIENT.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        
        output_file = Path(full_output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "wb") as out:
            out.write(response.audio_content)
            print(f"Google TTS Service: Audio content saved to -> {output_file}")
        
        return str(output_file)

    except Exception as e:
        print(f"Google TTS Service Error during synthesis: {e}")
        import traceback
        traceback.print_exc()
        return None