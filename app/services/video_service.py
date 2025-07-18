# --- START OF FILE: app/services/video_service.py (เวอร์ชันแก้ไขสมบูรณ์) ---
import ffmpeg
import os
import shutil
import uuid
import random
from typing import List, Optional, Dict
from pathlib import Path
from app.services import tts_service
from app import config



# (ฟังก์ชัน helper ด้านบนเหมือนเดิมทั้งหมด)
def format_time(seconds: float) -> str:
    millis = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    minutes = seconds // 60
    seconds %= 60
    hours = minutes // 60
    minutes %= 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

def create_srt_file_by_word_groups(script: List[Dict[str, str]], voice_duration: float, output_path: str, words_per_chunk: int = 6):
    if not script: return
    full_text = " ".join([line.get("text", "") for line in script])
    all_words = full_text.split()
    if not all_words: return
    chunks = [" ".join(all_words[i:i + words_per_chunk]) for i in range(0, len(all_words), words_per_chunk)]
    duration_per_chunk = voice_duration / len(chunks) if chunks else 0
    with open(output_path, "w", encoding="utf-8") as f:
        for i, chunk_text in enumerate(chunks):
            start_time = i * duration_per_chunk
            end_time = start_time + duration_per_chunk
            if i < len(chunks) - 1: end_time -= 0.1
            if end_time <= start_time: end_time = start_time + 0.1
            f.write(f"{i + 1}\n")
            f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
            f.write(f"{chunk_text}\n\n")
    print(f"  - Subtitle file created with {len(chunks)} word chunks.")

def get_audio_duration(file_path: str) -> float:
    try:
        probe = ffmpeg.probe(file_path)
        return float(probe['format']['duration'])
    except ffmpeg.Error as e:
        print(f"Error probing audio duration for {file_path}: {e.stderr.decode()}")
        return 0

