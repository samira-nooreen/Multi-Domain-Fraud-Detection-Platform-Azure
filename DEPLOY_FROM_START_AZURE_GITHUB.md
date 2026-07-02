# From Scratch Setup: GitHub -> Azure App Service

This guide takes you from local project to a live Azure deployment using GitHub Actions.

## 1) Prerequisites

1. Azure account with an active subscription.
2. GitHub account and a repository for this project.
3. Local git configured (`git --version`, `git config user.name`, `git config user.email`).
4. App Service deployment workflow present at:
   - `.github/workflows/azure-webapp.yml`

## 2) Azure App Service (Create)

1. Open Azure Portal.
2. Create `App Service`.
3. Select:
   - Publish: `Code`
   - Runtime stack: `Python 3.11`
   - Operating System: `Linux`
   - Region: nearest to your users
4. Set Web App name to your chosen value.

## 3) Azure App Service (Runtime Config)

In App Service -> Configuration -> General settings:

1. Startup Command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --worker-class gthread --threads 2 --timeout 120 --keep-alive 5
```

2. Turn `Web Sockets` to `On`.
3. Save and restart when prompted.

## 4) Azure App Service (Environment Variables)

In App Service -> Configuration -> Application settings, add:

1. `SECRET_KEY` = strong random string
2. `EMAIL_SENDER` = your sender email
3. `EMAIL_PASSWORD` = your app password
4. `EMAIL_RECIPIENT` = recipient email
5. `FLASK_DEBUG` = `false`
6. `SOCKETIO_ASYNC_MODE` = `threading`
7. `SCM_DO_BUILD_DURING_DEPLOYMENT` = `true`
8. `DATABASE_PATH` = optional (leave empty to use default writable path)

## 5) Get Publish Profile

1. Go to App Service -> Overview.
2. Click `Get publish profile` and download the `.PublishSettings` file.
3. Copy the full XML content.

## 6) GitHub Repository Secrets

In GitHub -> Repo -> Settings -> Secrets and variables -> Actions:

1. Add `AZURE_WEBAPP_NAME` = your Azure web app name
2. Add `AZURE_WEBAPP_PUBLISH_PROFILE` = full publish profile XML

## 7) Push Project to GitHub

Run from project root:

```bash
git init
git branch -M main
git remote add origin <your-github-repo-url>
git add .
git commit -m "Prepare Azure deployment"
git push -u origin main
```

If repo is already initialized, use:

```bash
git add .
git commit -m "Prepare Azure deployment"
git push origin main
```

## 8) Verify GitHub Actions Deployment

1. Open GitHub -> Actions tab.
2. Open the latest `Deploy Flask app to Azure Web App` run.
3. Confirm all steps pass.

## 9) Verify Live App

1. Open your App Service URL.
2. Test homepage, login, and signup.
3. Confirm the home page shows the heat-map dashboard rather than module cards.
4. Confirm the auth flow still redirects to `/verify_2fa`.
5. If failure occurs, check:
   - App Service -> Log stream
   - GitHub Actions logs

## 10) Security Cleanup

1. Rotate any credentials that were shared in plain text.
2. Update rotated values in Azure Application settings.
3. Never commit `.env` or secrets to git.
