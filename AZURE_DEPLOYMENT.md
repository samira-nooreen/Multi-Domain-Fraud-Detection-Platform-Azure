# Azure Deployment Guide

This repository is ready for two Azure paths:

1. Azure App Service on Linux using the existing Gunicorn startup command.
2. Azure Container Apps or App Service for Containers using the included Dockerfile.

The current homepage is trimmed down to the heat-map and incident dashboard, so the deployment package no longer needs the old module-card shortcuts on the landing page.

For GitHub-based deployments, the repository now includes a GitHub Actions workflow that deploys to Azure Web App on every push to `main`.

## Direct Deploy From VS Code

Use this path if you do not want GitHub involved.

1. Open the Azure panel in VS Code.
2. Sign in to Azure.
3. Under App Service, create a new Web App.
4. Choose:
   - Name: any unique name
   - Runtime: Python 3.10 or 3.11
   - Region: closest to you
5. Right-click the new Web App and choose Deploy to Web App.
6. Select this project folder when prompted.
7. Confirm the overwrite prompt.
8. Open the app in the Azure portal.
9. Set the startup command in Configuration > General Settings:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --worker-class gthread --threads 2 --timeout 120 --keep-alive 5
```

10. Turn Web Sockets ON in Configuration > General Settings.
11. Add these Application Settings:

- `SECRET_KEY`
- `EMAIL_SENDER`
- `EMAIL_PASSWORD`
- `EMAIL_RECIPIENT`
- `FLASK_DEBUG=false`
- `SOCKETIO_ASYNC_MODE=threading`
- `DATABASE_PATH` (optional; defaults to a writable home-directory location)

12. Save, restart the app, then use Browse Website from VS Code.
13. If it fails, open Start Streaming Logs from the Azure explorer.

### Website checks after deployment

1. Confirm the homepage hero shows the Azure deployment badge.
2. Confirm the heat-map dashboard loads and the removed module buttons are not shown.
3. Confirm `/login` and `/signup` still render and redirect through the 2FA flow.

## Option 1: Azure App Service

Use this if you want the simplest deployment from source code.

1. Create a new App Service.
2. Choose:
   - Publish: Code
   - Runtime stack: Python 3.11
   - Operating system: Linux
3. Set the startup command to:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --worker-class gthread --threads 2 --timeout 120 --keep-alive 5
```

4. Add these Application Settings in Azure:
   - `SECRET_KEY`
   - `EMAIL_SENDER`
   - `EMAIL_PASSWORD`
   - `EMAIL_RECIPIENT`
   - `FLASK_DEBUG=false`
   - `SOCKETIO_ASYNC_MODE=threading`
   - `SCM_DO_BUILD_DURING_DEPLOYMENT=true`
   - `DATABASE_PATH` (optional; defaults to a writable home-directory location)

5. Enable WebSockets in the App Service configuration.
6. Deploy from VS Code, ZIP deploy, or GitHub Actions.

## Option 1b: GitHub Actions to Azure Web App

Use this if you want GitHub to deploy automatically after each push.

1. Create an Azure App Service web app on Linux with Python 3.11.
2. Set the startup command to:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --worker-class gthread --threads 2 --timeout 120 --keep-alive 5
```

3. Enable WebSockets in the App Service configuration.
4. Add these Azure Application Settings:
   - `SECRET_KEY`
   - `EMAIL_SENDER`
   - `EMAIL_PASSWORD`
   - `EMAIL_RECIPIENT`
   - `FLASK_DEBUG=false`
   - `SOCKETIO_ASYNC_MODE=threading`
   - `SCM_DO_BUILD_DURING_DEPLOYMENT=true`
   - `DATABASE_PATH` (optional; defaults to a writable home-directory location)
5. In GitHub, add these repository secrets:
   - `AZURE_WEBAPP_NAME`
   - `AZURE_WEBAPP_PUBLISH_PROFILE`
6. Push to `main` and the workflow in `.github/workflows/azure-webapp.yml` will deploy the app.

## Option 2: Azure Container Apps

Use this if you want a fully containerized deployment.

1. Build the image from the included Dockerfile.
2. Push it to Azure Container Registry.
3. Create a Container App from that image.
4. Set these environment variables in the container app:
   - `PORT=8000`
   - `SECRET_KEY`
   - `EMAIL_SENDER`
   - `EMAIL_PASSWORD`
   - `EMAIL_RECIPIENT`
   - `FLASK_DEBUG=false`
   - `SOCKETIO_ASYNC_MODE=threading`
   - `WEBSITES_PORT=8000` if you use Azure App Service for Containers

5. Expose port `8000`.

## Notes

- The app now reads `SECRET_KEY` from the environment and falls back to a safer placeholder only for local development.
- The local `python app.py` path now listens on `0.0.0.0` and respects `PORT`, so it works in containers too.
- SQLite now defaults to a writable home-directory path, and you can override it with `DATABASE_PATH` in Azure if needed.
- The repository already includes `gunicorn` in `requirements.txt`.
- `simple-websocket` is recommended for SocketIO/WebSocket support under threaded workers.
