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

Installer files are hosted on Google Drive. Update their direct-download URLs in
`index.html` when a new release is uploaded.
