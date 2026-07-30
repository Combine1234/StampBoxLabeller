# StampBOX Download Portal

Static download page for the StampBOX Windows and macOS installers.

## Local preview

```powershell
python -m http.server 8610 --bind 127.0.0.1 --directory download_portal
```

Open `http://127.0.0.1:8610/`.

## Deployment

The production Vercel project is `stampbox-download`.

```powershell
vercel deploy --prod
```

The Windows installer is hosted on Google Drive. Signed-off macOS builds are
published as GitHub Release assets. Update their URLs in `index.html` when a new
release is uploaded.
