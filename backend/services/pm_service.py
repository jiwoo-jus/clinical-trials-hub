from typing import Dict, List, Optional, Set, Any
import requests
import os
import re
import time
import asyncio
import aiohttp
import json
from urllib.parse import urlencode
from config import NCBI_TOOL_NAME, NCBI_API_EMAIL, MAX_FETCH_SIZE, NCBI_API_KEY
from bs4 import BeautifulSoup
from rank_bm25 import BM25Okapi
from .pm_data_parser import parse_pubmed_xml
from .pm_metadata_extractor import extract_all_metadata_from_pm

print(f"[PM Service] NCBI API Key: {'***' if NCBI_API_KEY else 'Not set'}")
print(f"[PM Service] NCBI Tool Name: {NCBI_TOOL_NAME}")
print(f"[PM Service] NCBI API Email: {NCBI_API_EMAIL}")
print(f"[PM Service] Max Fetch Size: {MAX_FETCH_SIZE}")
print(f"[PM Service] PMC Fallback: Enabled (will try PMC if PubMed fails)")

# Rate limiting configuration
MAX_REQUESTS_PER_SECOND = 10 if NCBI_API_KEY else 3
REQUEST_DELAY = 1.0 / MAX_REQUESTS_PER_SECOND  # 0.1s with key, 0.33s without

NCBI_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Maximum number of PMIDs per request
ESEARCH_MAX_IDS = 1000  # E-Search can fetch up to 10,000 but we use 1000 for safety
EFETCH_MAX_IDS = 300   # E-Fetch should be limited to 300 for performance
MAX_PMIDS_LIMIT = MAX_FETCH_SIZE  # Use centralized configuration for maximum total PMIDs to fetch

