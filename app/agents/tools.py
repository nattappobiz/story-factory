# --- START OF FILE: app/agents/tools.py (เวอร์ชัน Google Tools) ---
from langchain.tools import Tool
from app.services import gemini_service, video_service, image_generation_service, tts_service

# --- นิยามเครื่องมือแต่ละชิ้น ---

# Tool ที่ 1: สร้างสคริปต์และ Prompt รูปภาพ
story_creator_tool = Tool(
    name="story_and_image_prompt_creator",
    func=lambda user_prompt: gemini_service.generate_full_script(user_prompt=user_prompt, image_style="Pixar"),
    description="""
    Useful for when you need to write a children's story and generate image prompts based on a user's idea.
    The input should be a single string describing the user's idea for the story.
    Returns a dictionary containing 'story_script' and 'image_prompts'.
    """
)

# Tool ที่ 2 (เตรียมสำหรับอนาคต): สร้างรูปภาพจาก Prompt
# หมายเหตุ: เราต้องปรับ image_generation_service เล็กน้อยให้รับ input เป็น list ได้
# และ video_service ให้รับ image_paths ที่เป็น list ได้
# image_generator_tool = Tool(
#     name="image_generator",
#     func=image_generation_service.generate_images_from_prompts,
#     description="Useful for creating images from a list of text prompts. Input must be a list of strings."
# )

# Tool ที่ 3 (เตรียมสำหรับอนาคต): สร้างวิดีโอ
# video_compiler_tool = Tool(
#     name="video_compiler",
#     func=video_service.create_video_with_music,
#     description="Useful for compiling a video from a script, image paths, and other settings."
# )


# รวบรวมเครื่องมือทั้งหมดที่ Agent สามารถใช้ได้
# ตอนนี้เราจะเปิดใช้งานแค่ story_creator_tool ก่อน
agent_tools = [story_creator_tool]

# --- END OF FILE ---