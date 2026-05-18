# MDFDP - Azure Deployment Checklist

## ✅ Configuration Files

- [x] `.python-version` - Python 3.11
- [x] `runtime.txt` - Python 3.11.11
- [x] `.dockerignore` - Exclude unnecessary files
- [x] `requirements.txt` - All dependencies
      (Deployment is via Azure App Service + GitHub Actions)

## ✅ Core Application

- [x] `app.py` - Main Flask application
- [x] `database.py` - Database module
- [x] `currency_config.py` - Currency formatting
- [x] `risk_engine.py` - Risk calculation engine

## ✅ ML Modules (10 Detection Systems)

- [x] `ml_modules/brand_abuse/` - Brand abuse detection
- [x] `ml_modules/click_fraud/` - Click fraud detection
- [x] `ml_modules/credit_card/` - Credit card fraud detection
- [x] `ml_modules/document_forgery/` - Document forgery detection
- [x] `ml_modules/fake_news/` - Fake news detection
- [x] `ml_modules/fake_profile/` - Fake profile detection
- [x] `ml_modules/insurance_fraud/` - Insurance fraud detection
- [x] `ml_modules/loan_default/` - Loan default prediction
- [x] `ml_modules/phishing_url/` - Phishing URL detection
- [x] `ml_modules/spam_email/` - Spam email detection
- [x] `ml_modules/upi_fraud/` - UPI fraud detection
- [x] `ml_modules/chatbot.py` - AI chatbot

## ✅ Frontend

- [x] `templates/` - HTML templates
- [x] `static/css/` - Stylesheets
- [x] `static/js/` - JavaScript files
- [x] `static/images/` - Images
- [x] `static/video/` - Videos

## ✅ Dependencies

- [x] Flask 3.1+
- [x] TensorFlow 2.17+
- [x] PyTorch 2.5+
- [x] scikit-learn 1.5+
- [x] All ML libraries included
- [x] gunicorn (production server)
- [x] python-dotenv

## ⚠️ Environment Variables Needed

Set these in Azure App Service Application settings (or GitHub Actions secrets):

- `EMAIL_SENDER` - Your Gmail address
- `EMAIL_PASSWORD` - Gmail App Password (16 chars)
- `EMAIL_RECIPIENT` - Report recipient email
- `SECRET_KEY` - Change from default in production

## 🚀 Deployment Status

- Python Version: 3.11 ✅
- Build Command: `pip install -r requirements.txt` ✅
- Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120` ✅
  (Use Azure App Service region and plan as required)

## 📝 Post-Deployment Tasks

1. Test all 10 fraud detection modules
2. Configure email settings in Azure App Service Application settings or GitHub Actions secrets
3. Update `app.secret_key` to a secure random value
4. Test database functionality
5. Verify ML models load correctly on-demand
6. Check SocketIO real-time features
7. Test responsive design on mobile

## 🔒 Security Notes

- `.env` file is NOT committed (in .gitignore)
- Database uses SQLite (project.db)
- Consider upgrading to PostgreSQL for production
- Update secret key before going live
- Enable HTTPS (Azure App Service provides this automatically)

## 💡 Performance Tips

- Models load on-demand (lazy loading) ✅
- Single worker to stay within memory limits ✅
- 120s timeout for ML model loading ✅
- First request will be slow (5-15s) - model loading
- Subsequent requests will be faster

## 📊 Monitoring

- Azure App Service provides build and deploy logs ✅
- Azure Application Insights or App Service metrics provide performance data ✅
- Monitor memory usage according to chosen App Service plan
