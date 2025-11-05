import os
import logging
import hashlib
import csv
import asyncio
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, Request
from services import pm_service, ctg_service
from services.query_service import get_query_service
from services.cache_service import generate_search_key, cache_search_results, get_cached_results
from services.filter_stats_service import calculate_filter_stats, ResultClassifier
from config import MAX_FETCH_SIZE, DEFAULT_PAGE_SIZE

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory caches for PubMed and ClinicalTrials.gov results
PUBMED_CACHE: Dict[str, Dict] = {}
CTG_CACHE: Dict[str, Dict] = {}

# Directory for saving CSV logs
LOG_DIR = "./logs/search_results"
os.makedirs(LOG_DIR, exist_ok=True)

# Define the request body schema with updated fields
class SearchRequest(BaseModel):
    cond: Optional[str] = None
    intr: Optional[str] = None
    other_term: Optional[str] = None
    journal: Optional[str] = None
    sex: Optional[str] = None
    age: Optional[str] = None
    studyType: Optional[List] = None
    phase: Optional[List] = None
    sponsor: Optional[List] = None
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = None
    user_query: Optional[str] = None
    pubmed_query: Optional[str] = None
    ctg_query: Optional[str] = None
    isRefined: Optional[bool] = False
    page: Optional[int] = 1
    pageSize: Optional[int] = DEFAULT_PAGE_SIZE
    sources: Optional[List[str]] = ["PM", "CTG"]
    ctgPageToken: Optional[str] = None
    refinedQuery: Optional[dict] = None

class PageRequest(BaseModel):
    search_key: str
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

def _generate_cache_key(params: dict, source: str) -> str:
    """Generate a unique cache key based on search parameters for PubMed or CTG."""
    if source == "PM":
        cache_components = {
            "pubmed_query": params.get("pubmed_query", ""),
            "query": params.get("query", ""),
            "journal": params.get("journal", ""),
            "sex": params.get("sex", ""),
            "age": params.get("age", ""),
            "condition_query": params.get("condition_query", "")
        }
    elif source == "CTG":
        cache_components = {
            "ctg_query": params.get("ctg_query", ""),
            "query": params.get("query", ""),
            "cond": params.get("cond", ""),
            "intr": params.get("intr", ""),
            "studyType": params.get("studyType", ""),
            "city": params.get("city", ""),
            "state": params.get("state", ""),
            "country": params.get("country", ""),
            "phase": params.get("phase", ""),
            "gender": params.get("sex", ""),
            "ages": params.get("age", ""),
            "sponsor": params.get("sponsor", ""),
            "location": params.get("location", ""),
            "status": params.get("status", "")
        }
    else:
        raise ValueError(f"Invalid source: {source}")

    cache_string = "|".join(f"{k}:{v}" for k, v in sorted(cache_components.items()) if v)
    return hashlib.md5(cache_string.encode("utf-8")).hexdigest()

def _write_results_to_csv(request: Request, data: dict, refined_query: dict, search_params: dict, final_results: List[Dict]):
    """Write search results and metadata to a CSV file."""
    try:
        # Get client IP (or use 'unknown' if not available)
        client_ip = request.client.host if request.client else "unknown"
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize IP for filename (replace dots with underscores)
        safe_ip = client_ip.replace(".", "_")
        filename = os.path.join(LOG_DIR, f"search_{safe_ip}_{timestamp}.csv")
        
        # Prepare metadata
        metadata = [
            ["# Timestamp", datetime.now().isoformat()],
            ["# Client IP", client_ip],
            ["# Original Query", data.get("user_query", "")],
            ["# Refined Query", str(refined_query)],
            ["# API Query", search_params.get("query", "")],
            ["# Condition Query (PubMed)", search_params.get("condition_query", "")],
            ["# Filters", str({
                "journal": search_params.get("journal"),
                "sex": search_params.get("sex"),
                "age": search_params.get("age"),
                "studyType": search_params.get("studyType"),
                "phase": search_params.get("phase"),
                "sponsor": search_params.get("sponsor"),
                "location": search_params.get("location"),
                "status": search_params.get("status")
            })]
        ]
        
        # Prepare CSV data
        csv_data = []
        for item in final_results:
            row = {
                "source": item.get("type", ""),
                "id": item.get("id", ""),
                "title": item.get("title", ""),
                "bm25_score": str(item.get("bm25_score", "")),
                "pmids": ",".join(item.get("pmids", [])) if item.get("type") == "CTG" else item.get("pmid", ""),
                "journal": item.get("journal", "") if item.get("type") == "PM" else "",
                "status": item.get("status", "") if item.get("type") == "CTG" else ""
            }
            csv_data.append(row)
        
        # Write to CSV
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = ["source", "id", "title", "bm25_score", "pmids", "journal", "status"]
            # Write metadata as commented, padded rows
            for meta_row in metadata:
                padded = meta_row + [""] * (len(header) - len(meta_row))
                writer.writerow(padded)
            # Write actual header and data
            writer.writerow(header)
            for row in csv_data:
                writer.writerow([
                    row["source"], row["id"], row["title"],
                    row["bm25_score"], row["pmids"],
                    row["journal"], row["status"]
                ])
        
        logger.info(f"Saved search results to {filename}")
        
    except Exception as e:
        logger.error(f"Failed to write CSV: {e}")

