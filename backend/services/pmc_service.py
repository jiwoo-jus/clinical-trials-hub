import io
from pathlib import Path
from urllib.parse import urlencode

import requests
from pdfminer.high_level import extract_text

from config import NCBI_TOOL_NAME, NCBI_API_EMAIL

OA_BASE = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"

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


def _ftp_to_https(url: str) -> str:
    if url.startswith("ftp://ftp.ncbi.nlm.nih.gov/"):
        return "https://ftp.ncbi.nlm.nih.gov/" + url[len("ftp://ftp.ncbi.nlm.nih.gov/"):]
    return url


def _get_pmc_oa_links(pmcid: str) -> dict:
    pmcid = pmcid if pmcid.startswith("PMC") else f"PMC{pmcid}"
    params = {"id": pmcid, "tool": NCBI_TOOL_NAME, "email": NCBI_API_EMAIL}
    response = requests.get(OA_BASE, params=params, timeout=60, headers={"User-Agent": NCBI_TOOL_NAME})
    response.raise_for_status()

    import xml.etree.ElementTree as ET

    root = ET.fromstring(response.text)
    rec = root.find(".//record")
    if rec is None:
        err = root.find(".//error")
        msg = err.text.strip() if err is not None and err.text else "No <record> found"
        raise RuntimeError(f"OA service returned no record for {pmcid}: {msg}")

    out = {
        "pmcid": pmcid,
        "license": rec.attrib.get("license"),
        "citation": rec.attrib.get("citation"),
        "retracted": rec.attrib.get("retracted"),
        "links": [],
    }

    for link in rec.findall("./link"):
        out["links"].append({
            "format": link.attrib.get("format"),
            "href": link.attrib.get("href"),
            "updated": link.attrib.get("updated"),
        })

    return out


def _get_pdf_url_from_oa(pmcid: str) -> str | None:
    data = _get_pmc_oa_links(pmcid)
    pdf_links = [x for x in data["links"] if x.get("format") == "pdf" and x.get("href")]
    if not pdf_links:
        return None
    pdf_links.sort(key=lambda x: x.get("updated", ""), reverse=True)
    return _ftp_to_https(pdf_links[0]["href"])


def get_pmc_pdf_text(pmcid: str) -> str:
    """Download PMC OA PDF and extract text for LLM input."""
    pmcid = pmcid if pmcid.startswith("PMC") else f"PMC{pmcid}"
    cache_dir = Path(__file__).parent.parent / "cache" / "pdf_text"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{pmcid}.txt"

    if cache_file.exists():
        try:
            return cache_file.read_text(encoding="utf-8")
        except Exception:
            pass

    pdf_url = _get_pdf_url_from_oa(pmcid)
    if not pdf_url:
        raise RuntimeError(f"No PDF link found for {pmcid}")

    response = requests.get(pdf_url, stream=True, timeout=120, headers={"User-Agent": NCBI_TOOL_NAME})
    response.raise_for_status()
    pdf_bytes = response.content

    try:
        text = extract_text(io.BytesIO(pdf_bytes))
    except Exception as e:
        raise RuntimeError(f"PDF text extraction failed for {pmcid}: {e}")

    try:
        cache_file.write_text(text, encoding="utf-8")
    except Exception:
        pass

    return text