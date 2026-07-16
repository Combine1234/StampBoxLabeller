# Deploy StampBOX

StampBOX can be hosted on Render or Railway as a normal long-running Python web service.

## Render

1. Push this folder to GitHub.
2. In Render, choose New > Web Service.
3. Select the GitHub repo.
4. Use these settings if Render does not auto-detect `render.yaml`:
   - Name: `stampbox`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python customer_web/server.py`
   - Python version: `3.11.9`
5. Deploy and share the generated Render URL.

## Railway

1. Push this folder to GitHub.
2. In Railway, choose New Project > Deploy from GitHub repo.
3. Select the repo.
4. Railway should use `railway.json` / `Procfile`.
5. Deploy and share the generated Railway URL.

## Notes

- The app uses the hosting provider's `PORT` environment variable automatically.
- Generated PDFs are stored in `output/customer_web`.
- On free hosting, files may disappear after redeploy or restart, so customers should download the PDF after processing.
- The app currently has no login screen. Add access control before sharing widely.

## Vercel

Vercel uses a separate serverless adapter in `api/index.py`.

1. Push this folder to GitHub.
2. In Vercel, create a new project from the GitHub repo.
3. Keep the default install command, or use:

```text
pip install -r requirements.txt
```

4. Vercel will use `vercel.json` and route traffic to `api/index.py`.
5. The Vercel version processes the uploaded PDF in one request and returns the finished PDF directly.

Notes for Vercel:

- Progress is simulated in the browser while the request runs.
- Finished files are not stored permanently on Vercel.
- Customers should download the PDF immediately after processing.
- This is best for small to medium batches that finish within the Vercel function duration.
