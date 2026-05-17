# Deployment Diagram

The following Mermaid diagram shows the deployment flow for MDFDP (CI/CD → Container Registry → Hosting → App → Model/DB):

```mermaid
flowchart LR
  Dev[Developer]
  GH[GitHub Repo]
  CI[CI/CD (GitHub Actions)]
  Reg[Container Registry\n(ACR / Docker Hub)]
  Deploy[Deployment Trigger]
  LB[Load Balancer]
  Cluster[Hosting (Azure App Service / AKS)]
  Container[Docker Container\n(App + Gunicorn/Uvicorn)]
  App[Application API]
  Model[Model & Artifacts\n(Azure Blob Storage)]
  DB[Database\n(Azure SQL / PostgreSQL)]
  Cache[Redis Cache]
  KV[Azure Key Vault]
  Users[Users / Clients]
  Monitor[Monitoring / Logging\n(Azure Monitor / Log Analytics / Prometheus)]

  Dev --> |push| GH
  GH --> |CI pipeline: build/test| CI
  CI --> |build image| Reg
  CI --> |deploy| Deploy
  Deploy --> Reg
  Reg --> |pull image| Cluster
  LB --> Cluster
  Users --> |HTTPS| LB
  Cluster --> Container
  Container --> App
  App --> Model
  App --> DB
  App --> Cache
  App --> KV
  Cluster --> Monitor
  Cluster --> Monitor -->|alerts/logs| Dev

  subgraph Optional Components
    CDN[CDN / Static Assets]
    EmailSrv[External Email / 3rd-party APIs]
    FeatureFlags[Feature Flag Service]
  end

  App --> CDN
  App --> EmailSrv
  App --> FeatureFlags

  classDef cloud fill:#f3f7ff,stroke:#0366d6;
  class Cluster,Reg,Model,DB,KV cloud;
```

Export tip: open this file in VS Code and use a Mermaid preview extension or paste the block into https://mermaid.live to export PNG/SVG.
