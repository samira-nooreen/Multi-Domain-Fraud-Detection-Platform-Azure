# Multi-Domain Fraud Detection Platform (MDFDP)

Multi-Domain Fraud Detection Platform is a Flask-based security demo that detects fraud across multiple domains, including UPI, credit card, spam email, phishing URLs, bot profiles, and related risk signals. It includes a public landing page, protected dashboards, and Azure-ready deployment settings.

## Live Website

- Azure website: https://multi-domain-fraud-detection-platform-e2f0e9g2hha4axcm.southeastasia-01.azurewebsites.net/

## Demo Login

Use the demo account to explore the full website:

- Email: demo@mdfdp.com
- Password: MDFDP@2026

## Key Features

- Multi-domain fraud detection modules
- Public homepage with login and signup entry points
- Suspicious login and 2FA flow for authenticated access
- Fraud heatmap, analytics, and security dashboards
- Azure App Service and GitHub Actions deployment support

## Local Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python app.py
```

The app listens on `0.0.0.0` and respects `PORT` when running in Azure or containers.

## Configuration

Set these environment variables as needed:

- `SECRET_KEY`
- `EMAIL_SENDER`
- `EMAIL_PASSWORD`
- `EMAIL_RECIPIENT`
- `FLASK_DEBUG=false`
- `SOCKETIO_ASYNC_MODE=threading`
- `DATABASE_PATH` (optional)
- `DEMO_EMAIL` (optional)
- `DEMO_PASSWORD` (optional)
- `DEMO_NAME` (optional)

## Azure Deployment

This repository supports Azure App Service deployment using Gunicorn:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --worker-class gthread --threads 2 --timeout 120 --keep-alive 5
```

If you deploy from GitHub, the workflow in `.github/workflows/azure-webapp.yml` builds and deploys on every push to `main`.

## Project Notes

- SQLite defaults to a writable local path, with Azure override support through `DATABASE_PATH`.
- The homepage is public so visitors can view the platform before logging in.
- Demo login bypasses the 2FA step so new visitors can explore the project quickly.

## Repository Structure

- `app.py` - Flask application and routes
- `database.py` - SQLite helpers and auth utilities
- `templates/` - HTML templates
- `static/` - CSS, JS, images, and video assets
- `.github/workflows/azure-webapp.yml` - GitHub Actions deployment workflow

## License

See `LICENSE` for details.
