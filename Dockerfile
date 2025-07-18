# 1. ใช้ Base Image ของ Python ที่เป็นทางการ
FROM python:3.10-slim

# 2. ตั้งค่า Working Directory ภายใน Container
WORKDIR /code

# 3. คัดลอกไฟล์ requirements เข้าไปก่อน เพื่อใช้ประโยชน์จาก Docker's layer caching
COPY ./requirements.txt /code/requirements.txt

# 4. ติดตั้ง Dependencies ทั้งหมด
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 5. คัดลอกโค้ดแอปพลิเคชันทั้งหมดเข้าไป
COPY ./app /code/app
COPY ./assets /code/assets

# 6. ตั้งค่า PORT environment variable (สำคัญ!)
ENV PORT=8080

# 7. ตั้งค่า Python environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code

# 8. สร้าง user ที่ไม่ใช่ root เพื่อความปลอดภัย (optional)
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# 9. บอกให้ Container รู้ว่าแอปของเราจะรันบน Port 8080
EXPOSE 8080

# 10. ระบุคำสั่งที่จะรันเมื่อ Container เริ่มต้น
# เลือกใช้อย่างใดอย่างหนึ่งตามที่คุณใช้:

# สำหรับ FastAPI + Uvicorn:
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT"]

# สำหรับ Flask:
# CMD ["sh", "-c", "python -m flask run --host 0.0.0.0 --port $PORT"]

# สำหรับ Django:
# CMD ["sh", "-c", "python manage.py runserver 0.0.0.0:$PORT"]

# สำหรับ Python script ธรรมดา:
# CMD ["python", "app/main.py"]