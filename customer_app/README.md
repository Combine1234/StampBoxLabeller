# Customer UI

หน้าใช้งานแบบง่ายสำหรับลูกค้า:

- มีแค่อัปโหลด PDF
- Google Sheet mapping ถูกล็อกไว้ในระบบ
- แสดงเปอร์เซ็นต์ระหว่างทำงาน
- เสร็จแล้วกดบันทึก PDF ได้ทันที

รันจากโฟลเดอร์โปรเจกต์:

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\customer_app\app.py --server.port 8502
```

แล้วเปิด:

```text
http://localhost:8502
```