@router.post("")
async def search(request: Request, body: SearchRequest):
    try:
        data = body.model_dump()
        logger.info("=== SEARCH REQUEST START ===")
        import time
        start = time.time()
        logger.info(f"Received search request: {data}")
        
        # Query refinement
        logger.info("Starting query refinement...")
        refined_query = await _get_or_create_refined_query(data)
        logger.info(f"Refined query result: {refined_query}")
        
        # Search parameters
        search_params = _build_search_params(data, refined_query, fetch_all=True)
        logger.info(f"Built search params: {search_params}")
        
        # Track if this is an initial search (cache miss)
        is_initial_search = False
        results = {}
        
        # Determine which sources to search based on available queries
        pubmed_query = data.get("pubmed_query")
        ctg_query = data.get("ctg_query")
        has_general_query = any([
            refined_query.get("combined_query"),
            data.get("user_query"),
            data.get("cond"),
            data.get("intr"),
            data.get("other_term")
        ])
        
        # Determine sources to search
        sources_to_search = []
        if pubmed_query or has_general_query:
            sources_to_search.append("PM")
        if ctg_query or has_general_query:
            sources_to_search.append("CTG")
            
        # Override with user-specified sources if provided and queries support it
        if data.get("sources"):
            user_sources = data.get("sources", [])
            final_sources = []
            for source in user_sources:
                if source == "PM" and (pubmed_query or has_general_query):
                    final_sources.append("PM")
                elif source == "CTG" and (ctg_query or has_general_query):
                    final_sources.append("CTG")
            sources_to_search = final_sources if final_sources else sources_to_search
        
        logger.info(f"Determined sources to search: {sources_to_search} (pubmed_query: {bool(pubmed_query)}, ctg_query: {bool(ctg_query)}, has_general_query: {has_general_query})")
        
        generate_dynamic_queries = not data.get("isRefined") 
        dynamic_queries = {}
        if generate_dynamic_queries:
            logger.info("Starting query generation...")
            dynamic_queries = await _create_dynamic_queries(refined_query)
            logger.info(f"dynamic query result: {dynamic_queries}")
        
        

        # Execute searches
        if "PM" in sources_to_search:
            logger.info("Searching PubMed...")
            # Check cache for PubMed results
            pm_cache_key = _generate_cache_key(search_params, source="PM")
            if pm_cache_key in PUBMED_CACHE:
                logger.info("Using cached PubMed results")
                results["pm"] = PUBMED_CACHE[pm_cache_key]
            else:
                results["pm"] = await _search_pubmed(search_params)
                PUBMED_CACHE[pm_cache_key] = results["pm"]
                logger.info(f"Cached PubMed results for key: {pm_cache_key}")
                is_initial_search = True
            logger.info(f"PubMed search completed. Results: {len(results['pm'].get('results', []))} items")
        
        if "CTG" in sources_to_search:
            logger.info("Searching ClinicalTrials.gov...")
            # Check cache for CTG results
            ctg_cache_key = _generate_cache_key(search_params, source="CTG")
            if ctg_cache_key in CTG_CACHE:
                logger.info("Using cached ClinicalTrials.gov results")
                results["ctg"] = CTG_CACHE[ctg_cache_key]
            else:
                results["ctg"] = await _search_clinicaltrials(search_params)
                CTG_CACHE[ctg_cache_key] = results["ctg"]
                logger.info(f"Cached ClinicalTrials.gov results for key: {ctg_cache_key}")
                is_initial_search = True
            logger.info(f"CTG search completed. Results: {len(results['ctg'].get('results', []))} items")
        
        # Merge and paginate results
        logger.info("Starting merge and pagination...")
        merged_results = _merge_and_paginate_results(
            results, 
            refined_query.get("combined_query", ""),
            page=data.get("page", 1),
            page_size=data.get("pageSize", DEFAULT_PAGE_SIZE)
        )
        
        # Log full results to CSV on initial search
        if is_initial_search:
            csv_results = _get_full_merged_results_for_csv(results, refined_query.get("combined_query", ""))
            _write_results_to_csv(request, data, refined_query, search_params, csv_results)
        
        # Prepare results with extracted metadata
        all_results = []
        pm_results_with_meta = []
        ctg_results_with_meta = []
        
        if "PM" in data.get("sources", ["PM", "CTG"]):
            pm_results = results.get("pm", {}).get("results", [])
            for r in pm_results:
                enhanced_result = {
                    **r,
                    'type': 'PM'
                }
                pm_results_with_meta.append(enhanced_result)
                all_results.append(enhanced_result)
                
        if "CTG" in data.get("sources", ["PM", "CTG"]):
            ctg_results = results.get("ctg", {}).get("results", [])
            for r in ctg_results:
                enhanced_result = {
                    **r,
                    'type': 'CTG',
                    '_meta': {
                        'phase': r.get('phase'),
                        'study_type': r.get('study_type'),
                        'design_allocation': r.get('design_allocation'),
                        'observational_model': r.get('observational_model'),
                        'phase_extraction_source': 'CTG_DATABASE',
                        'study_type_extraction_source': 'CTG_DATABASE', 
                        'design_allocation_extraction_source': 'CTG_DATABASE',
                        'observational_model_extraction_source': 'CTG_DATABASE',
                        'start_date': r.get('start_date'),
                        'completion_date': r.get('completion_date')
                    }
                }
                ctg_results_with_meta.append(enhanced_result)
                all_results.append(enhanced_result)
                
        filter_stats = calculate_filter_stats(pm_results_with_meta, ctg_results_with_meta)
        
        filter_stats['merged_count'] = merged_results["counts"].get("merged", 0)

        search_key = generate_search_key(data)
        cache_data = {
            "all_results": all_results,
            "search_params": data,
            "timestamp": datetime.now().isoformat(),
            "filter_stats": filter_stats
        }
        cache_search_results(search_key, cache_data)
        
        # Add cache status information
        from services.cache_service import get_cache_info
        cache_info = get_cache_info()
        
        response = {
            "search_key": search_key,
            "refinedQuery": refined_query,
            "appliedQueries": {
                "pubmed": results.get("pm", {}).get("applied_query", ""),
                "clinicaltrials": results.get("ctg", {}).get("applied_query", "")
            },
            "results": merged_results["results"],
            "additional_queries": dynamic_queries,
            "counts": merged_results["counts"],
            "total": merged_results["total"],
            "page": data.get("page", 1),
            "pageSize": data.get("pageSize", DEFAULT_PAGE_SIZE),
            "totalPages": merged_results["totalPages"],
            "filter_stats": filter_stats,
            "cache_status": {
                "redis_available": cache_info["redis_available"],
                "filtering_available": True,
                "cache_type": "Redis" if cache_info["redis_available"] else "Memory"
            }
        }
        
        logger.info(f"Final response structure: total={response.get('total')}, page={response.get('page')}")
        logger.info(f"Filter stats: {filter_stats}")

        logger.info("=== SEARCH REQUEST END ===")
        end = time.time()
        print(f"FULL SEARCH TIME: {end-start}s")
        
        return response
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Search failed")
    
