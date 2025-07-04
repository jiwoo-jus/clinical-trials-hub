# Clinical Trials Hub: A Unified Platform for Clinical Trial Search and Information Extraction

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

## Option 1: Quick Start with Docker

### Steps

```bash
# 1. Clone repository
git clone https://github.com/jiwoo-jus/clinical-trials-hub.git
cd clinical-trials-hub

# 2. Setup environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Configure environment variables in backend/.env and frontend/.env

# 4. Launch with Docker
docker-compose up --build
```

---

## Option 2: Manual Installation Without Docker

### Steps

```bash
# 1. Clone repository
git clone https://github.com/jiwoo-jus/clinical-trials-hub.git
cd clinical-trials-hub

# 2. Setup environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Configure environment variables in backend/.env and frontend/.env
```

### Backend Setup

```bash
cd backend

conda install -c conda-forge pip # optional, if you prefer conda

pip install -r requirements.txt

python app.py
```

### Frontend Setup

```bash
cd frontend

conda install -c conda-forge nodejs # optional, if you prefer conda

npm install

npm start
```

---

## Access URLs

- Frontend: http://localhost:3000
- Backend API Docs: http://localhost:5050/docs