# --- [การแก้ไขจุดที่ 1: เปลี่ยนพารามิเตอร์] ---
def create_video_with_music(
    script: List[Dict[str, str]],
    image_paths: List[str],
    voice_name: str,
    music_filename: str, # <--- เปลี่ยนจาก music_style
    aspect_ratio: str,
    music_volume: float,
    transition_style: str,
    output_filename: str
) -> Optional[str]:
# -----------------------------------------------
    print("Video Service: Creating final video...")
    if not image_paths or not script: return None

    temp_dir = config.CONTENT_DIR / f"temp_{os.path.splitext(output_filename)[0]}"
    temp_dir.mkdir(exist_ok=True, parents=True)

    try:
        print("  - Step 1: Synthesizing voice track...")
        voice_audio_path = tts_service.convert_script_to_speech(script, str(temp_dir / "voice.mp3"), voice_name)
        if not voice_audio_path: raise Exception("Failed to create voice audio file.")
        voice_duration = get_audio_duration(voice_audio_path)
        if voice_duration <= 0: raise ValueError("Invalid voice audio duration.")

        print(f"  - Step 2: Preparing silent video with Ken Burns & Transitions...")
        if aspect_ratio == "9:16": VIDEO_WIDTH, VIDEO_HEIGHT = 720, 1280
        elif aspect_ratio == "1:1": VIDEO_WIDTH, VIDEO_HEIGHT = 1080, 1080
        else: VIDEO_WIDTH, VIDEO_HEIGHT = 1280, 720
        duration_per_image = voice_duration / len(image_paths) if len(image_paths) > 0 else 0
        transition_duration = 1.0

        zoom_pan_effects = [
            {'z': 'min(zoom+0.0015,1.2)', 'x': 'iw/2-(iw/zoom/2)', 'y': 'ih/2-(ih/zoom/2)'},
            {'z': '1.2-0.0015*on', 'x': 'iw/2-(iw/zoom/2)', 'y': 'ih/2-(ih/zoom/2)'},
            {'z': '1.2', 'x': '0', 'y': '0'},
            {'z': '1.2', 'x': 'iw-iw/zoom', 'y': 'ih-ih/zoom'},
        ]
        
        animated_clips = []
        for i, image_path in enumerate(image_paths):
            clip = ffmpeg.input(image_path, loop=1, t=duration_per_image, framerate=config.VIDEO_FPS)
            
            initial_scale = 1.2
            target_w, target_h = int(VIDEO_WIDTH * initial_scale), int(VIDEO_HEIGHT * initial_scale)

            scaled_clip = clip.filter(
                'scale', 
                w=f"if(gte(iw/ih,{target_w}/{target_h}),-1,{target_w})", 
                h=f"if(gte(iw/ih,{target_w}/{target_h}),{target_h},-1)"
            ).filter(
                'crop', w=target_w, h=target_h
            )
            
            selected_effect = random.choice(zoom_pan_effects)
            zoomed_clip = scaled_clip.filter(
                'zoompan', z=selected_effect['z'], x=selected_effect['x'], y=selected_effect['y'],
                d=int(duration_per_image * config.VIDEO_FPS), s=f'{VIDEO_WIDTH}x{VIDEO_HEIGHT}', fps=config.VIDEO_FPS
            )
            animated_clips.append(zoomed_clip)

        if not animated_clips: raise ValueError("No animated clips to process.")

        video_stream = animated_clips[0]
        if len(animated_clips) > 1:
            for i in range(1, len(animated_clips)):
                offset = (duration_per_image - transition_duration) * i
                video_stream = ffmpeg.filter([video_stream, animated_clips[i]], 'xfade', transition=transition_style, duration=transition_duration, offset=offset)
        
        srt_path = temp_dir / "subtitles.srt"
        create_srt_file_by_word_groups(script, voice_duration, str(srt_path))
        if srt_path.is_file():
             video_stream = video_stream.filter('subtitles', filename=str(srt_path).replace('\\', '/'), force_style='FontName=Arial,FontSize=24,PrimaryColour=&HFFFFFF,BorderStyle=1,OutlineColour=&H000000,Outline=1,Shadow=0.5,Alignment=2')

        silent_video_path = str(temp_dir / "silent_video.mp4")
        ffmpeg.output(video_stream, silent_video_path, vcodec='libx264', pix_fmt='yuv420p', preset='ultrafast', crf=23).overwrite_output().run(capture_stdout=True, capture_stderr=True)
        print(f"  - Silent video with visuals created at '{silent_video_path}'")

        print("  - Step 3: Preparing final audio track...")
        voice_stream = ffmpeg.input(voice_audio_path)
        final_audio_stream = voice_stream
        
        # --- [การแก้ไขจุดที่ 2: เปลี่ยน Logic การหาไฟล์เพลง] ---
        # ตอนนี้เราใช้ music_filename โดยตรง ไม่ต้องเติม .mp3 แล้ว
        music_path = config.MUSIC_DIR / music_filename 
        if music_filename != "none" and music_path.is_file():
            print(f"  - Music file found: {music_filename}. Mixing with controlled weights...")
            music_stream = ffmpeg.input(str(music_path)).filter('atrim', duration=voice_duration).filter('asetpts', 'PTS-STARTPTS')
            final_audio_stream = ffmpeg.filter([voice_stream, music_stream], 'amix', duration='first', weights=f"1 {music_volume}")
        # ----------------------------------------------------
        
        final_audio_path = str(temp_dir / "final_audio.aac")
        ffmpeg.output(final_audio_stream, final_audio_path, acodec='aac').overwrite_output().run(capture_stdout=True, capture_stderr=True)
        print(f"  - Final audio track created at '{final_audio_path}'")

        print("  - Step 4: Combining video and audio...")
        final_video_input = ffmpeg.input(silent_video_path)
        final_audio_input = ffmpeg.input(final_audio_path)
        output_path = config.CONTENT_DIR / output_filename
        (
            ffmpeg.output(
                final_video_input.video, final_audio_input.audio, str(output_path),
                vcodec='copy', acodec='copy', shortest=None
            ).overwrite_output().run(capture_stdout=True, capture_stderr=True)
        )
        
        print(f"Video Service: Video created successfully at -> {output_path}")
        return str(output_path)

    except ffmpeg.Error as e:
        stderr = e.stderr.decode('utf-8') if e.stderr else "No stderr output."
        print(f"--- FFmpeg Error ---\n{stderr}")
        raise e
    except Exception as e:
        print(f"An unexpected error occurred in video service: {e}")
        raise e
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"  - Cleaned up temporary directory.")
# --- END OF FILE ---