@router.post("/patient")
async def patient_search(request: Request, body: SearchRequest):
    try:
        data = body.model_dump()
        logger.info("=== SEARCH REQUEST START ===")
        logger.info(f"Received search request: {data}")
        
        # Query generation
        logger.info("Starting patient query generation...")
        queries = await _create_patient_queries(data)
        logger.info(f"Generated query result: {queries}")

        search_results = { "final_results": [] }
        default = queries.get("default")
        r = await _get_query_results(default)
        r["name"] = "Default"
        r["modified"] = default.get("modified", [])
        desc = ""
        flist = ["cond", "intr", "other_term", "city", "state", "country", "age", "sex", "studyType", "phase", "sponsor"]
        if default.get("query"):
            desc += f"User Search: '{default.get("query")}'"
        for k, v in data.items():
            if v and k in flist:
                desc += f'/n{k}: {v}'
        r["description"] = desc
        search_results["final_results"].append(r)

        '''
        x=1
        for q in queries.get("expanded_queries"):
            s4 = time.time()
            res = await _get_query_results(q["filters"])
            res["name"] = q.get("type", "")
            res["description"] = q.get("description", "")
            res["modified"] = q.get("modified", [])
            search_results["final_results"].append(res)
            e4 = time.time()
            print(f"SEARCH TIMER - 4. additional query search #{x}: {e4-s4:.2f} seconds")
            x+=1 
        '''
        tasks = []
        for q in queries.get("expanded_queries"):
            tasks.append(_get_query_results(q["filters"]))

        results_list = await asyncio.gather(*tasks)

        for q, res in zip(queries.get("expanded_queries"), results_list):
            res["name"] = q.get("type", "")
            res["description"] = q.get("description", "")
            res["modified"] = q.get("modified", [])
            search_results["final_results"].append(res)
 
       # ids = await ctg_service.get_patient_results(params)
        return search_results
       # return {
        #    "params": params,
         #   "study_ids": ids
        #} 
        
    except Exception as e:
        logger.error(f"Patient query refinement error: {str(e)}")

@router.post("/patient/paging")
async def patient_page(request: Request, body: PageRequest):
    try:
        data = body.model_dump()
        logger.info(data)

        cache_results = get_cached_results(data["search_key"])
        all_results = cache_results.get("all_results", "")
        logger.info("Found cached results. Total: %d", len(all_results))

        start_idx = (data["page"] - 1) * data["page_size"]
        end_idx = start_idx + data["page_size"]

        return all_results[start_idx:end_idx]

    except Exception as e:
        logger.error(f"Patient mode pagination error: {str(e)}")
        return {"error": str(e)}
    

async def _create_dynamic_queries(data: dict) -> dict:

    query_service = get_query_service()
    query_terms = query_service.generate_query_terms(data)

    queries = []
    c = data.get("cond", "")
    i = data.get("intr", "")
    o = data.get("other_term", "")

    if c:
        l1 = [c] + query_terms["cond"]
        c1 = ' OR '.join(l1)
        # Only include non-empty components in the combined_query
        combined_parts = []
        if c1:
            combined_parts.append(f"({c1})")
        if i:
            combined_parts.append(f"({i})")
        if o:
            combined_parts.append(f"({o})")
        q =  {
            "combined_query": ' AND '.join(combined_parts),
            "cond": c1,
            "intr": i,
            "other_term": o,
            "name": "Refined Condition",
            "terms": l1
        }
        queries.append(q)

    if i:
        l1 = [i] + query_terms["intr"]
        i1 = ' OR '.join(l1)
        combined_parts = []
        if c:
            combined_parts.append(f"({c})")
        if i1:
            combined_parts.append(f"({i1})")
        if o:
            combined_parts.append(f"({o})")
        q =  {
            "combined_query": ' AND '.join(combined_parts),
            "cond": c,
            "intr": i1,
            "other_term": o,
            "name": "Refined Intervention",
            "terms": l1
        }
        queries.append(q)

    if o:
        l1 = [o] + query_terms["other"]
        o1 = ' OR '.join(l1)
        combined_parts = []
        if c:
            combined_parts.append(f"({c})")
        if i:
            combined_parts.append(f"({i})")
        if o1:
            combined_parts.append(f"({o1})")
        q =  {
            "combined_query": ' AND '.join(combined_parts),
            "cond": c,
            "intr": i,
            "other_term": o1,
            "name": "Refined Other Term",
            "terms": l1
        }
        queries.append(q)
    return queries

