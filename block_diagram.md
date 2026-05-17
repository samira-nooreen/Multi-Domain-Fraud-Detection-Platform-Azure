# Block Diagram

High-level block diagram of MDFDP components and their interactions.

```mermaid
flowchart TB
  subgraph Clients
    Browser[Web Client (Browser)]
    Mobile[Mobile Client]
  end

  LB[Load Balancer / API Gateway]
  API[Flask API (Gunicorn / Uvicorn)]
  Auth[Auth & Sessions]

  subgraph "ML & Models"
    MLModules[ML Modules\n(Detectors)]
    ModelStore[Model Artifacts\n(Azure Blob Storage / ./models)]
  end

  DB[Database\n(SQLite / Azure SQL)]
  Cache[Redis Cache]
  Queue[Message Queue\n(RabbitMQ / Redis)]
  Workers[Background Workers\n(Celery / RQ)]
  Admin[Admin Dashboard]
  External[External Services\n(Email, 3rd-party APIs)]
  Monitor[Monitoring / Logging\n(Azure Monitor / Prometheus / ELK)]

  Clients --> LB
  LB --> API
  API --> Auth
  API --> MLModules
  MLModules --> ModelStore
  API --> DB
  API --> Cache
  API --> Queue
  Queue --> Workers
  Workers --> MLModules
  API --> Admin
  API --> External
  API --> Monitor

  classDef infra fill:#f7fff4,stroke:#0b6623;
  class ModelStore,DB,Cache,Queue,Monitor infra;
```

Open this file in VS Code and use a Mermaid preview extension or https://mermaid.live to render/export the diagram.
