# Clinical Trials Hub: A Unified Platform for Clinical Trial Search and Information Extraction

A comprehensive platform that integrates PubMed articles and ClinicalTrials.gov data for unified search and analysis with automatic information extraction capabilities.

> **Note:** Code for PMC–CTG sample collection and evaluation pipelines is maintained separately at  
> https://github.com/jiwoo-jus/clinical-trials-hub-evaluation

## Prerequisites

- **NCBI API Key**: Register at https://www.ncbi.nlm.nih.gov/account/

  - Sign in to your NCBI account or create a new one
  - Once logged in, access your acount settings by clicking on your username in the top-right corner
  - Scroll down to the section titled “API Key Management”
  - Click “Create an API Key.” This will generate a unique alphanumeric key

- **Azure OpenAI**: Get credentials from your Azure portal
- **LiteLLM**: Configure your LiteLLM API credentials to route requests to supported LLM providers
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

---

## Citation

If you use this pipeline in your research, please cite:

```bibtex
@inproceedings{park-etal-2026-clinicaltrialshub,
    title = "{C}linical{T}rials{H}ub: Bridging Registries and Literature for Comprehensive Clinical Trial Access",
    author = "Park, Jiwoo  and
      Liu, Ruoqi  and
      Jagdale, Avani  and
      Srisuwananukorn, Andrew  and
      Zhao, Jing  and
      Li, Lang  and
      Zhang, Ping  and
      Kumar, Sachin",
    editor = "Croce, Danilo  and
      Leidner, Jochen  and
      Moosavi, Nafise Sadat",
    booktitle = "Proceedings of the 19th Conference of the {E}uropean Chapter of the {A}ssociation for {C}omputational {L}inguistics (Volume 3: System Demonstrations)",
    month = mar,
    year = "2026",
    address = "Rabat, Marocco",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2026.eacl-demo.26/",
    doi = "10.18653/v1/2026.eacl-demo.26",
    pages = "359--396",
    ISBN = "979-8-89176-382-1",
    abstract = "We present ClinicalTrialsHub, an interactive search-focused platform that consolidates all data from ClinicalTrials.gov and augments it by automatically extracting and structuring trial-relevant information from PubMed research articles. Our system effectively increases access to structured clinical trial data by 83.8{\%} compared to relying on ClinicalTrials.gov alone, with potential to make access easier for patients, clinicians, researchers, and policymakers, advancing evidence-based medicine. ClinicalTrialsHub uses large language models such as GPT-5.1 and Gemini-3-Pro to enhance accessibility. The platform automatically parses full-text research articles to extract structured trial information, translates user queries into structured database searches, and provides an attributed question-answering system that generates evidence-grounded answers linked to specific source sentences. We demonstrate its utility through a user study involving clinicians, clinical researchers, and PhD students of pharmaceutical sciences and nursing, and a systematic automatic evaluation of its information extraction and question answering capabilities."
}
```

## Contact

For questions or issues, please contact park.3620@osu.edu.