async def _get_query_results(data: dict) -> dict:
    results = {}
    # Determine sources to search
    sources_to_search = ["CTG"]

    if "CTG" in sources_to_search:
        logger.info("Searching ClinicalTrials.gov...")
        # Check cache for CTG results
        ctg_cache_key = _generate_cache_key(data, source="CTG")
        if ctg_cache_key in CTG_CACHE:
            logger.info("Using cached ClinicalTrials.gov results")
            results["ctg"] = CTG_CACHE[ctg_cache_key]
        else:
            results["ctg"] = await ctg_service.get_patient_results(data)
            CTG_CACHE[ctg_cache_key] = results["ctg"]
            logger.info(f"Cached ClinicalTrials.gov results for key: {ctg_cache_key}")
        logger.info(f"CTG search completed. Results: {len(results['ctg'].get('results', []))} items")
    
    # Merge and paginate results
    logger.info("Starting merge and pagination...")
    merged_results = _merge_and_paginate_results(
        results, 
        data.get("user_query", ""),
        page=data.get("page", 1),
        page_size=data.get("pageSize", DEFAULT_PAGE_SIZE)
    )

    all_results = []
    pm_results_with_meta = []
    ctg_results_with_meta = []

    if "CTG" in sources_to_search:
        ctg_results = results.get("ctg", {}).get("results", [])
        for r in ctg_results:
            enhanced_result = {
                **r,
                'type': 'CTG',
                '_meta': {
                    'phase': r.get('phase'),
                    'study_type': r.get('study_type'),
                    'design_allocation': r.get('design_allocation'),
                    'observational_model': r.get('observational_model'),
                    'phase_extraction_source': 'CTG_DATABASE',
                    'study_type_extraction_source': 'CTG_DATABASE', 
                    'design_allocation_extraction_source': 'CTG_DATABASE',
                    'observational_model_extraction_source': 'CTG_DATABASE',
                    'start_date': r.get('start_date'),
                    'completion_date': r.get('completion_date')
                }
            }
            ctg_results_with_meta.append(enhanced_result)
            all_results.append(enhanced_result)
            
    filter_stats = None #calculate_filter_stats(pm_results_with_meta, ctg_results_with_meta)
    
    #filter_stats['merged_count'] = merged_results["counts"].get("merged", 0)

    search_key = generate_search_key(data)
    cache_data = {
        "all_results": all_results,
        "search_params": data,
        "timestamp": datetime.now().isoformat(),
        "filter_stats": filter_stats
    }
    cache_search_results(search_key, cache_data)

    
    # Add cache status information
    from services.cache_service import get_cache_info
    cache_info = get_cache_info()
    response = {
        "search_key": search_key,
        "refinedQuery": data,
        "appliedQueries": {
            "pubmed": results.get("pm", {}).get("applied_query", ""),
            "clinicaltrials": results.get("ctg", {}).get("applied_query", "")
        },
        "results": merged_results["results"],
        "counts": merged_results["counts"],
        "total": merged_results["total"],
        "page": data.get("page", 1),
        "pageSize": data.get("pageSize", DEFAULT_PAGE_SIZE),
        "totalPages": merged_results["totalPages"],
        "filter_stats": filter_stats,
        "cache_status": {
            "redis_available": cache_info["redis_available"],
            "filtering_available": True,
            "cache_type": "Redis" if cache_info["redis_available"] else "Memory"
        }
    }
    return response

async def _create_patient_queries(data: dict) -> dict:
    refine_params = {
        "cond": data.get("cond"),
        "intr": data.get("intr"),
        "other_term": data.get("other_term"),
        "sex": data.get("sex"),
        "age": data.get("age"),
        "locStr": data.get("location"),
        "city": data.get("city"),
        "state": data.get("state"),
        "country": data.get("country"),
        "phase": data.get("phase"),
        "study_type": data.get("studyType"),
        "sponsor": data.get("sponsor"),
        "user_query": data.get("user_query")
    }

    logger.info(f"Creating default query with params: {refine_params}")
    query_service = get_query_service()
    default = query_service.build_patient_default(refine_params)
    logger.info(f"Created new patient query: {default}")

    logger.info(f"Creating variant queries with params: {default}")
    query_service = get_query_service()
    queries = query_service.generate_patient_variations(default)
    logger.info(f"Created expanded patient queries: {queries}")

    return {
        "default": default,
        "expanded_queries": queries.get("queries")
    }

async def _get_or_create_refined_query(data: dict) -> dict:
    """Get existing refined query or create new one"""
    # Skip query refinement if direct queries are provided
    if data.get("pubmed_query") and data.get("ctg_query"):
        logger.info("Direct queries provided, skipping query refinement")
        return {
            "combined_query": "",
            "cond": "",
            "intr": ""
        }
    
    if data.get("isRefined") and data.get("refinedQuery"):
        logger.info("Using existing refined query")
        return data["refinedQuery"]
    
    refine_params = {
        "cond": data.get("cond"),
        "intr": data.get("intr"), 
        "other_term": data.get("other_term"),
        "user_query": data.get("user_query", "")
    }
    
    logger.info(f"Refining query with params: {refine_params}")
    query_service = get_query_service()
    refined = query_service.refine_query(refine_params)
    logger.info(f"Created new refined query: {refined}")
    return refined

