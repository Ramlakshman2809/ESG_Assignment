# ESG Data Ingestion & Review Dashboard

A Django REST + React application for ingesting emissions data from multiple sources (SAP, Utility, Travel), normalizing it, and providing an analyst review workflow before audit approval.

## Features

- **Multi-tenant architecture** - Support for multiple client companies
- **Three data sources**:
  - SAP (fuel & procurement data)
  - Utility portals (electricity consumption)
  - Corporate travel platforms (flights, hotels, ground transport)
- **Emission categorization** - Scope 1/2/3 classifications
- **Unit normalization** - Convert various units to base units
- **Review workflow** - Analysts can approve, reject, or flag suspicious records
- **Audit trail** - Full history of all changes for compliance

## Tech Stack

- **Backend**: Django 5.x, Django REST Framework, SQLite/PostgreSQL
- **Frontend**: React 18, Vite, Axios
- **Deployment**: Docker-ready, Render-compatible

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed initial data
python manage.py seed_data

# Start server
python manage.py runserver
```

### Frontend Setup

```bash
cd esg-frontend
npm install
npm run dev
```

### Default Credentials

- Username: `admin`
- Password: `admin123`

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/login/` | Login and get token |
| `GET /api/tenants/` | List tenants |
| `GET /api/emission-records/` | List emission records |
| `POST /api/emission-records/{id}/update_status/` | Update record status |
| `POST /api/emission-records/bulk_approve/` | Bulk approve records |
| `POST /api/ingestion/ingest_sap/` | Import SAP data |
| `POST /api/ingestion/ingest_utility/` | Import utility data |
| `POST /api/ingestion/ingest_travel/` | Import travel data |

## Data Model

See [MODEL.md](MODEL.md) for detailed data model documentation.

## Deployment

The project includes configuration for Render deployment:

```yaml
# render.yaml
services:
  - type: web
    name: esg-backend
    buildCommand: pip install -r requirements.txt && python manage.py migrate
    startCommand: gunicorn esg_backend.wsgi:application --bind 0.0.0.0:$PORT
```

## Documentation

- [MODEL.md](MODEL.md) - Data model and justifications
- [DECISIONS.md](DECISIONS.md) - Design decisions and trade-offs
- [TRADEOFFS.md](TRADEOFFS.md) - Things deliberately not built
- [SOURCES.md](SOURCES.md) - Research on real-world data formats

## License

MIT