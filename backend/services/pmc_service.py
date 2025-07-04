import requests
from urllib.parse import urlencode
from config import NCBI_TOOL_NAME, NCBI_API_EMAIL

def get_pmc_full_text_xml(pmcid: str) -> str:
    try:
        print(f"[get_PMC_xml] Using PMCID: {pmcid}")
        params = {
            "db": "pmc",
            "id": pmcid.replace("PMC", ""),
            "retmode": "xml",
            "tool": NCBI_TOOL_NAME,
            "email": NCBI_API_EMAIL
        }
        efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urlencode(params)
        response = requests.get(efetch_url)
        response.raise_for_status()
        raw_xml = response.text
        return raw_xml
    except Exception as e:
        print("PMC full text API error:", str(e))
        return "Error retrieving full text."

def get_pmc_full_text_html(pmcid: str):
    try:
        print(f"[get_PMC_html] Using PMCID: {pmcid}")
        url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return f"Error retrieving article detail: {http_err}"
    except Exception as e:
        print("Error fetching article HTML from PMC:", str(e))
        return "Error retrieving article detail."