def _build_search_params(data: dict, refined_query: dict, fetch_all: bool = False) -> dict:
    """Build unified search parameters with proper filter mapping"""
    # Use MAX_FETCH_SIZE when fetch_all is True, otherwise use user-requested pageSize or default
    page_size = MAX_FETCH_SIZE if fetch_all else data.get("pageSize", DEFAULT_PAGE_SIZE)
    
    # Check for direct queries first
    pubmed_query = data.get("pubmed_query")
    ctg_query = data.get("ctg_query")
    
    # Map frontend values to API values
    sex_mapping = {
        'MALE': 'Male',
        'FEMALE': 'Female', 
        'ALL': 'All'
    }
    
    age_mapping = {
        'child': 'Child',
        'adult': 'Adult', 
        'older adult': 'Older Adult'
    }
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    condition_query_path = os.path.join(base_dir, "../queries/pmConditionQuery.md")
    try:
        with open(condition_query_path, "r", encoding="utf-8") as f:
            condition_query = f.read().strip()
            if not condition_query:
                condition_query = None
                logger.warning("PM condition query file is empty")
    except FileNotFoundError:
        condition_query = None
        logger.warning("PM condition query file not found")
    
    params = {
        # Direct query handling
        "pubmed_query": pubmed_query,
        "ctg_query": ctg_query,
        
        # Query components (used when no direct queries)
        "query": refined_query.get("combined_query", ""),
        "cond": refined_query.get("cond"),
        "intr": refined_query.get("intr"),
        "other_term": refined_query.get("other_term", ""),
        "condition_query": condition_query,
        
        # PubMed-specific filters
        "journal": data.get("journal"),
        "sex": sex_mapping.get(data.get("sex"), data.get("sex")) if data.get("sex") else None,
        "age": age_mapping.get(data.get("age"), data.get("age")) if data.get("age") else None,
        
        # CTG-specific filters
        "studyType": data.get("studyType"),
        "phase": data.get("phase"),
        "status": data.get("status"),
        
        # Local DB filters
        "sponsor": data.get("sponsor"),
        "location": data.get("location"),
        
        # Pagination
        "page": 1 if fetch_all else data.get("page", 1),
        "pageSize": page_size,
        "ctgPageToken": data.get("ctgPageToken")
    }
    
    logger.info(f"Built search parameters: {params}")
    return params

async def _search_pubmed(params: dict) -> dict:
    logger.info("Starting PubMed search...")
    
    # Check for direct PubMed query
    pubmed_query = params.get("pubmed_query")
    if pubmed_query:
        logger.info(f"Using direct PubMed query: {pubmed_query}")
        # Use direct query, ignore all other filters and processing
        results = await pm_service.search_pm(
            combined_query=pubmed_query,
            condition_query=None,
            journal=None,
            sex=None,
            age=None,
            page=params["page"],
            page_size=params["pageSize"]
        )
    else:
        # Use normal refined query with filters
        results = await pm_service.search_pm(
            combined_query=params["query"],
            condition_query=params.get("condition_query"),
            journal=params.get("journal"),
            sex=params.get("sex"),
            age=params.get("age"),
            page=params["page"],
            page_size=params["pageSize"]
        )
    
    if not results or not results.get("results"):
        logger.warning("No PubMed results found")
        query_used = pubmed_query if pubmed_query else params["query"]
        return {"results": [], "total": 0, "query": query_used}
    
    # Apply BM25 reranking
    query_for_ranking = pubmed_query if pubmed_query else params["query"]
    if results["results"] and query_for_ranking:
        logger.info(f"Reranking {len(results['results'])} PM results")
        reranked = pm_service.rerank_pm_results_with_bm25(
            query_for_ranking, 
            results["results"]
        )
        results["results"] = reranked
    else:
        for item in results["results"]:
            item["bm25_score"] = None
    
    logger.info(f"PubMed search completed: {len(results['results'])} results")
    return results

async def _search_clinicaltrials(params: dict) -> dict:
    """Search ClinicalTrials.gov with proper filter application"""
    logger.info("Starting ClinicalTrials.gov search...")
    
    # Check for direct CTG query
    ctg_query = params.get("ctg_query")
    
    # Map sex values for CTG API
    ctg_sex_mapping = {
        'Male': 'MALE',
        'Female': 'FEMALE',
        'All': 'ALL'
    }
    
    # Determine if this is a fetch_all request based on MAX_FETCH_SIZE
    fetch_all = params.get("pageSize", DEFAULT_PAGE_SIZE) >= MAX_FETCH_SIZE
    
    if ctg_query:
        logger.info(f"Using direct CTG query: {ctg_query}")
        # Use direct query, ignore cond/intr but keep other filters
        results = await ctg_service.search_ctg(
            term=ctg_query,
            page_size=params["pageSize"],
            page_token=params.get("ctgPageToken"),
            fetch_all=fetch_all
        )
    else:
        # Use normal refined query with all filters
        results = await ctg_service.search_ctg(
            term=params["query"],
            cond=params.get("cond"),
            intr=params.get("intr"),
            other_term=params.get("other_term"),
            study_type=params.get("studyType"),
            phase=params.get("phase"),
            gender=ctg_sex_mapping.get(params.get("sex"), params.get("sex")) if params.get("sex") else None,
            ages=params.get("age"),
            sponsor=params.get("sponsor"),
            location=params.get("location"),
            status=params.get("status"),
            page_size=params["pageSize"],
            page_token=params.get("ctgPageToken"),
            fetch_all=fetch_all
        )
    
    logger.info(f"ClinicalTrials.gov search completed: {len(results.get('results', []))} results")
    return results

