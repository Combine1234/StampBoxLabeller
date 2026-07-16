# Shopee Label Overlay MVP

เครื่องมือนี้อ่านไฟล์ใบปะ Shopee PDF แบบ 3x3 ต่อหน้า แล้วเขียนโค้ด/คำย่อสินค้าแบบตัวใหญ่ลงในพื้นที่ว่างของตารางสินค้าโดยไม่แก้ไขไฟล์ต้นฉบับ

## ติดตั้ง

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## ใช้งานผ่าน Streamlit

```powershell
.\.venv\Scripts\streamlit run app.py
```

จากนั้นอัปโหลด PDF ได้ทันที:

- PDF ใบปะ Shopee

Excel เป็น optional ใช้เมื่ออยาก override โค้ดสินค้าเอง คอลัมน์หลักคือ `order_no`, `product_code`, `variant`, `quantity`

## รูปแบบ Excel

หนึ่งแถวคือหนึ่งรายการสินค้าที่จะเขียนลงใบปะ โดยข้อความที่เขียนจริงคือ `product_code xquantity` ถ้าไม่มี `product_code` จะ fallback เป็น `variant xquantity`

| order_no | tracking_no | product_code | short_product_name | variant | quantity | box_no | total_boxes | note |
|---|---|---|---|---|---:|---:|---:|---|
| 2607060SXN316F | 5910552865138006 | TB-7575-MP | โต๊ะญี่ปุ่น 75x75 | เมเปิ้ล | 1 | 1 | 2 | ระวังกระแทก |

ระบบจะจับคู่ด้วย `tracking_no` ก่อน แล้วจึงใช้ `order_no` เป็นตัวสำรอง ถ้า Excel มีหลายแถวในออเดอร์เดียวกัน ระบบจะรวมเป็นหลายบรรทัดในใบเดียว เช่น `TABLE-MAPLE x1`

## โค้ดสินค้าอัตโนมัติจาก PDF

ถ้าไม่ได้อัปโหลด Excel ระบบจะอ่านตารางสินค้าใน PDF แล้วสร้าง `product_code` จากไฟล์:

```text
config/product_code_rules.json
```

แก้ไฟล์นี้เพื่อเพิ่มคำย่อของร้านได้ เช่น keyword `เก้าอี้` ให้เป็น `CHAIR` หรือ keyword `น้ำเงิน` ให้เติม token `NAVY`

## ฟอนต์ภาษาไทย

ระบบจะค้นหาฟอนต์ตามลำดับนี้:

1. ค่าที่ระบุในช่อง `Font path`
2. ตัวแปรแวดล้อม `SHOPEE_LABEL_FONT`
3. `assets/fonts/NotoSansThai-Regular.ttf` หรือ `assets/fonts/Sarabun-Regular.ttf`
4. ฟอนต์ Windows เช่น Leelawadee UI หรือ Tahoma

## โครงสร้าง

```text
app.py
config/layout_config.json
src/
  excel_reader.py
  pdf_reader.py
  matcher.py
  layout_detector.py
  overlay_writer.py
  preview.py
  validator.py
  report.py
tests/
```

## ทดสอบ

```powershell
.\.venv\Scripts\pytest
```
