# Clinical Trials Hub: A Unified Search and Information Extraction Platform

A comprehensive platform that integrates PubMed articles and ClinicalTrials.gov data for unified search and analysis with automatic information extraction capabilities.

## Prerequisites

- **NCBI API Key**: Register at https://www.ncbi.nlm.nih.gov/account/
- **Azure OpenAI**: Get credentials from your Azure portal
- **Firebase(Optional)**: Set up a Firebase project at https://console.firebase.google.com/
- **AACT Database**: Download from https://aact.ctti-clinicaltrials.org/downloads and import to PostgreSQL:
  ```bash
  createdb trials
  psql trials < clinical_trials_dump.sql
  ```

---

## Quick Start (Docker)

> **Recommended for most users.**
> Run the entire platform with minimal setup using Docker Compose.

### Steps

```bash
# 1. Clone repository
git clone [repository-url]
cd clinical-trials-hub

# 2. Setup environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Configure environment variables in backend/.env and frontend/.env

# 4. Launch with Docker
docker-compose up --build
```

---

## Manual Installation (Without Docker)

> **For development.**
> Set up backend and frontend environments manually.

### Backend Setup

```bash
cd backend
conda install pip # optional, if you prefer conda
pip install -r requirements.txt
cp .env.example .env
# Configure .env with your credentials
python app.py
```

### Frontend Setup

```bash
cd frontend
conda install -c conda-forge nodejs #optional, if you prefer conda
npm install
cp .env.example .env
# Configure .env with your credentials
npm start
```

## Access URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:5050