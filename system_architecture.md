# Chapter 4: System Architecture & Design

## 4.2.2 Component Architecture

The system is composed of the following main components:

1. **Web Interface**: Frontend application built with HTML, CSS, and JavaScript
   - Provides user-friendly dashboards for fraud detection results
   - Real-time visualization of risk levels and fraud alerts
   - Interactive forms for module-specific inputs

2. **API Layer**: Flask-based RESTful API for backend services
   - Handles HTTP requests and routes to appropriate fraud detection modules
   - Manages session handling and request authentication
   - Returns standardized JSON responses with risk scores, actions, and metadata

3. **ML Modules**: 10 specialized fraud detection modules
   - UPI Fraud Detection
   - Credit Card Fraud Detection
   - Loan Default Risk Prediction
   - Insurance Fraud Detection
   - Click Fraud Detection
   - Fake News Detection
   - Spam Email Detection
   - Phishing URL Detection
   - Fake Profile / Bot Detection
   - Document Forgery Detection

4. **Database Layer**: SQLite for data persistence
   - Stores user accounts, device fingerprints, and trusted locations
   - Maintains fraud analysis logs and decision audit trails
   - Enables historical query and trend analysis

5. **Analytics Engine**: Real-time visualization and monitoring
   - Processes and aggregates fraud detection results
   - Generates performance metrics and risk distribution charts
   - Provides live dashboard updates via WebSocket (Flask-SocketIO)

6. **Authentication System**: User management and security
   - Implements user registration and login workflows
   - Supports multi-factor authentication (TOTP/2FA)
   - Manages role-based access control (admin, analyst, viewer)

7. **Logging System**: Comprehensive audit trail
   - Records all fraud detection activities with timestamps
   - Maintains decision reasoning and feature importance for each analysis
   - Supports compliance and forensic investigation needs

## 4.2.3 Technology Stack

### Backend

- **Language**: Python 3.9
- **Web Framework**: Flask with Flask-SocketIO and Flask-CORS
- **WSGI Server**: Gunicorn (production), Flask dev server (local)

### ML Libraries

- **Scikit-learn**: Classification, ensemble methods (RandomForest, IsolationForest)
- **XGBoost**: Gradient boosting for transaction fraud and anomaly detection
- **PyTorch**: Deep learning models (LSTM for sequences, CNN for images, GNN for graphs)
- **TensorFlow**: Alternative deep learning support (optional)
- **LightGBM**: Fast gradient boosting for loan default prediction
- **Pandas & NumPy**: Data manipulation and numerical computing

### Database

- **SQLite**: Local, file-based database for development and deployment
- **Optional**: Azure SQL or PostgreSQL for cloud-scale deployments

### Frontend

- **HTML5**: Semantic markup for accessibility and structure
- **CSS3**: Responsive design with Bootstrap framework
- **JavaScript**: Client-side interactivity, form validation, and real-time updates
- **Chart.js**: Data visualization for fraud trends and distributions
- **Leaflet**: Geographic mapping for location-based fraud indicators

### Deployment & Infrastructure

- **Local Server**: Python-based Flask development or Gunicorn production server
- **Cloud Deployment**: Azure App Service with GitHub Actions CI/CD
- **Containerization**: Docker (optional, for consistency across environments)
- **Version Control**: Git and GitHub

### Supporting Libraries

- **Joblib**: Model serialization and caching
- **TF-IDF & NLP**: Text vectorization for email and news classification
- **Jinja2**: Server-side templating for dynamic HTML rendering

### Key Architectural Decisions

- **Modular Design**: Each detector is independent, allowing parallel development and easy testing.
- **Lazy Loading**: Models are loaded on-demand via a caching layer to reduce memory footprint.
- **Standardized Output**: All modules return consistent risk levels (LOW, MEDIUM, HIGH, CRITICAL) and recommended actions.
- **Hybrid Approach**: Combines ensemble ML models with rule-based logic for explainability and control.
- **Real-Time Capable**: Sub-100ms latency across most modules for interactive use.
