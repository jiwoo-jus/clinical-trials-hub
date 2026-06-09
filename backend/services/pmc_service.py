import io
import shutil
import subprocess
from html import escape
from pathlib import Path
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text

from config import NCBI_TOOL_NAME, NCBI_API_EMAIL

OA_BASE = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
PMC_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)


def _normalize_pmcid(pmcid: str) -> str:
    pmcid = str(pmcid or "").strip()
    return pmcid if pmcid.upper().startswith("PMC") else f"PMC{pmcid}"


def _ncbi_headers() -> dict:
    tool = NCBI_TOOL_NAME or "clinical-trials-hub"
    if NCBI_API_EMAIL:
        user_agent = f"{tool}/1.0 (mailto:{NCBI_API_EMAIL})"
    else:
        user_agent = f"{tool}/1.0"
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def _pmc_html_headers() -> dict:
    return {
        "User-Agent": PMC_BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _fetch_pmc_html_with_curl(url: str) -> str:
    curl_bin = shutil.which("curl")
    if not curl_bin:
        raise RuntimeError("curl is not installed")

    result = subprocess.run(
        [
            curl_bin,
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--max-time",
            "30",
            "-A",
            PMC_BROWSER_USER_AGENT,
            "-H",
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "-H",
            "Accept-Language: en-US,en;q=0.9",
            url,
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"curl failed with code {result.returncode}: {stderr}")

    html = result.stdout.decode("utf-8", errors="replace")
    if not html or "<html" not in html.lower():
        raise RuntimeError("curl returned non-HTML content")
    return html

def get_pmc_full_text_xml(pmcid: str) -> str:
    try:
        pmcid = _normalize_pmcid(pmcid)
        print(f"[get_PMC_xml] Using PMCID: {pmcid}")
        params = {
            "db": "pmc",
            "id": pmcid.replace("PMC", ""),
            "retmode": "xml",
            "tool": NCBI_TOOL_NAME,
            "email": NCBI_API_EMAIL
        }
        efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urlencode(params)
        response = requests.get(efetch_url, headers=_ncbi_headers(), timeout=60)
        response.raise_for_status()
        raw_xml = response.text
        return raw_xml
    except Exception as e:
        print("PMC full text API error:", str(e))
        return "Error retrieving full text."


def _text(tag) -> str:
    if not tag:
        return ""
    return " ".join(tag.get_text(" ", strip=True).split())


def _render_paragraphs(container) -> list[str]:
    if not container:
        return []

    rendered = []
    for child in container.find_all(["p", "list", "table-wrap"], recursive=False):
        if child.name == "p":
            text = _text(child)
            if text:
                rendered.append(f"<p>{escape(text)}</p>")
        elif child.name == "list":
            items = []
            for item in child.find_all("list-item", recursive=False):
                item_text = _text(item)
                if item_text:
                    items.append(f"<li>{escape(item_text)}</li>")
            if items:
                rendered.append("<ul>" + "".join(items) + "</ul>")
        elif child.name == "table-wrap":
            caption = _text(child.find("caption"))
            table_text = _text(child.find("table"))
            parts = []
            if caption:
                parts.append(f"<strong>{escape(caption)}</strong>")
            if table_text:
                parts.append(escape(table_text))
            if parts:
                rendered.append(f"<p>{'<br />'.join(parts)}</p>")
    return rendered


def _render_section(section, level: int = 2) -> str:
    parts = []
    title = section.find("title", recursive=False)
    title_text = _text(title)
    if title_text:
        heading_level = min(max(level, 2), 4)
        parts.append(f"<h{heading_level}>{escape(title_text)}</h{heading_level}>")

    parts.extend(_render_paragraphs(section))

    for child_section in section.find_all("sec", recursive=False):
        parts.append(_render_section(child_section, level + 1))

    return f"<section>{''.join(parts)}</section>" if parts else ""


def _pmc_xml_to_html(xml: str, pmcid: str) -> str:
    soup = BeautifulSoup(xml, "xml")
    article = soup.find("article")
    if article is None:
        raise RuntimeError("No article element found in PMC XML")

    title = _text(article.find("article-title")) or pmcid
    journal = _text(article.find("journal-title"))
    year = _text(article.find("pub-date").find("year")) if article.find("pub-date") else ""

    parts = [
        "<!doctype html><html><head><meta charset=\"utf-8\">",
        "<style>",
        "body{font-family:Arial,sans-serif;line-height:1.55;color:#1f2937;margin:24px;}",
        "article{max-width:920px;margin:0 auto;}",
        "h1{font-size:28px;line-height:1.2;margin:0 0 12px;}",
        "h2{font-size:21px;margin:28px 0 10px;border-bottom:1px solid #e5e7eb;padding-bottom:4px;}",
        "h3{font-size:17px;margin:20px 0 8px;}",
        "p,li{font-size:14px;}",
        ".meta{color:#6b7280;margin-bottom:24px;}",
        "</style></head><body><main id=\"main-content\"><article>",
        f"<h1>{escape(title)}</h1>",
    ]

    meta = " · ".join(x for x in [journal, year, pmcid] if x)
    if meta:
        parts.append(f"<p class=\"meta\">{escape(meta)}</p>")

    abstract = article.find("abstract")
    if abstract:
        abstract_parts = _render_paragraphs(abstract)
        if abstract_parts:
            parts.append("<section><h2>Abstract</h2>")
            parts.extend(abstract_parts)
            parts.append("</section>")

    body = article.find("body")
    if body:
        body_paragraphs = _render_paragraphs(body)
        if body_paragraphs:
            parts.extend(body_paragraphs)
        for section in body.find_all("sec", recursive=False):
            parts.append(_render_section(section))

    back = article.find("back")
    ref_list = back.find("ref-list") if back else None
    if ref_list:
        refs = []
        for ref in ref_list.find_all("ref", recursive=False):
            ref_text = _text(ref)
            if ref_text:
                refs.append(f"<li>{escape(ref_text)}</li>")
        if refs:
            parts.append("<section><h2>References</h2><ol>")
            parts.extend(refs)
            parts.append("</ol></section>")

    parts.append("</article></main></body></html>")
    return "".join(parts)


def get_pmc_full_text_html(pmcid: str):
    pmcid = _normalize_pmcid(pmcid)
    url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
    try:
        print(f"[get_PMC_html] Using PMCID: {pmcid}")
        response = requests.get(url, headers=_pmc_html_headers(), timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        try:
            print(f"[get_PMC_html] Retrying with curl for PMCID: {pmcid}")
            return _fetch_pmc_html_with_curl(url)
        except Exception as curl_err:
            print("curl fallback for PMC HTML failed:", str(curl_err))
        try:
            xml = get_pmc_full_text_xml(pmcid)
            if xml.startswith("Error retrieving"):
                return f"<p>Error retrieving article detail: {escape(str(http_err))}</p>"
            return _pmc_xml_to_html(xml, pmcid)
        except Exception as fallback_err:
            print("Error converting PMC XML fallback to HTML:", str(fallback_err))
            return f"<p>Error retrieving article detail: {escape(str(http_err))}</p>"
    except Exception as e:
        print("Error fetching article HTML from PMC:", str(e))
        try:
            print(f"[get_PMC_html] Retrying with curl for PMCID: {pmcid}")
            return _fetch_pmc_html_with_curl(url)
        except Exception as curl_err:
            print("curl fallback for PMC HTML failed:", str(curl_err))
        try:
            xml = get_pmc_full_text_xml(pmcid)
            if xml.startswith("Error retrieving"):
                return "<p>Error retrieving article detail.</p>"
            return _pmc_xml_to_html(xml, pmcid)
        except Exception as fallback_err:
            print("Error converting PMC XML fallback to HTML:", str(fallback_err))
            return "<p>Error retrieving article detail.</p>"


def _ftp_to_https(url: str) -> str:
    if url.startswith("ftp://ftp.ncbi.nlm.nih.gov/"):
        return "https://ftp.ncbi.nlm.nih.gov/" + url[len("ftp://ftp.ncbi.nlm.nih.gov/"):]
    return url


def _get_pmc_oa_links(pmcid: str) -> dict:
    pmcid = _normalize_pmcid(pmcid)
    params = {"id": pmcid, "tool": NCBI_TOOL_NAME, "email": NCBI_API_EMAIL}
    response = requests.get(OA_BASE, params=params, timeout=60, headers=_ncbi_headers())
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
    pmcid = _normalize_pmcid(pmcid)
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

    response = requests.get(pdf_url, stream=True, timeout=120, headers=_ncbi_headers())
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