def _merge_and_paginate_results(results: dict, query: str,
                                page: int, page_size: int) -> dict:
    """
    Merge PM and CTG results → sort by BM25 → paginate,
    then populate abstracts for PMIDs included in the page using efetch.
    """
    logger.info("=== MERGE AND PAGINATE START ===")
    try:
        # ----- 0. Input separation --------------------------------------------------
        pm_results  = results.get("pm",  {}).get("results", [])
        ctg_results = results.get("ctg", {}).get("results", [])
        logger.info(f"Input results - PM: {len(pm_results)}, CTG: {len(ctg_results)}")

        # ----- 1. Create unified list -------------------------------------------
        unified_results = []

        # 1-A) PubMed - use all data already including rich metadata
        for item in pm_results:
            # Add classification information
            classification = ResultClassifier.classify_result(item)
            
            unified_item = {
                "type": "PM",
                "id": item.get("pmid"),
                "pmid": item.get("pmid"),
                "pmcid": item.get("pmcid"),
                "title": item.get("title", ""),
                "journal": item.get("journal", ""),
                "journal_abbrev": item.get("journal_abbrev", ""),
                "authors": item.get("authors", []),
                "pubDate": item.get("pubDate", ""),
                "pub_year": item.get("pub_year"),
                "abstract": item.get("abstract"),  # already includes structured abstract
                "doi": item.get("doi"),
                "pii": item.get("pii"),
                "mesh_headings": item.get("mesh_headings", []),
                "keywords": item.get("keywords", []),
                "chemicals": item.get("chemicals", []),
                "grants": item.get("grants", []),
                "ref_nctids": item.get("ref_nctids", []),
                "publication_types": item.get("publication_types", []),
                "language": item.get("language", []),
                "country": item.get("country"),
                "volume": item.get("volume"),
                "issue": item.get("issue"),
                "pagination": item.get("pagination"),
                "bm25_score": item.get("bm25_score"),
                # Add classification information
                "study_type": classification['study_type'],
                "phase": classification['phase'],
                "design_allocation": classification['design_allocation'],
                "observational_model": classification['observational_model']
            }
            unified_results.append(unified_item)

        # 1-B) ClinicalTrials.gov
        for item in ctg_results:
            # Add classification information
            classification = ResultClassifier.classify_result(item)
            
            unified_item = {
                "type": "CTG",
                "id": item.get("id"),
                "nctid": item.get("id"),
                "title": item.get("title", ""),
                "official_title": item.get("official_title", ""),
                "status": item.get("status", ""),
                "brief_summary": item.get("brief_summary", ""),
                "phase": item.get("phase", ""),
                "lead_sponsor": item.get("lead_sponsor", ""),
                "start_date": item.get("start_date"),
                "completion_date": item.get("completion_date"),
                "primary_completion_date": item.get("primary_completion_date"),
                "study_type": item.get("study_type", ""),
                "has_results": item.get("has_results", False),
                "enrollment": item.get("enrollment"),
                "enrollment_type": item.get("enrollment_type", ""),
                "countries": item.get("countries", []),
                "conditions": item.get("conditions", []),
                "keywords": item.get("keywords", []),
                "pmids": item.get("pmids", []),
                "primary_outcomes": item.get("primary_outcomes", []),
                "secondary_outcomes": item.get("secondary_outcomes", []),
                "intervention_names": item.get("intervention_names", []),
                "collaborators": item.get("collaborators", []),
                "structured_info": item.get("structured_info", {}),
                "bm25_score": item.get("bm25_score"),
                # Add classification information (using already normalized values)
                "study_type": classification['study_type'],
                "phase": classification['phase'],
                "design_allocation": classification['design_allocation'],
                "observational_model": classification['observational_model']
            }
            unified_results.append(unified_item)

        # ----- 2. Find MERGED pairs (bidirectional matching) -------------------------------------------
        pm_by_pmid   = {d["pmid"]: d for d in unified_results if d["type"] == "PM" and d["pmid"]}
        merged_items = []
        used_pmids, used_nctids = set(), set()

        for ctg_item in (d for d in unified_results if d["type"] == "CTG"):
            ref_pmids = ctg_item.get("pmids", [])
            # Check if CTG item references exactly one PMID
            if len(ref_pmids) == 1:
                ref_pmid = str(ref_pmids[0])
                if ref_pmid in pm_by_pmid:
                    pm_item = pm_by_pmid[ref_pmid]
                    pm_ref_nctids = pm_item.get("ref_nctids", [])
                    
                    # Check if PM item also references exactly one NCT ID and it matches current CTG item (bidirectional matching)
                    if len(pm_ref_nctids) == 1 and str(pm_ref_nctids[0]) == ctg_item["nctid"]:
                        score = pm_item.get("bm25_score") or ctg_item.get("bm25_score")
                        
                        # Classification information for MERGED item (prioritize CTG info, supplement with PM info)
                        merged_classification = {
                            "study_type": ctg_item.get("study_type", pm_item.get("study_type", "NA")),
                            "phase": ctg_item.get("phase", pm_item.get("phase", "NA")),
                            "design_allocation": ctg_item.get("design_allocation", pm_item.get("design_allocation", "NA")),
                            "observational_model": ctg_item.get("observational_model", pm_item.get("observational_model", "NA"))
                        }
                        
                        merged_items.append({
                            "type": "MERGED",
                            "id": f"{ref_pmid}|{ctg_item['nctid']}",  # Add unique ID
                            "pmid": ref_pmid,
                            "nctid": ctg_item["nctid"],
                            "bm25_score": score,
                            "pm_data": pm_item,
                            "ctg_data": ctg_item,
                            # Add classification information
                            "study_type": merged_classification["study_type"],
                            "phase": merged_classification["phase"],
                            "design_allocation": merged_classification["design_allocation"],
                            "observational_model": merged_classification["observational_model"]
                        })
                        used_pmids.add(ref_pmid)
                        used_nctids.add(ctg_item["nctid"])
                        logger.debug(f"Bidirectional match found: PMID {ref_pmid} <-> NCT {ctg_item['nctid']}")
                    else:
                        logger.debug(f"Unidirectional match rejected: CTG {ctg_item['nctid']} -> PM {ref_pmid}, but PM refs: {pm_ref_nctids}")

        # ----- 3. Remaining standalone results --------------------------------------------
        pm_only_items  = [d for d in unified_results
                          if d["type"] == "PM"  and d["pmid"]  not in used_pmids]
        ctg_only_items = [d for d in unified_results
                          if d["type"] == "CTG" and d["nctid"] not in used_nctids]

        final_results = merged_items + pm_only_items + ctg_only_items

        # MERGED bonus and None value handling
        merge_bonus = 0.3
        for item in final_results:
            # Set bm25_score to 0 if None
            if item.get("bm25_score") is None:
                item["bm25_score"] = 0.0
            
            if item.get("type") == "MERGED":
                item["bm25_score"] = item["bm25_score"] + merge_bonus

        # Final sorting (safe since all bm25_score are float)
        final_results.sort(
            key=lambda x: x.get("bm25_score", 0.0),
            reverse=True
        )

        # ----- 4. Sort by BM25 criteria ---------------------------------------
        # final_results.sort(key=lambda x: x.get("bm25_score") or float("-inf"), reverse=True)

        # ----- 5. Counts -----------------------------------------------------
        merged_count   = len(merged_items)
        pm_only_count  = len(pm_only_items)
        ctg_only_count = len(ctg_only_items)
        total_count    = len(final_results)

        # ----- 6. Page slice -------------------------------------------
        start_idx = (page - 1) * page_size
        end_idx   = start_idx + page_size
        page_results = final_results[start_idx:end_idx]
        total_pages  = (total_count + page_size - 1) // page_size

        # ----- 7. Abstract data already retrieved from PM search, no additional API calls needed -----
        # Since abstract data including all metadata was already retrieved from PM search,
        # no additional efetch calls needed, use existing data
        logger.info("Abstracts already included in initial PM search - no additional API calls needed")

        # ----- 8. Response object --------------------------------------------------
        result = {
            "results": page_results,
            "counts": {
                "total": total_count,
                "merged": merged_count,
                "pm_only": pm_only_count,
                "ctg_only": ctg_only_count
            },
            "total": total_count,
            "totalPages": total_pages
        }

        logger.info(f"Returning {len(page_results)} results (page {page}/{total_pages})")
        logger.info("=== MERGE AND PAGINATE END ===")
        return result

    except Exception as e:
        logger.error(f"Error in _merge_and_paginate_results: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "results": [],
            "counts": {"total": 0, "merged": 0, "pm_only": 0, "ctg_only": 0},
            "total": 0,
            "totalPages": 0
        }