# Global rate limiter
class RateLimiter:
    def __init__(self, max_requests_per_second: int):
        self.max_requests_per_second = max_requests_per_second
        self.requests = []
        self.lock = asyncio.Lock()
        
    async def acquire(self):
        async with self.lock:
            now = time.time()
            # Remove requests older than 1 second
            self.requests = [req_time for req_time in self.requests if now - req_time < 1.0]
            
            # If we have too many requests in the last second, wait
            if len(self.requests) >= self.max_requests_per_second:
                # Calculate how long to wait
                oldest_request = min(self.requests)
                wait_time = 1.0 - (now - oldest_request)
                if wait_time > 0:
                    print(f"Rate limiting: waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    # Update now after waiting
                    now = time.time()
                    # Remove old requests again
                    self.requests = [req_time for req_time in self.requests if now - req_time < 1.0]
            
            # Record this request
            self.requests.append(now)

# Create global rate limiter
rate_limiter = RateLimiter(MAX_REQUESTS_PER_SECOND)

# Synchronous rate limiter for fallback
class SyncRateLimiter:
    def __init__(self, max_requests_per_second: int):
        self.max_requests_per_second = max_requests_per_second
        self.requests = []
        
    def acquire(self):
        now = time.time()
        # Remove requests older than 1 second
        self.requests = [req_time for req_time in self.requests if now - req_time < 1.0]
        
        # If we have too many requests in the last second, wait
        if len(self.requests) >= self.max_requests_per_second:
            # Calculate how long to wait
            oldest_request = min(self.requests)
            wait_time = 1.0 - (now - oldest_request)
            if wait_time > 0:
                print(f"Rate limiting: waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                # Update now after waiting
                now = time.time()
                # Remove old requests again
                self.requests = [req_time for req_time in self.requests if now - req_time < 1.0]
        
        # Record this request
        self.requests.append(now)

sync_rate_limiter = SyncRateLimiter(MAX_REQUESTS_PER_SECOND)

async def search_pm(combined_query, condition_query=None, journal=None, sex=None, age=None, date_from=None, date_to=None, page=1, page_size=10, sort='relevance', sort_order=None):
    try:
        # For search requests, we need to fetch all results then paginate
        # since we want to apply BM25 reranking to all results
        term = combined_query.replace("+", " ")
        if condition_query and condition_query.strip():
            term += f" AND {condition_query}"
        if journal:
            term += f' AND "{journal}"[ta]'
        if sex:
            term += f' AND {sex}[filter]'
        if age:
            term += f' AND {age}[filter]'
        if date_from or date_to:
            df = date_from or "1800/01/01"
            dt = date_to or "3000/01/01"
            term += f' AND ({df}:{dt}[dp])'
        
        print(f"Searching PubMed with query: {term}")
        
        # Try PubMed first
        all_pmids = await fetch_all_pmids_paginated(term, sort=sort, sort_order=sort_order, max_limit=MAX_PMIDS_LIMIT, db="pubmed")
        total = len(all_pmids)
        db_used = "pubmed"
        
        print(f"# total PMIDs found in PubMed: {total}")
        
        # If PubMed fails or returns no results, try PMC as fallback
        if not all_pmids:
            print("No results found in PubMed, trying PMC as fallback...")
            all_pmids = await fetch_all_pmids_paginated(term, sort=sort, sort_order=sort_order, max_limit=MAX_PMIDS_LIMIT, db="pmc")
            total = len(all_pmids)
            db_used = "pmc"
            print(f"# total PMC IDs found: {total}")
            
            if not all_pmids:
                print("No results found in both PubMed and PMC.")
                return {"results": [], "total": 0, "page": page, "page_size": page_size, "applied_query": term}

        print(f"About to fetch detailed data for {len(all_pmids)} IDs from {db_used.upper()}")
        
        # Fetch complete data using the unified XML approach with the correct database
        results = await fetch_pubmed_data(all_pmids, db=db_used)
        
        print(f"Successfully fetched detailed data for {len(results)} PMIDs")

        # Extract metadata for each result using the new unified function
        for doc in results:
            try:
                extract_all_metadata_from_pm(doc)
            except Exception as e:
                print(f"Error extracting metadata for PMID {doc.get('pmid', 'unknown')}: {e}")
                # If metadata extraction fails, set default values
                if '_meta' not in doc:
                    doc['_meta'] = {}
                doc['_meta']['study_type'] = 'NA'
                doc['_meta']['phase'] = 'NA'
                doc['study_type'] = 'NA'
                doc['phase'] = 'NA'
                doc['design_allocation'] = 'NA'
                doc['observational_model'] = 'NA'

        # Apply pagination to the results
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = results[start_idx:end_idx]

        return {
            "results": paginated_results,
            "total": total,  # Return actual total count
            "page": page,
            "page_size": page_size,
            "applied_query": term
        }
    except Exception as e:
        import traceback
        print(f"PubMed API error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return {"results": [], "total": 0, "page": page, "page_size": page_size, "applied_query": term if 'term' in locals() else combined_query}

async def fetch_all_pmids_paginated(query: str, sort='relevance', sort_order=None, max_limit: int = MAX_PMIDS_LIMIT, db: str = "pubmed") -> List[str]:
    """
    Fetch PMIDs/PMCIDs for a query using paginated E-Search requests with a maximum limit.
    Uses proper rate limiting to stay within NCBI limits.
    Supports both pubmed and pmc databases.
    """
    all_pmids = []
    
    # First, get the total count with rate limiting
    await rate_limiter.acquire()
    initial_params = {
        "db": db,
        "term": query,
        "retmode": "json",
        "retmax": 0,  # Just get count
        "tool": NCBI_TOOL_NAME,
        "email": NCBI_API_EMAIL,
        "api_key": NCBI_API_KEY
    }
    
    try:
        response = requests.get(NCBI_ESEARCH, params=initial_params, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Defensive: check for 'esearchresult' and 'count'
        if 'esearchresult' not in data or 'count' not in data['esearchresult']:
            print(f"❌ Unexpected E-Search response structure for {db}: {json.dumps(data, indent=2)}")
            return []
        total_count = int(data['esearchresult']['count'])
        print(f"📄 Total {db.upper()} IDs found in NCBI: {total_count}")
        print(f"data: {data}")
        
        if total_count == 0:
            return []
        
        # Apply our limit
        actual_limit = min(total_count, max_limit)
        print(f"📄 Will fetch up to {actual_limit} {db.upper()} IDs (limit: {max_limit})")
            
    except Exception as e:
        print(f"❌ Failed to retrieve total count from {db}: {e}")
        return []
    
    # Now fetch PMIDs in chunks with sequential processing (no concurrency)
    try:
        async with aiohttp.ClientSession() as session:
            # Only fetch up to our limit
            for start_pos in range(0, actual_limit, ESEARCH_MAX_IDS):
                # Don't exceed our limit
                if len(all_pmids) >= max_limit:
                    print(f"✅ Reached maximum limit of {max_limit} PMIDs")
                    break
                
                # Rate limit each request
                await rate_limiter.acquire()
                
                # Calculate how many to fetch in this request
                remaining = max_limit - len(all_pmids)
                fetch_count = min(ESEARCH_MAX_IDS, remaining)
                
                params = {
                    "db": db,
                    "term": query,
                    "retmode": "json",
                    "retstart": start_pos,
                    "retmax": fetch_count,
                    "sort": sort,
                    "tool": NCBI_TOOL_NAME,
                    "email": NCBI_API_EMAIL,
                    "api_key": NCBI_API_KEY
                }
                if sort_order:
                    params["sort_order"] = sort_order
                
                try:
                    async with session.get(NCBI_ESEARCH, params=params, timeout=15) as response:
                        response.raise_for_status()
                        data = await response.json()
                        pmids = data['esearchresult']['idlist']
                        all_pmids.extend(pmids)
                        print(f"✅ Retrieved {len(pmids)} {db.upper()} IDs (start={start_pos}, total so far: {len(all_pmids)})")
                        
                        if not pmids:  # No more results
                            break
                        
                        # Check if we've reached our limit
                        if len(all_pmids) >= max_limit:
                            print(f"✅ Reached maximum limit of {max_limit} {db.upper()} IDs")
                            break
                            
                except Exception as e:
                    print(f"⚠️ Error at retstart={start_pos}: {e}")
                    # For 429 errors or other API errors, wait longer before continuing
                    if "429" in str(e) or "Invalid control character" in str(e):
                        print("API error detected, waiting 2 seconds...")
                        await asyncio.sleep(2)
                    continue
                    
    except ImportError:
        # Fallback to synchronous requests if aiohttp is not available
        print("aiohttp not available, falling back to synchronous E-Search")
        all_pmids = _fetch_all_pmids_sync(query, sort, sort_order, actual_limit, max_limit, db)
    
    # Ensure we don't exceed the limit
    if len(all_pmids) > max_limit:
        all_pmids = all_pmids[:max_limit]
    
    print(f"🎉 Done. Total collected {db.upper()} IDs: {len(all_pmids)} (limit: {max_limit})")
    return all_pmids

def _fetch_all_pmids_sync(query: str, sort: str, sort_order: Optional[str], total_count: int, max_limit: int, db: str = "pubmed") -> List[str]:
    """Synchronous fallback for fetching PMIDs/PMCIDs with proper rate limiting and limit."""
    all_pmids = []
    actual_limit = min(total_count, max_limit)
    
    for start_pos in range(0, actual_limit, ESEARCH_MAX_IDS):
        # Don't exceed our limit
        if len(all_pmids) >= max_limit:
            print(f"✅ Reached maximum limit of {max_limit} {db.upper()} IDs")
            break
        
        # Apply rate limiting
        sync_rate_limiter.acquire()
        
        # Calculate how many to fetch in this request
        remaining = max_limit - len(all_pmids)
        fetch_count = min(ESEARCH_MAX_IDS, remaining)
        
        params = {
            "db": db,
            "term": query,
            "retmode": "json",
            "retstart": start_pos,
            "retmax": fetch_count,
            "sort": sort,
            "tool": NCBI_TOOL_NAME,
            "email": NCBI_API_EMAIL,
            "api_key": NCBI_API_KEY
        }
        if sort_order:
            params["sort_order"] = sort_order
        
        try:
            response = requests.get(NCBI_ESEARCH, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            pmids = data['esearchresult']['idlist']
            
            if not pmids:
                print("✅ Retrieval complete.")
                break
                
            all_pmids.extend(pmids)
            print(f"✅ Retrieved {len(pmids)} {db.upper()} IDs (start={start_pos}, total so far: {len(all_pmids)})")
            
            # Check if we've reached our limit
            if len(all_pmids) >= max_limit:
                print(f"✅ Reached maximum limit of {max_limit} {db.upper()} IDs")
                break
            
        except Exception as e:
            print(f"⚠️ Error at retstart={start_pos} for {db}: {e}")
            # For 429 errors or other API errors, wait longer before continuing
            if "429" in str(e) or "Invalid control character" in str(e):
                print("API error detected, waiting 2 seconds...")
                time.sleep(2)
            continue
    
    # Ensure we don't exceed the limit
    if len(all_pmids) > max_limit:
        all_pmids = all_pmids[:max_limit]
    
    return all_pmids

def rerank_pm_results_with_bm25(query: str, pm_results: list) -> list:
    """
    Rerank PubMed results using BM25 algorithm with title, abstract, and keywords.
    Now uses rich data from the unified XML parsing approach.
    """
    if not pm_results or not query:
        return pm_results

    # Build corpus with richer text content
    corpus_texts = []
    for doc in pm_results:
        text_parts = []
        
        # Title
        title = doc.get("title", "") or ""
        if title:
            text_parts.append(title)
        
        # Abstract (structured or simple)
        abstract_data = doc.get("abstract")
        if abstract_data:
            if isinstance(abstract_data, dict):
                # Structured abstract with labels
                abstract_text = " ".join(str(v) for v in abstract_data.values() if v is not None)
            elif isinstance(abstract_data, str):
                abstract_text = abstract_data
            else:
                abstract_text = ""
            
            if abstract_text.strip():
                text_parts.append(abstract_text.strip())
        
        # Keywords (from our rich metadata)
        keywords = doc.get("keywords", [])
        if keywords:
            text_parts.append(" ".join(keywords))
        
        # MeSH headings (descriptors only for simplicity)
        mesh_headings = doc.get("mesh_headings", [])
        if mesh_headings:
            mesh_terms = []
            for mesh in mesh_headings:
                if isinstance(mesh, dict):
                    descriptor = mesh.get("descriptor", "")
                    if descriptor:
                        mesh_terms.append(str(descriptor))
                elif mesh:  # If mesh is a string or other type
                    mesh_terms.append(str(mesh))
            if mesh_terms:
                text_parts.append(" ".join(mesh_terms))
        
        # Journal name for additional context
        journal = doc.get("journal", "") or ""
        if journal:
            text_parts.append(journal)
        
        # Combine all text
        combined_text = " ".join(text_parts).strip()
        corpus_texts.append(combined_text)

    # Tokenize corpus
    tokenized_corpus = [doc_text.lower().split() for doc_text in corpus_texts if doc_text]

    if not tokenized_corpus:
        return pm_results

    # Apply BM25
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query.lower().split()
    raw_scores = bm25.get_scores(tokenized_query)

    # Normalize scores to 0-1 range
    max_s, min_s = max(raw_scores), min(raw_scores)
    norm_scores = [(s - min_s) / (max_s - min_s) if max_s > min_s else 0.0 for s in raw_scores]

    # Add original rank bonus to favor higher-ranked results
    original_weight = 0.2
    L = len(pm_results)
    for i, doc in enumerate(pm_results):
        bonus = (L - i) / L * original_weight
        doc["bm25_score"] = norm_scores[i] + bonus

    # Sort by BM25 score
    return sorted(pm_results,
                  key=lambda x: x.get("bm25_score", 0.0),
                  reverse=True)

def fetch_abstracts(pmids: List[str], db: str = "pubmed") -> Dict[str, Optional[dict]]:
    """
    Fetch abstracts for given PMIDs/PMCIDs using the unified XML approach.
    This is a simplified version that leverages our new fetch_pubmed_data function.
    
    Args:
        pmids: List of PMIDs or PMCIDs
        db: Database to use ("pubmed" or "pmc")
    
    Returns: { "PMID/PMCID": abstract_dict | None }
    """
    if not pmids:
        return {}

    # Use the synchronous version for simplicity since this is called from sync context
    results = _fetch_pubmed_data_sync(pmids, db)
    
    # Extract just the abstracts
    abstracts = {}
    for result in results:
        id_key = result.get("pmid") if db == "pubmed" else result.get("pmcid")
        if id_key:
            abstracts[id_key] = result.get("abstract")
    
    # Ensure all requested PMIDs have an entry
    for pmid in pmids:
        if pmid not in abstracts:
            abstracts[pmid] = None
    
    return abstracts

async def _fetch_with_aiohttp(url: str, params: Dict, session: aiohttp.ClientSession) -> str:
    """Helper to make an async HTTP request with rate limiting."""
    params["api_key"] = NCBI_API_KEY
    
    # Apply rate limiting
    await rate_limiter.acquire()
    
    try:
        async with session.get(url, params=params, timeout=15) as response:
            response.raise_for_status()
            text = await response.text()
            print(f"Fetched {url}. | # PMIDS in params: {len(params['id'].split(','))}")
            return text
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return ""

def _fetch_with_requests(url: str, params: Dict) -> str:
    """Helper to make a synchronous HTTP request with rate limiting."""
    params["api_key"] = NCBI_API_KEY
    
    # Apply rate limiting
    sync_rate_limiter.acquire()
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        print(f"Fetched {url} | # PMIDs: {len(params['id'].split(','))}")
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return ""

async def fetch_pubmed_data(pmids: List[str], db: str = "pubmed") -> List[Dict]:
    """
    Fetch complete PubMed/PMC data for given PMIDs/PMCIDs using XML EFETCH API.
    Uses sequential processing with proper rate limiting instead of concurrent requests.
    
    Args:
        pmids: List of PMIDs or PMCIDs
        db: Database to use ("pubmed" or "pmc")
    
    Returns: List of complete PubMed/PMC records with all metadata, abstracts, and NCT IDs.
    """
    if not pmids:
        return []

    print(f"Starting fetch_pubmed_data for {len(pmids)} {db.upper()} IDs")
    results = []
    
    try:
        # Use sequential processing instead of concurrent to respect rate limits
        async with aiohttp.ClientSession() as session:
            total_chunks = (len(pmids) + EFETCH_MAX_IDS - 1) // EFETCH_MAX_IDS
            
            for i in range(0, len(pmids), EFETCH_MAX_IDS):
                chunk_ids = pmids[i:i + EFETCH_MAX_IDS]
                chunk_idx = i // EFETCH_MAX_IDS + 1
                
                print(f"Fetching XML data for chunk {chunk_idx}/{total_chunks}: {len(chunk_ids)} {db.upper()} IDs")
                params = {
                    "db": db,
                    "id": ",".join(chunk_ids),
                    "retmode": "xml",
                    "tool": NCBI_TOOL_NAME,
                    "email": NCBI_API_EMAIL
                }
                
                xml_content = await _fetch_with_aiohttp(NCBI_EFETCH, params, session)
                if not xml_content:
                    print(f"Warning: No XML content returned for chunk {chunk_idx}")
                    continue
                
                # Parse XML and convert to our standard format
                try:
                    if db == "pmc":
                        # PMC returns different XML structure, we'll handle basic fields
                        parsed_data = parse_pmc_xml(xml_content)
                    else:
                        # PubMed XML parsing
                        parsed_data = parse_pubmed_xml(xml_content)
                    print(f"Parsed {len(parsed_data)} records from chunk {chunk_idx}")
                except Exception as e:
                    print(f"Error parsing XML for chunk {chunk_idx}: {e}")
                    continue
                
                chunk_results = []
                
                for id_val in chunk_ids:
                    if id_val in parsed_data:
                        data = parsed_data[id_val]
                        # Convert to the format expected by the rest of the system
                        result = {
                            "source": "PMC" if db == "pmc" else "PM",
                            "type": "PMC" if db == "pmc" else "PM",
                            "id": id_val,
                            "pmid": data.get("pmid") if db == "pubmed" else None,
                            "pmcid": data.get("pmcid") if db == "pmc" else data.get("pmcid"),
                            "title": data.get("title", ""),
                            "journal": data.get("journal", ""),
                            "authors": [author.get("name", "") for author in data.get("authors", [])],
                            "pubDate": data.get("pub_date", ""),
                            "doi": data.get("doi"),
                            "abstract": data.get("abstract"),
                            "score": None,
                            "ref_nctids": data.get("ref_nctids", []),
                            # Additional rich metadata
                            "journal_abbrev": data.get("journal_abbrev", ""),
                            "journal_issn": data.get("journal_issn"),
                            "pub_year": data.get("pub_year"),
                            "article_date": data.get("article_date"),
                            "pii": data.get("pii"),
                            "language": data.get("language", []),
                            "publication_types": data.get("publication_types", []),
                            "mesh_headings": data.get("mesh_headings", []),
                            "keywords": data.get("keywords", []),
                            "chemicals": data.get("chemicals", []),
                            "grants": data.get("grants", []),
                            "country": data.get("country"),
                            "nlm_unique_id": data.get("nlm_unique_id"),
                            "citation_subset": data.get("citation_subset", []),
                            "coi_statement": data.get("coi_statement"),
                            "pagination": data.get("pagination"),
                            "volume": data.get("volume"),
                            "issue": data.get("issue")
                        }
                        # Set the appropriate ID field based on database
                        if db == "pmc":
                            result["pmcid"] = id_val
                        else:
                            result["pmid"] = id_val
                        
                        chunk_results.append(result)
                    else:
                        print(f"Warning: {db.upper()} ID {id_val} not found in parsed XML for chunk {chunk_idx}")
                
                results.extend(chunk_results)
                print(f"Chunk {chunk_idx} completed: {len(chunk_results)} results (total so far: {len(results)})")

    except ImportError:
        # Fallback to synchronous requests
        print("aiohttp not available, falling back to synchronous requests")
        results = _fetch_pubmed_data_sync(pmids, db)

    print(f"fetch_pubmed_data completed: {len(results)} results")
    return results

def _fetch_pubmed_data_sync(pmids: List[str], db: str = "pubmed") -> List[Dict]:
    """Synchronous fallback for fetching PubMed/PMC data with proper rate limiting."""
    print(f"Starting sync fetch for {len(pmids)} {db.upper()} IDs")
    results = []
    
    total_chunks = (len(pmids) + EFETCH_MAX_IDS - 1) // EFETCH_MAX_IDS
    
    for i in range(0, len(pmids), EFETCH_MAX_IDS):
        chunk_ids = pmids[i:i + EFETCH_MAX_IDS]
        chunk_num = i // EFETCH_MAX_IDS + 1
        print(f"Fetching XML data for chunk {chunk_num}/{total_chunks} with {len(chunk_ids)} {db.upper()} IDs")
        
        params = {
            "db": db,
            "id": ",".join(chunk_ids),
            "retmode": "xml",
            "tool": NCBI_TOOL_NAME,
            "email": NCBI_API_EMAIL
        }
        
        xml_content = _fetch_with_requests(NCBI_EFETCH, params)
        if not xml_content:
            print(f"Warning: No XML content returned for chunk {chunk_num}")
            continue
        
        try:
            # Parse XML and convert to our standard format
            if db == "pmc":
                parsed_data = parse_pmc_xml(xml_content)
            else:
                parsed_data = parse_pubmed_xml(xml_content)
            print(f"Parsed {len(parsed_data)} records from chunk {chunk_num}")
            
            chunk_results = 0
            for id_val in chunk_ids:
                if id_val in parsed_data:
                    data = parsed_data[id_val]
                    # Convert to the format expected by the rest of the system
                    result = {
                        "source": "PMC" if db == "pmc" else "PM",
                        "type": "PMC" if db == "pmc" else "PM",
                        "id": id_val,
                        "pmid": data.get("pmid") if db == "pubmed" else data.get("pmid"),
                        "pmcid": data.get("pmcid"),
                        "title": data.get("title", ""),
                        "journal": data.get("journal", ""),
                        "authors": [author.get("name", "") for author in data.get("authors", [])],
                        "pubDate": data.get("pub_date", ""),
                        "doi": data.get("doi"),
                        "abstract": data.get("abstract"),
                        "score": None,
                        "ref_nctids": data.get("ref_nctids", []),
                        # Additional rich metadata
                        "journal_abbrev": data.get("journal_abbrev", ""),
                        "journal_issn": data.get("journal_issn"),
                        "pub_year": data.get("pub_year"),
                        "article_date": data.get("article_date"),
                        "pii": data.get("pii"),
                        "language": data.get("language", []),
                        "publication_types": data.get("publication_types", []),
                        "mesh_headings": data.get("mesh_headings", []),
                        "keywords": data.get("keywords", []),
                        "chemicals": data.get("chemicals", []),
                        "grants": data.get("grants", []),
                        "country": data.get("country"),
                        "nlm_unique_id": data.get("nlm_unique_id"),
                        "citation_subset": data.get("citation_subset", []),
                        "coi_statement": data.get("coi_statement"),
                        "pagination": data.get("pagination"),
                        "volume": data.get("volume"),
                        "issue": data.get("issue")
                    }
                    # Set the appropriate ID field based on database
                    if db == "pmc":
                        result["pmcid"] = id_val
                    else:
                        result["pmid"] = id_val
                        
                    results.append(result)
                    chunk_results += 1
                else:
                    print(f"Warning: {db.upper()} ID {id_val} not found in parsed XML for chunk {chunk_num}")
            
            print(f"Chunk {chunk_num} completed: {chunk_results} results (total so far: {len(results)})")
                    
        except Exception as e:
            print(f"Error processing XML for chunk {chunk_num}: {str(e)}")
            continue
    
    print(f"Sync processing completed: {len(results)} total results")
    return results

def parse_pmc_xml(xml_content: str) -> Dict[str, Dict]:
    """
    Parse PMC XML response and extract basic information.
    PMC XML structure is different from PubMed XML.
    """
    from xml.etree import ElementTree as ET
    
    try:
        root = ET.fromstring(xml_content)
        parsed_data = {}
        
        # PMC articles are in <article> elements
        for article in root.findall('.//article'):
            pmcid = None
            pmid = None
            
            # Extract PMC ID from article-id elements
            for article_id in article.findall('.//article-id'):
                pub_id_type = article_id.get('pub-id-type', '')
                if pub_id_type == 'pmc':
                    pmcid = article_id.text
                elif pub_id_type == 'pmid':
                    pmid = article_id.text
            
            if not pmcid:
                continue
                
            # Extract basic metadata
            title_elem = article.find('.//article-title')
            title = title_elem.text if title_elem is not None else ""
            
            # Extract journal info
            journal_elem = article.find('.//journal-title')
            journal = journal_elem.text if journal_elem is not None else ""
            
            # Extract authors
            authors = []
            for contrib in article.findall('.//contrib[@contrib-type="author"]'):
                name_elem = contrib.find('.//name')
                if name_elem is not None:
                    surname = name_elem.find('surname')
                    given_names = name_elem.find('given-names')
                    if surname is not None and given_names is not None:
                        authors.append({
                            "name": f"{given_names.text} {surname.text}",
                            "lastname": surname.text,
                            "forename": given_names.text
                        })
            
            # Extract abstract
            abstract_elem = article.find('.//abstract')
            abstract = ""
            if abstract_elem is not None:
                # PMC abstracts can have structured content
                abstract_parts = []
                for p in abstract_elem.findall('.//p'):
                    if p.text:
                        abstract_parts.append(p.text)
                abstract = " ".join(abstract_parts) if abstract_parts else abstract_elem.text or ""
            
            # Extract publication date
            pub_date = ""
            pub_year = None
            for pub_date_elem in article.findall('.//pub-date'):
                year_elem = pub_date_elem.find('year')
                month_elem = pub_date_elem.find('month')
                day_elem = pub_date_elem.find('day')
                
                if year_elem is not None:
                    pub_year = year_elem.text
                    date_parts = [year_elem.text]
                    if month_elem is not None:
                        date_parts.append(month_elem.text.zfill(2))
                    if day_elem is not None:
                        date_parts.append(day_elem.text.zfill(2))
                    pub_date = "/".join(date_parts)
                    break
            
            # Extract DOI
            doi = None
            for article_id in article.findall('.//article-id'):
                if article_id.get('pub-id-type') == 'doi':
                    doi = article_id.text
                    break
            
            # Look for NCT IDs in the text content
            ref_nctids = []
            full_text = ET.tostring(article, encoding='unicode', method='text')
            nct_pattern = r'NCT\d{8}'
            import re
            ref_nctids = list(set(re.findall(nct_pattern, full_text, re.IGNORECASE)))
            
            parsed_data[pmcid] = {
                "pmcid": pmcid,
                "pmid": pmid,
                "title": title,
                "journal": journal,
                "authors": authors,
                "pub_date": pub_date,
                "pub_year": pub_year,
                "doi": doi,
                "abstract": abstract,
                "ref_nctids": ref_nctids,
                # Default values for fields that PMC might not have
                "journal_abbrev": "",
                "journal_issn": None,
                "article_date": pub_date,
                "pii": None,
                "language": ["eng"],  # Default to English
                "publication_types": [],
                "mesh_headings": [],
                "keywords": [],
                "chemicals": [],
                "grants": [],
                "country": None,
                "nlm_unique_id": None,
                "citation_subset": [],
                "coi_statement": None,
                "pagination": None,
                "volume": None,
                "issue": None
            }
        
        return parsed_data
        
    except Exception as e:
        print(f"Error parsing PMC XML: {e}")
        return {}

# Export the functions that are used by other modules
from .pm_metadata_extractor import (
    extract_study_type_from_pm, 
    extract_phase_from_pm, 
    normalize_design_allocation_from_pm as _normalize_design_allocation_pm,
    normalize_observational_model_from_pm as _normalize_observational_model_pm
)

# Add PMService class at the end of the file
class PMService:
    """PM Service class wrapper for function-based PM operations"""
    
    def get_paper_details(self, pmid: str, db: str = "pubmed") -> Optional[Dict[str, Any]]:
        """Get detailed paper information for a specific PMID/PMCID using efetch XML"""
        try:
            # Use the existing function which now supports both databases
            results = _fetch_pubmed_data_sync([pmid], db)
            if results:
                return results[0]
            return None
        except Exception as e:
            print(f"Error fetching {db.upper()} details for {pmid}: {str(e)}")
            return None