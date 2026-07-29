# StampBOX Desktop

รุ่น Desktop ใช้ UI และระบบประมวลผลเดียวกับเว็บ StampBOX แต่ทำงานในหน้าต่างแอป
ไฟล์ PDF จะถูกประมวลผลภายในเครื่อง และบันทึกอัตโนมัติที่:

```text
Downloads/StampBOX
```

เว็บเดิมยังอยู่ที่ `customer_web/` และไม่ได้ถูกแทนที่

## ทดลองรันบน Windows

```powershell
.\desktop_app\run_desktop.ps1
```

## สร้าง Windows app และ installer

```powershell
.\desktop_app\build_windows.ps1
```

ผลลัพธ์:

```text
D:\StampBOXDesktopBuild\dist\StampBOX\StampBOX.exe
D:\StampBOXDesktopBuild\dist\installer\StampBOX-Setup-1.0.0.exe
```

สคริปต์เลือกไดรฟ์ `D:` สำหรับไฟล์ build, cache และ temp โดยอัตโนมัติ
ถ้าไม่มีไดรฟ์ `D:` จะใช้ `.desktop-build` ภายในโปรเจกต์แทน
ถ้าเครื่องไม่มี Inno Setup สคริปต์จะสร้าง Portable ZIP ให้แทน

## สร้าง macOS app

ต้องรันบน Mac จริง เพราะ Windows ไม่สามารถสร้าง `.app` ที่มี Python native libraries
ของ macOS ได้

```bash
chmod +x desktop_app/build_macos.sh
./desktop_app/build_macos.sh
```

ผลลัพธ์:

```text
dist/StampBOX.app
dist/StampBOX-macOS-1.0.0.dmg
```

ถ้าไม่มีเครื่อง Mac ให้ push โค้ดขึ้น GitHub แล้วไปที่แท็บ **Actions** เลือก
**Build StampBOX Desktop** > **Run workflow** ระบบจะ build บน macOS และให้ดาวน์โหลด:

- `StampBOX-macOS-arm64` สำหรับ Apple Silicon (M1/M2/M3/M4 และใหม่กว่า)
- `StampBOX-macOS-x64` สำหรับ Intel Mac

กรณียังไม่มี Apple Developer certificate สคริปต์จะเซ็นแบบ ad-hoc ผู้ใช้ปลายทาง
อาจต้องคลิกขวาที่แอปแล้วเลือก Open ในครั้งแรก สำหรับการแจกให้ลูกค้าโดยไม่ขึ้นคำเตือน
ให้ตั้ง `APPLE_SIGNING_IDENTITY` เป็นชื่อ Developer ID Application certificate
ก่อน build แล้วนำ `.dmg` ไป notarize กับ Apple

## ข้อมูลสำคัญ

- Windows 10/11 ควรมี Microsoft Edge WebView2 Runtime ซึ่งปกติติดตั้งมากับระบบ
- แอปต้องใช้อินเทอร์เน็ตเพื่ออ่าน Google Sheet รายการสินค้า
- PDF และ Excel ไม่ถูกส่งไป Render
- ไฟล์ชั่วคราวถูกล้างเมื่อปิดแอป