def _get_full_merged_results_for_csv(results: dict, query: str) -> List[Dict]:
    """
    Generate full merged results for CSV logging using the same logic as _merge_and_paginate_results
    to ensure consistent ordering between CSV and frontend results.
    """
    try:
        # Use the same logic as _merge_and_paginate_results but without pagination
        pm_results = results.get("pm", {}).get("results", [])
        ctg_results = results.get("ctg", {}).get("results", [])
        
        # Create unified results with all necessary fields
        unified_results = []
        
        # Add PubMed results - includes rich metadata
        for item in pm_results:
            unified_results.append({
                "type": "PM",
                "id": item.get("pmid"),
                "pmid": item.get("pmid"),
                "pmcid": item.get("pmcid"),
                "title": item.get("title", ""),
                "journal": item.get("journal", ""),
                "journal_abbrev": item.get("journal_abbrev", ""),
                "authors": item.get("authors", []),
                "pubDate": item.get("pubDate", ""),
                "pub_year": item.get("pub_year"),
                "abstract": item.get("abstract"),  # already includes structured abstract
                "doi": item.get("doi"),
                "pii": item.get("pii"),
                "mesh_headings": item.get("mesh_headings", []),
                "keywords": item.get("keywords", []),
                "ref_nctids": item.get("ref_nctids", []),
                "bm25_score": item.get("bm25_score")
            })
        
        # Add CTG results
        for item in ctg_results:
            unified_results.append({
                "type": "CTG",
                "id": item.get("id"),
                "nctid": item.get("id"),
                "title": item.get("title", ""),
                "status": item.get("status", ""),
                "study_type": item.get("study_type", ""),
                "has_results": item.get("has_results", False),
                "enrollment": item.get("enrollment"),
                "enrollment_type": item.get("enrollment_type", ""),
                "countries": item.get("countries", []),
                "pmids": item.get("pmids", []),
                "bm25_score": item.get("bm25_score")
            })
        
        # Find MERGED pairs using the same logic
        pm_by_pmid = {d["pmid"]: d for d in unified_results if d["type"] == "PM" and d["pmid"]}
        merged_items = []
        used_pmids, used_nctids = set(), set()
        
        for ctg_item in (d for d in unified_results if d["type"] == "CTG"):
            ref_pmids = ctg_item.get("pmids", [])
            if len(ref_pmids) == 1:
                ref_pmid = str(ref_pmids[0])
                if ref_pmid in pm_by_pmid:
                    pm_item = pm_by_pmid[ref_pmid]
                    score = pm_item.get("bm25_score") or ctg_item.get("bm25_score")
                    merged_items.append({
                        "type": "MERGED",
                        "id": f"{ref_pmid}|{ctg_item['id']}",
                        "pmid": ref_pmid,
                        "nctid": ctg_item["id"],
                        "title": f"{pm_item['title']} / {ctg_item['title']}",
                        "bm25_score": score,
                        "journal": pm_item.get("journal", ""),
                        "status": ctg_item.get("status", ""),
                        "pmids": [ref_pmid]
                    })
                    used_pmids.add(ref_pmid)
                    used_nctids.add(ctg_item["id"])
        
        # Get remaining standalone results
        pm_only_items = [d for d in unified_results if d["type"] == "PM" and d["pmid"] not in used_pmids]
        ctg_only_items = [d for d in unified_results if d["type"] == "CTG" and d["nctid"] not in used_nctids]
        
        final_results = merged_items + pm_only_items + ctg_only_items
        
        # Apply MERGED bonus and handle None values (same as in _merge_and_paginate_results)
        merge_bonus = 0.3
        for item in final_results:
            # Set bm25_score to 0 if None
            if item.get("bm25_score") is None:
                item["bm25_score"] = 0.0
                
            if item.get("type") == "MERGED":
                item["bm25_score"] = item["bm25_score"] + merge_bonus
        
        # Final sort (same as in _merge_and_paginate_results)
        final_results.sort(
            key=lambda x: x.get("bm25_score", 0.0),
            reverse=True
        )
        
        return final_results
        
    except Exception as e:
        logger.error(f"Error in _get_full_merged_results_for_csv: {e}")
        return []

