# StampBOX

เว็บสำหรับอัปโหลดใบปะหน้า Shopee PDF แล้วเขียนโค้ดสินค้า + จำนวนลงไฟล์ให้อัตโนมัติ

## Run locally

```powershell
.\.venv\Scripts\python.exe .\customer_web\server.py
```

เปิด:

```text
http://127.0.0.1:8600
```

## Deploy on Render

1. Push repo นี้ขึ้น GitHub
2. เข้า Render แล้วเลือก New > Web Service
3. เลือก repo นี้
4. Render จะอ่าน `render.yaml` ได้เอง หรือใส่เอง:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python customer_web/server.py`
5. Deploy แล้วใช้ URL ที่ Render ให้

## Deploy on Railway

1. Push repo นี้ขึ้น GitHub
2. เข้า Railway แล้วเลือก New Project > Deploy from GitHub repo
3. เลือก repo นี้
4. Railway จะใช้ `railway.json` / `Procfile` เพื่อ start:

```text
python customer_web/server.py
```

## Output files

ไฟล์ PDF และ report ที่ทำเสร็จจะถูกเก็บชั่วคราวใน:

```text
output/customer_web
```

บน Render/Railway filesystem อาจถูกล้างเมื่อ redeploy/restart ดังนั้นลูกค้าควรกดดาวน์โหลดทันทีหลังประมวลผลเสร็จ
