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
# (เราจะไม่คัดลอกไฟล์ .env หรือ .json ที่เป็นความลับเข้าไป)

# 6. บอกให้ Container รู้ว่าแอปของเราจะรันบน Port 8080
EXPOSE 8080

# 7. คำสั่งที่จะรันเมื่อ Container เริ่มทำงาน
# ใช้ gunicorn ซึ่งเหมาะสำหรับ Production มากกว่า uvicorn dev server
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8080"]