class FilterRequest(BaseModel):
    search_key: Optional[str] = None
    phase: Optional[List[str]] = None  # ['NA', 'EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4']
    study_type: Optional[List[str]] = None  # ['INTERVENTIONAL', 'OBSERVATIONAL', 'EXPANDED_ACCESS', 'NA']
    design_allocation: Optional[List[str]] = None  # ['RANDOMIZED', 'NON_RANDOMIZED', 'NA']
    observational_model: Optional[List[str]] = None  # ['COHORT', 'CASE_CONTROL', 'CASE_ONLY', 'CASE_CROSSOVER', 'ECOLOGIC_OR_COMMUNITY_STUDY', 'FAMILY_BASED', 'OTHER', 'NA']
    year_range: Optional[Dict[str, int]] = None  # {"from": 2020, "to": 2024}
    source_type: Optional[List[str]] = None  # ['PM', 'CTG']
    page: Optional[int] = 1
    page_size: Optional[int] = DEFAULT_PAGE_SIZE

@router.post("/filter")
async def filter_results(request: Request):
    """Apply filtering to cached search results"""
    try:
        # Log original request data
        raw_body = await request.body()
        logger.info(f"Raw filter request body: {raw_body}")
        
        # Attempt JSON parsing
        import json
        try:
            body_data = json.loads(raw_body)
            logger.info(f"Parsed filter request data: {body_data}")
        except Exception as parse_error:
            logger.error(f"Failed to parse request body: {parse_error}")
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        
        # Attempt Pydantic model conversion
        try:
            body = FilterRequest(**body_data)
            logger.info(f"Filter request validated successfully: {body}")
        except Exception as validation_error:
            logger.error(f"Validation error: {validation_error}")
            raise HTTPException(status_code=422, detail=f"Validation failed: {validation_error}")
        
        logger.info(f"Filter request received with search_key: {body.search_key}")
        
        # Handle case where search_key is None
        if not body.search_key:
            logger.error("No search_key provided in filter request")
            raise HTTPException(status_code=400, detail="search_key is required for filtering")
        
        # Get original results from cache
        cached_data = get_cached_results(body.search_key)
        
        if not cached_data:
            logger.warning("Search results not found in cache. This may be due to cache expiration or unavailability.")
            # Check cache status
            from services.cache_service import get_cache_info
            cache_info = get_cache_info()
            cache_status = "Redis available" if cache_info["redis_available"] else f"Memory cache only ({cache_info['memory_cache_size']} items)"
            
            raise HTTPException(
                status_code=404, 
                detail=f"Search results not found or expired. Cache status: {cache_status}. Please perform a new search to enable filtering."
            )
        
        # Get all results
        all_results = cached_data.get('all_results', [])
        
        # Apply source type filter
        if body.source_type:
            all_results = [r for r in all_results if r['type'] in body.source_type]
        
        # Apply filter stats based filtering
        from services.filter_stats_service import apply_filter_stats_to_results
        
        filter_criteria = {}
        if body.phase:
            filter_criteria['phase'] = body.phase
        if body.study_type:
            filter_criteria['study_type'] = body.study_type
        if body.design_allocation:
            filter_criteria['design_allocation'] = body.design_allocation
        if body.observational_model:
            filter_criteria['observational_model'] = body.observational_model
        if body.year_range:
            filter_criteria['year_range'] = body.year_range
        
        filtered_results = apply_filter_stats_to_results(all_results, filter_criteria)
        
        # Re-perform merge on filtered results
        # Separate filtered results into PM and CTG
        filtered_pm = [r for r in filtered_results if r['type'] == 'PM']
        filtered_ctg = [r for r in filtered_results if r['type'] == 'CTG']
        
        logger.info(f"After filtering - PM: {len(filtered_pm)}, CTG: {len(filtered_ctg)}")
        
        # Create temporary result structure with filtered results
        temp_results = {
            "pm": {"results": filtered_pm},
            "ctg": {"results": filtered_ctg}
        }
        
        # Perform merge and pagination
        merged_result = _merge_and_paginate_results(
            temp_results, 
            "", # query is not used in filtering
            body.page, 
            body.page_size
        )
        
        logger.info(f"Filtered merge result: total={merged_result['total']}, counts={merged_result['counts']}")
        
        # Extract data from merge result
        paged_results = merged_result["results"]
        total_count = merged_result["total"]
        total_pages = merged_result["totalPages"]
        result_counts = merged_result["counts"]
        
        # Recalculate statistics for filtered results
        from services.filter_stats_service import calculate_filter_stats
        filtered_stats = calculate_filter_stats(filtered_pm, filtered_ctg)
        
        # Reconstruct results
        response = {
            "results": paged_results,
            "total": total_count,
            "page": body.page,
            "page_size": body.page_size,
            "totalPages": total_pages,
            "counts": result_counts,  # Use merged result counts
            "filters_applied": {
                "phase": body.phase,
                "study_type": body.study_type,
                "design_allocation": body.design_allocation,
                "observational_model": body.observational_model,
                "year_range": body.year_range,
                "source_type": body.source_type
            },
            "filter_stats": filtered_stats  # Statistics of filtered results
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Filter error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Filter failed: {str(e)}")