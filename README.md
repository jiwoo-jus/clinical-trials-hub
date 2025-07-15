# Clinical Trials Hub: A Unified Platform for Clinical Trial Search and Information Extraction

A comprehensive platform that integrates PubMed articles and ClinicalTrials.gov data for unified search and analysis with automatic information extraction capabilities.

## Prerequisites

- **NCBI API Key**: Register at https://www.ncbi.nlm.nih.gov/account/

  - Sign in to your NCBI account or create a new one
  - Once logged in, access your acount settings by clicking on your username in the top-right corner
  - Scroll down to the section titled “API Key Management”
  - Click “Create an API Key.” This will generate a unique alphanumeric key

- **Azure OpenAI**: Get credentials from your Azure portal
- **LiteLLM**: Configure your LiteLLM API credentials for GPT-4o access
- **Firebase(Optional)**: Set up a Firebase project at https://console.firebase.google.com/
- **AACT Database**: Download from https://aact.ctti-clinicaltrials.org/downloads and unzip. To import to PostgreSQL:

  ```bash
  createdb trials

  pg_restore -e -v -O -x -d trials --no-owner path/to/postgres.dmp
  
  psql -d trials  # connects to your local trials database using your PostgreSQL client
  
  SELECT count(*) FROM ctgov.studies; # to verify your database is working
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