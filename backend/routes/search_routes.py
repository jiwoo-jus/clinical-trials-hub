import asyncio
import csv
import hashlib
import json
import logging
import os
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import DEFAULT_PAGE_SIZE, MAX_FETCH_SIZE
from services import ctg_service, pm_service
from services.cache_service import (
    cache_search_results,
    generate_search_key,
    get_cache_info,
    get_cached_results,
)
from services.ctg_filter_builder import CTGFilterBuilder
from services.filter_stats_service import calculate_filter_stats
from services.pubmed_filter_builder import PubMedFilterBuilder
from services.query_service import get_query_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Directory for saving CSV logs
LOG_DIR = "./logs/search_results"
os.makedirs(LOG_DIR, exist_ok=True)

# Define the request body schema - supports initial filtering
class SearchRequest(BaseModel):
    cond: Optional[str] = None
    intr: Optional[str] = None
    other_term: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    user_query: Optional[str] = None
    pubmed_query: Optional[str] = None
    ctg_query: Optional[str] = None
    isRefined: Optional[bool] = False
    page: Optional[int] = 1
    pageSize: Optional[int] = DEFAULT_PAGE_SIZE
    sources: Optional[List[str]] = ["PM", "CTG"]
    ctgPageToken: Optional[str] = None
    refinedQuery: Optional[dict] = None
    # Post-filter parameters for initial search filtering
    article_type: Optional[List[str]] = []
    species: Optional[List[str]] = []
    age: Optional[List[str]] = []
    publication_date: Optional[dict] = None
    # PubMed-only filters
    pmc_open_access: Optional[bool] = False
    # CTG-only filters
    ctg_has_results: Optional[bool] = False
    ctg_status: Optional[List[str]] = []

class PageRequest(BaseModel):
    search_key: str
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

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
            ["# Condition Query (PubMed)", search_params.get("condition_query", "")]
        ]
        
        # Prepare CSV data
        csv_data = []
        for item in final_results:
            row = {
                "source": item.get("type", ""),
                "id": item.get("id", ""),
                "title": item.get("title", ""),
                "bm25_score": str(item.get("bm25_score", "")),
                "pmids": ",".join(item.get("pmids", [])) if item.get("type") == "CTG" else item.get("pmid", "")
            }
            csv_data.append(row)
        
        # Write to CSV
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = ["source", "id", "title", "bm25_score", "pmids"]
            # Write metadata as commented, padded rows
            for meta_row in metadata:
                padded = meta_row + [""] * (len(header) - len(meta_row))
                writer.writerow(padded)
            # Write actual header and data
            writer.writerow(header)
            for row in csv_data:
                writer.writerow([
                    row["source"], row["id"], row["title"],
                    row["bm25_score"], row["pmids"]
                ])
        
        logger.info(f"Saved search results to {filename}")
        
    except Exception as e:
        logger.error(f"Failed to write CSV: {e}")

@router.post("")
async def search(request: Request, body: SearchRequest):
    try:
        data = body.model_dump()
        logger.info("=== SEARCH REQUEST START ===")
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
        
        # Always build filter criteria (even if empty)
        publication_date = data.get("publication_date")
        filter_criteria = {
            "article_type": data.get("article_type", []),
            "species": data.get("species", []),
            "age": data.get("age", []),
            "publication_date": publication_date or {},
            "pmc_open_access": data.get("pmc_open_access", False)
        }
        
        # Check if user explicitly provided filters
        has_user_filters = any([
            data.get("article_type"),
            data.get("species"),
            data.get("age"),
            publication_date and publication_date.get("type") if isinstance(publication_date, dict) else False
        ])
        
        logger.info(f"🎯 Filter criteria: {filter_criteria} (user provided: {has_user_filters})")
        
        #generate_dynamic_queries = False
        generate_dynamic_queries = not data.get("isRefined") 
        dynamic_queries = {}
        if generate_dynamic_queries:
            logger.info("Starting query generation...")
            dynamic_queries = await _create_dynamic_queries(refined_query)
            logger.info(f"dynamic query result: {dynamic_queries}")
        
        # Execute searches with filtering always applied
        if "PM" in sources_to_search:
            logger.info("Searching PubMed...")
            # Always apply filters to PubMed query (includes fixed PMC Open Access filter)
            base_query = search_params.get("pubmed_query") or search_params.get("query")
            filtered_query = PubMedFilterBuilder.append_filters_to_query(base_query, filter_criteria)
            logger.info(f"🔍 PubMed query with filters: {filtered_query}")
            
            # Create modified search params with filtered query
            filtered_params = search_params.copy()
            filtered_params["query"] = filtered_query
            filtered_params["pubmed_query"] = None  # Use query field instead
            results["pm"] = await _search_pubmed(filtered_params)
            is_initial_search = True
            logger.info(f"PubMed search completed. Results: {len(results['pm'].get('results', []))} items")
        
        if "CTG" in sources_to_search:
            logger.info("Searching ClinicalTrials.gov...")
            # Always build and apply CTG filters (exclude PubMed-only filters)
            filter_criteria_ctg = _build_ctg_filter_criteria(data)
            logger.info(f"🎯 CTG filter criteria (before building): {filter_criteria_ctg}")
            
            area_filter = CTGFilterBuilder.build_combined_filter(filter_criteria_ctg)
            logger.info(f"🔍 CTG AREA filter string: '{area_filter}'")
            
            # Build status parameter for API
            status_param = CTGFilterBuilder.build_status_param(filter_criteria_ctg)
            logger.info(f"📊 CTG Status filter: '{status_param}'")
            
            if not area_filter:
                logger.warning("⚠️ CTG AREA filter is empty! No filters will be applied to CTG search.")
            
            # Add filters to search params (date filter is now in area_filter)
            filtered_ctg_params = search_params.copy()
            filtered_ctg_params["area_filter"] = area_filter
            filtered_ctg_params["overall_status"] = status_param
            filtered_ctg_params["last_update_post_date"] = None  # No longer used separately
            
            logger.info(f"📤 Calling CTG service with area_filter: '{area_filter}', status: '{status_param}'")
            results["ctg"] = await _search_clinicaltrials(filtered_ctg_params)
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
        
        # Prepare results with extracted metadata (keep raw lists separately)
        pm_results_with_meta: List[Dict] = []
        ctg_results_with_meta: List[Dict] = []
        
        if "PM" in data.get("sources", ["PM", "CTG"]):
            pm_results = results.get("pm", {}).get("results", [])
            for r in pm_results:
                enhanced_result = {
                    **r,
                    'type': 'PM'
                }
                pm_results_with_meta.append(enhanced_result)
                
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
                        'start_date': r.get('start_date'),
                        'completion_date': r.get('completion_date')
                    }
                }
                ctg_results_with_meta.append(enhanced_result)
                
        # Calculate unified filter stats
        filter_stats = calculate_filter_stats(pm_results_with_meta, ctg_results_with_meta)

        # Build full merged (BM25-sorted) list for pagination instead of simple PM-then-CTG ordering
        total_items = len(pm_results_with_meta) + len(ctg_results_with_meta)
        if total_items > 0:
            # Build a unified results dict similar to search merge input
            unified_results_for_merge = {
                "pm": {"results": pm_results_with_meta},
                "ctg": {"results": ctg_results_with_meta}
            }
            full_merged = _merge_and_paginate_results(
                unified_results_for_merge,
                refined_query.get("combined_query", ""),
                page=1,
                page_size=total_items
            )
            merged_all_results = full_merged.get("results", [])
        else:
            merged_all_results = []

        search_key = generate_search_key(data)

        # Build appliedQueries with actual executed queries
        applied_queries = {
            "pubmed": results.get("pm", {}).get("applied_query", ""),
            "clinicaltrials": results.get("ctg", {}).get("applied_query", "")
        }

        # Store both original and filtered queries for proper filter re-application
        cache_data = {
            "all_results": merged_all_results,            # merged & interleaved list used for pagination
            "raw_pm_results": pm_results_with_meta,       # optional raw PM list
            "raw_ctg_results": ctg_results_with_meta,     # optional raw CTG list
            "search_params": search_params,
            "original_request": data,
            "timestamp": datetime.now().isoformat(),
            "filter_stats": filter_stats,
            "appliedQueries": applied_queries,
            "baseQueries": {
                "pubmed": search_params.get("pubmed_query") or search_params.get("query", ""),
                "clinicaltrials": ""  # CTG uses cond/intr/term params, not a query string
            }
        }
        cache_search_results(search_key, cache_data)
        logger.info(f"✅ Cached search results with key: {search_key}")
        
        # Add cache status information
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
        logger.info(f"CTG filters in stats: {filter_stats.get('ctg_filters', {})}")

        logger.info("=== SEARCH REQUEST END ===")
        end = time.time()
        logger.info(f"FULL SEARCH TIME: {end-start:.3f}s")
        
        return response
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Search failed")
    
@router.post("/patient")
async def patient_search(request: Request, body: SearchRequest):
    try:
        data = body.model_dump()
        logger.info("=== PATIENT SEARCH REQUEST START ===")
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
            desc += f"User Search: '{default.get('query')}'"
        for k, v in data.items():
            if v and k in flist:
                desc += f'/n{k}: {v}'
        r["description"] = desc
        search_results["final_results"].append(r)

        # Generate additional query results asynchronously
        tasks = []
        for q in queries.get("expanded_queries"):
            tasks.append(_get_query_results(q["filters"]))

        results_list = await asyncio.gather(*tasks)

        for q, res in zip(queries.get("expanded_queries"), results_list):
            res["name"] = q.get("type", "")
            res["description"] = q.get("description", "")
            res["modified"] = q.get("modified", [])
            search_results["final_results"].append(res)
 
        return search_results
 
        
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


@router.post("/paging")
async def search_page(request: Request, body: PageRequest):
    """Handle pagination for regular search results using cached data"""
    try:
        data = body.model_dump()
        logger.info("="*80)
        logger.info("📄 SEARCH PAGINATION REQUEST")
        logger.info(f"  search_key: {data['search_key']}")
        logger.info(f"  page: {data['page']}")
        logger.info(f"  page_size: {data['page_size']}")

        # Get cached results
        cached_data = get_cached_results(data["search_key"])
        
        if not cached_data:
            logger.error(f"❌ No cached results found for search_key: {data['search_key']}")
            # Try to get cache info
            cache_info = get_cache_info()
            logger.error(f"  Cache info: {cache_info}")
            raise HTTPException(
                status_code=404,
                detail="Search results not found or expired. Please perform a new search."
            )

        all_results = cached_data.get("all_results", [])
        filter_stats = cached_data.get("filter_stats", {})
        applied_queries = cached_data.get("appliedQueries", {})
        
        logger.info(f"✅ Found cached results. Total: {len(all_results)}")

        # Calculate pagination
        page_size = data["page_size"]
        page = data["page"]
        total_results = len(all_results)
        total_pages = (total_results + page_size - 1) // page_size
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_results = all_results[start_idx:end_idx]
        
        logger.info(f"  Returning results {start_idx+1} to {min(end_idx, total_results)} of {total_results}")

        # Return paginated response matching search API structure
        response = {
            "search_key": data["search_key"],
            "results": page_results,
            "counts": {
                "total": total_results,
                "merged": sum(1 for r in all_results if r.get("type") == "MERGED"),
                "pm_only": sum(1 for r in all_results if r.get("type") == "PM"),
                "ctg_only": sum(1 for r in all_results if r.get("type") == "CTG")
            },
            "total": total_results,
            "page": page,
            "pageSize": page_size,
            "totalPages": total_pages,
            "filter_stats": filter_stats,
            "appliedQueries": applied_queries
        }
        
        logger.info("✅ Pagination response prepared")
        logger.info("="*80)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Search pagination error: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}


class PublicationDateFilter(BaseModel):
    type: Optional[str] = None
    from_year: Optional[int] = None
    to_year: Optional[int] = None

class FilterRequest(BaseModel):
    search_key: Optional[str] = None
    source_type: Optional[List[str]] = None
    article_type: Optional[List[str]] = None
    species: Optional[List[str]] = None
    age: Optional[List[str]] = None
    publication_date: Optional[Union[PublicationDateFilter, Dict[str, Any]]] = None
    page: Optional[int] = 1
    page_size: Optional[int] = DEFAULT_PAGE_SIZE
    pmc_open_access: Optional[bool] = True
    ctg_has_results: Optional[bool] = False
    ctg_status: Optional[List[str]] = []

@router.post("/filter")
async def filter_results(request: Request):
    """Apply filtering by re-querying with filter syntax and caching filtered results"""
    try:
        # Parse request
        raw_body = await request.body()
        logger.info("="*80)
        logger.info("🔍 FILTER REQUEST START")
        logger.info(f"Raw body: {raw_body}")
        
        try:
            body_data = json.loads(raw_body)
            logger.info(f"Parsed data: {json.dumps(body_data, indent=2)}")
        except Exception as parse_error:
            logger.error(f"Failed to parse request body: {parse_error}")
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        
        # Validate with Pydantic
        try:
            body = FilterRequest(**body_data)
            logger.info(f"✅ Filter request validated")
        except Exception as validation_error:
            logger.error(f"Validation error: {validation_error}")
            raise HTTPException(status_code=422, detail=f"Validation failed: {validation_error}")
        
        # Check search_key
        if not body.search_key:
            logger.error("No search_key provided")
            raise HTTPException(status_code=400, detail="search_key is required")
        
        # Reset page to 1 when filters change
        if body.page is None or body.page < 1:
            body.page = 1
        
        logger.info(f"📋 Filter parameters:")
        logger.info(f"  search_key: {body.search_key}")
        logger.info(f"  source_type: {body.source_type}")
        logger.info(f"  article_type: {body.article_type}")
        logger.info(f"  age: {body.age}")
        logger.info(f"  species: {body.species}")
        logger.info(f"  publication_date: {body.publication_date}")
        logger.info(f"  page: {body.page} (reset to 1 on filter change)")
        
        # Get cached data
        cached_data = get_cached_results(body.search_key)
        
        if not cached_data:
            logger.warning(f"Search results not found in cache for key: {body.search_key}")
            raise HTTPException(
                status_code=404, 
                detail="Search results not found or expired. Please perform a new search."
            )
        
        # Validate cache structure
        required_fields = ['all_results', 'search_params', 'original_request']
        missing_fields = [field for field in required_fields if field not in cached_data]
        if missing_fields:
            logger.error(f"❌ Cache data missing fields: {missing_fields}")
            raise HTTPException(
                status_code=500,
                detail=f"Cache data corrupted. Please perform a new search."
            )
        
        logger.info(f"✅ Cache data validated")
        
        # Get BASE queries (without filters) for proper filter re-application
        base_queries = cached_data.get('baseQueries', {})
        pubmed_base_query = base_queries.get('pubmed', '')
        
        # Fallback to appliedQueries if baseQueries not available (legacy cache)
        if not pubmed_base_query:
            original_queries = cached_data.get('appliedQueries', {})
            pubmed_base_query = original_queries.get('pubmed', '')
        
        logger.info(f"📝 Base queries (without filters):")
        logger.info(f"  PubMed base: {pubmed_base_query}")
        
        # Process publication_date
        pub_date_filter = {}
        if body.publication_date:
            if isinstance(body.publication_date, dict):
                pub_date_filter = {
                    'type': body.publication_date.get('type'),
                    'from_year': body.publication_date.get('from_year') or body.publication_date.get('from'),
                    'to_year': body.publication_date.get('to_year') or body.publication_date.get('to')
                }
            else:
                pub_date_filter = {
                    'type': body.publication_date.type,
                    'from_year': body.publication_date.from_year,
                    'to_year': body.publication_date.to_year
                }
        
        # Build filter criteria
        filter_criteria = {
            'article_type': body.article_type or [],
            'species': body.species or [],
            'age': body.age or [],
            'publication_date': pub_date_filter,
            'pmc_open_access': body.pmc_open_access if body.pmc_open_access is not None else True,
            'ctg_has_results': body.ctg_has_results or False,
            'ctg_status': body.ctg_status or []
        }
        
        logger.info(f"🎯 Filter criteria: {json.dumps(filter_criteria, indent=2)}")
        
        # Build cache key with ALL filter information (including CTG-only filters)
        filter_dict = {
            'article_type': sorted(filter_criteria['article_type']),
            'species': sorted(filter_criteria['species']),
            'age': sorted(filter_criteria['age']),
            'publication_date': pub_date_filter,
            'pmc_open_access': filter_criteria['pmc_open_access'],
            'ctg_has_results': filter_criteria['ctg_has_results'],
            'ctg_status': sorted(filter_criteria['ctg_status']),
            'source_type': sorted(body.source_type) if body.source_type else ['PM', 'CTG']
        }
        cache_input = json.dumps(filter_dict, sort_keys=True)
        filter_cache_key = f"{body.search_key}:filter:{hashlib.md5(cache_input.encode()).hexdigest()}"
        
        logger.info(f"🔑 Filter cache key: {filter_cache_key}")
        
        # Check if filtered results are cached
        cached_filtered = get_cached_results(filter_cache_key)
        
        if cached_filtered and 'all_filtered_results' in cached_filtered:
            logger.info(f"✅ Using cached filtered results (total: {len(cached_filtered['all_filtered_results'])})")
            all_filtered_results = cached_filtered['all_filtered_results']
            filtered_stats = cached_filtered.get('filter_stats', {})
            filtered_queries = cached_filtered.get('appliedQueries', {})
        else:
            logger.info(f"🔄 Computing filtered results (will cache for future use)")
            
            # Determine sources
            source_types = body.source_type if body.source_type else ['PM', 'CTG']
            logger.info(f"🎯 Source types to search: {source_types}")
            
            filtered_results = {}
            
            # Search PubMed if requested
            if 'PM' in source_types and pubmed_base_query:
                logger.info(f"🔍 Searching PubMed with filters")
                filtered_pm_query = PubMedFilterBuilder.append_filters_to_query(pubmed_base_query, filter_criteria)
                logger.info(f"  Base query (no filters): {pubmed_base_query}")
                logger.info(f"  Filtered query: {filtered_pm_query}")
                
                pm_results = await pm_service.search_pm(
                    combined_query=filtered_pm_query,
                    condition_query=None,
                    page=1,
                    page_size=MAX_FETCH_SIZE
                )
                
                if pm_results and pm_results.get("results"):
                    reranked = pm_service.rerank_pm_results_with_bm25(
                        filtered_pm_query,
                        pm_results["results"]
                    )
                    pm_results["results"] = reranked
                
                filtered_results["pm"] = pm_results
                logger.info(f"✅ PubMed results: {len(pm_results.get('results', []))}")
            else:
                filtered_results["pm"] = {"results": [], "total": 0}
                logger.info(f"⏭️  PubMed skipped (source not requested or no query)")
            
            # Search CTG if requested
            if 'CTG' in source_types:
                logger.info(f"🔍 Searching ClinicalTrials.gov with filters")
                
                # Extract original query params
                search_params = cached_data.get('search_params', {})
                original_request = cached_data.get('original_request', {})
                
                original_cond = search_params.get('cond')
                original_intr = search_params.get('intr')
                original_other_term = search_params.get('other_term')
                
                # Use combined query as term if other_term is empty
                original_query = search_params.get('query') or original_request.get('refinedQuery', {}).get('combined_query')
                if original_query and not original_other_term:
                    original_other_term = original_query
                
                # Clean None strings
                if original_cond in ['None', '', None]:
                    original_cond = None
                if original_intr in ['None', '', None]:
                    original_intr = None
                if original_other_term in ['None', '', None]:
                    original_other_term = None
                
                logger.info(f"📋 CTG query params:")
                logger.info(f"  cond: {original_cond}")
                logger.info(f"  intr: {original_intr}")
                logger.info(f"  term: {original_other_term}")
                
                # Build CTG-applicable filters (exclude PubMed-only)
                filter_criteria_ctg = _build_ctg_filter_criteria_from_full(filter_criteria)
                area_filter = CTGFilterBuilder.build_combined_filter(filter_criteria_ctg)
                status_param = CTGFilterBuilder.build_status_param(filter_criteria_ctg)
                
                logger.info(f"🎯 CTG-applicable filters: {filter_criteria_ctg}")
                logger.info(f"📐 CTG AREA filter: {area_filter}")
                logger.info(f"📊 CTG Status filter: {status_param}")
                
                # Call CTG API
                logger.info(f"🚀 Calling CTG API with AREA filter: {area_filter}, Status: {status_param}")
                ctg_results = await ctg_service.search_ctg(
                    cond=original_cond,
                    intr=original_intr,
                    term=original_other_term,
                    area_filter=area_filter,
                    last_update_post_date=None,
                    overall_status=status_param,
                    fetch_all=True
                )
                
                filtered_results["ctg"] = ctg_results
                logger.info(f"✅ CTG results: {len(ctg_results.get('results', []))}")
            else:
                filtered_results["ctg"] = {"results": [], "total": 0}
                logger.info(f"⏭️  CTG skipped (source not requested)")
            
            # Log final counts
            pm_count = len(filtered_results.get("pm", {}).get("results", []))
            ctg_count = len(filtered_results.get("ctg", {}).get("results", []))
            logger.info(f"📊 Filtered counts before merge: PM={pm_count}, CTG={ctg_count}")
            
            # Merge all results (preserving BM25 order)
            merged_all = _merge_and_paginate_results(
                filtered_results,
                "",
                page=1,
                page_size=pm_count + ctg_count  # Get all results
            )
            
            all_filtered_results = merged_all.get("results", [])
            logger.info(f"📊 Total merged filtered results: {len(all_filtered_results)}")
            
            # Recalculate statistics
            filtered_pm = filtered_results.get("pm", {}).get("results", [])
            filtered_ctg = filtered_results.get("ctg", {}).get("results", [])
            filtered_stats = calculate_filter_stats(filtered_pm, filtered_ctg)
            
            # Build filtered queries for display
            filtered_queries = _build_filtered_queries_display(
                body.source_type or ['PM', 'CTG'],
                pubmed_base_query,
                filter_criteria,
                cached_data,
                filtered_results
            )
            
            # Cache ALL filtered results with stats and queries
            cache_data_filtered = {
                'all_filtered_results': all_filtered_results,
                'filter_criteria': filter_criteria,
                'filter_stats': filtered_stats,
                'appliedQueries': filtered_queries,
                'timestamp': datetime.now().isoformat()
            }
            cache_search_results(filter_cache_key, cache_data_filtered)
            logger.info(f"💾 Cached {len(all_filtered_results)} filtered results with key: {filter_cache_key}")
        
        # Paginate from cached results
        total_results = len(all_filtered_results)
        total_pages = (total_results + body.page_size - 1) // body.page_size if total_results > 0 else 1
        
        start_idx = (body.page - 1) * body.page_size
        end_idx = start_idx + body.page_size
        page_results = all_filtered_results[start_idx:end_idx]
        
        logger.info(f"📄 Paginating: page {body.page}/{total_pages}, showing {len(page_results)} results")
        
        response = {
            "results": page_results,
            "total": total_results,
            "page": body.page,
            "page_size": body.page_size,
            "totalPages": total_pages,
            "counts": {
                "total": total_results,
                "merged": sum(1 for r in all_filtered_results if r.get("type") == "MERGED"),
                "pm_only": sum(1 for r in all_filtered_results if r.get("type") == "PM"),
                "ctg_only": sum(1 for r in all_filtered_results if r.get("type") == "CTG")
            },
            "filters_applied": filter_criteria,
            "filter_stats": filtered_stats,
            "appliedQueries": filtered_queries,
            "filter_cache_key": filter_cache_key  # Return this for future pagination
        }
        
        logger.info(f"✅ Filter response: {total_results} total results, {total_pages} pages")
        logger.info(f"📋 Applied queries: {filtered_queries}")
        logger.info("="*80)
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Filter error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Filter failed: {str(e)}")


# ============================================================================
# Helper Functions
# ============================================================================

def _build_ctg_filter_criteria(data: dict) -> dict:
    """
    Build CTG-applicable filter criteria by excluding PubMed-only filters.
    PubMed-only filters: meta_analysis, review, systematic_review, other_animals
    Includes publication_date for AREA filter.
    Includes CTG-only filters: ctg_has_results, ctg_status
    """
    article_types = data.get("article_type", [])
    species = data.get("species", [])
    
    # Remove PubMed-only article types
    ctg_article_types = [
        at for at in article_types
        if at not in ['meta_analysis', 'review', 'systematic_review']
    ]
    
    # Remove PubMed-only species
    ctg_species = [
        sp for sp in species
        if sp != 'other_animals'
    ]
    
    return {
        "article_type": ctg_article_types,
        "species": ctg_species,  # Will be empty list, but kept for consistency
        "age": data.get("age", []),
        "publication_date": data.get("publication_date"),
        "ctg_has_results": data.get("ctg_has_results", False),
        "ctg_status": data.get("ctg_status", [])
    }

def _build_ctg_filter_criteria_from_full(filter_criteria: dict) -> dict:
    """
    Build CTG-applicable filter criteria from full filter criteria.
    Includes publication_date, ctg_has_results, and ctg_status for CTG-specific filters.
    """
    article_types = filter_criteria.get("article_type", [])
    species = filter_criteria.get("species", [])
    
    # Remove PubMed-only article types
    ctg_article_types = [
        at for at in article_types
        if at not in ['meta_analysis', 'review', 'systematic_review']
    ]
    
    # Remove PubMed-only species
    ctg_species = [
        sp for sp in species
        if sp != 'other_animals'
    ]
    
    return {
        "article_type": ctg_article_types,
        "species": ctg_species,
        "age": filter_criteria.get("age", []),
        "publication_date": filter_criteria.get("publication_date"),
        "ctg_has_results": filter_criteria.get("ctg_has_results", False),
        "ctg_status": filter_criteria.get("ctg_status", [])
    }

def _build_filtered_queries_display(
    source_types: List[str],
    pubmed_query: str,
    filter_criteria: dict,
    cached_data: dict,
    filtered_results: dict
) -> dict:
    """Build filtered queries for display in response"""
    filtered_queries = {}
    
    # PubMed query
    if 'PM' in source_types:
        if pubmed_query:
            filtered_queries['pubmed'] = PubMedFilterBuilder.append_filters_to_query(pubmed_query, filter_criteria)
        else:
            filtered_queries['pubmed'] = "No PubMed query available"
    
    # CTG query
    if 'CTG' in source_types:
        search_params = cached_data.get('search_params', {})
        original_cond = search_params.get('cond')
        original_intr = search_params.get('intr')
        original_other_term = search_params.get('other_term')
        
        # Use combined query if other_term is empty
        original_query = search_params.get('query')
        if original_query and not original_other_term:
            original_other_term = original_query
        
        # Clean None strings
        if original_cond in ['None', '', None]:
            original_cond = None
        if original_intr in ['None', '', None]:
            original_intr = None
        if original_other_term in ['None', '', None]:
            original_other_term = None
        
        # Build CTG query display
        ctg_query_parts = []
        if original_cond:
            ctg_query_parts.append(f"Condition: {original_cond}")
        if original_intr:
            ctg_query_parts.append(f"Intervention: {original_intr}")
        if original_other_term:
            ctg_query_parts.append(f"Other terms: {original_other_term}")
        
        # Add filter information (CTG-applicable only)
        filter_criteria_ctg = _build_ctg_filter_criteria_from_full(filter_criteria)
        area_filter = CTGFilterBuilder.build_combined_filter(filter_criteria_ctg)
        if area_filter:
            ctg_query_parts.append(f"AREA Filters: {area_filter}")
        
        # Add has_results filter if present
        has_results = filter_criteria_ctg.get('ctg_has_results', False)
        if has_results:
            ctg_query_parts.append(f"Has Results: true")
        
        # Add status filter if present
        status_param = CTGFilterBuilder.build_status_param(filter_criteria_ctg)
        if status_param:
            ctg_query_parts.append(f"Status: {status_param}")
        
        filtered_queries['clinicaltrials'] = ' | '.join(ctg_query_parts) if ctg_query_parts else 'All studies'
    
    return filtered_queries


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
    sources_to_search = ["CTG"]

    if "CTG" in sources_to_search:
        logger.info("Searching ClinicalTrials.gov...")
        results["ctg"] = await ctg_service.get_patient_results(data)
        logger.info(f"CTG search completed. Results: {len(results['ctg'].get('results', []))} items")
    
    merged_results = _merge_and_paginate_results(
        results, 
        data.get("user_query", ""),
        page=data.get("page", 1),
        page_size=data.get("pageSize", DEFAULT_PAGE_SIZE)
    )

    all_results = []
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
                    'start_date': r.get('start_date'),
                    'completion_date': r.get('completion_date')
                }
            }
            ctg_results_with_meta.append(enhanced_result)
            all_results.append(enhanced_result)
            
    filter_stats = calculate_filter_stats([], ctg_results_with_meta)

    search_key = generate_search_key(data)
    cache_data = {
        "all_results": all_results,
        "search_params": data,
        "timestamp": datetime.now().isoformat(),
        "filter_stats": filter_stats
    }
    cache_search_results(search_key, cache_data)

    cache_info = get_cache_info()
    response = {
        "search_key": search_key,
        "refinedQuery": data,
        "appliedQueries": {
            "pubmed": "",
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
    """Build unified search parameters"""
    page_size = MAX_FETCH_SIZE if fetch_all else data.get("pageSize", DEFAULT_PAGE_SIZE)
    
    pubmed_query = data.get("pubmed_query")
    ctg_query = data.get("ctg_query")
    
    # Clean None strings
    cond = refined_query.get("cond")
    intr = refined_query.get("intr")
    other_term = refined_query.get("other_term", "")
    
    if cond in ["", "None", None]:
        cond = None
    if intr in ["", "None", None]:
        intr = None
    if other_term in ["", "None", None]:
        other_term = None
    
    params = {
        "pubmed_query": pubmed_query,
        "ctg_query": ctg_query,
        "query": refined_query.get("combined_query", ""),
        "cond": cond,
        "intr": intr,
        "other_term": other_term,
        "page": 1 if fetch_all else data.get("page", 1),
        "pageSize": page_size,
        "ctgPageToken": data.get("ctgPageToken")
    }
    
    logger.info(f"Built search parameters: {params}")
    return params

async def _search_pubmed(params: dict) -> dict:
    logger.info("Starting PubMed search...")
    
    pubmed_query = params.get("pubmed_query")
    if pubmed_query:
        logger.info(f"Using direct PubMed query: {pubmed_query}")
        results = await pm_service.search_pm(
            combined_query=pubmed_query,
            condition_query=None,
            page=params["page"],
            page_size=params["pageSize"]
        )
    else:
        # Note: condition_query is now always applied as fixed filter in PubMedFilterBuilder
        results = await pm_service.search_pm(
            combined_query=params["query"],
            condition_query=None,
            page=params["page"],
            page_size=params["pageSize"]
        )
    
    if not results or not results.get("results"):
        logger.warning("No PubMed results found")
        query_used = pubmed_query if pubmed_query else params["query"]
        return {
            "results": [], 
            "total": 0, 
            "query": query_used,
            "applied_query": query_used
        }
    
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
    
    if "applied_query" not in results:
        results["applied_query"] = query_for_ranking
    
    logger.info(f"PubMed search completed: {len(results['results'])} results")
    return results

async def _search_clinicaltrials(params: dict) -> dict:
    """Search ClinicalTrials.gov with optional filtering"""
    logger.info("Starting ClinicalTrials.gov search...")
    
    ctg_query = params.get("ctg_query")
    area_filter = params.get("area_filter")
    overall_status = params.get("overall_status")
    last_update_post_date = params.get("last_update_post_date")
    fetch_all = params.get("pageSize", DEFAULT_PAGE_SIZE) >= MAX_FETCH_SIZE
    
    if ctg_query:
        logger.info(f"Using direct CTG query: {ctg_query}")
        results = await ctg_service.search_ctg(
            term=ctg_query,
            page_size=params["pageSize"],
            page_token=params.get("ctgPageToken"),
            fetch_all=fetch_all,
            area_filter=area_filter,
            overall_status=overall_status,
            last_update_post_date=last_update_post_date
        )
    else:
        results = await ctg_service.search_ctg(
            term=params["query"],
            cond=params.get("cond"),
            intr=params.get("intr"),
            other_term=params.get("other_term"),
            page_size=params["pageSize"],
            page_token=params.get("ctgPageToken"),
            fetch_all=fetch_all,
            area_filter=area_filter,
            overall_status=overall_status,
            last_update_post_date=last_update_post_date
        )
    
    logger.info(f"ClinicalTrials.gov search completed: {len(results.get('results', []))} results")
    return results

def _merge_and_paginate_results(results: dict, query: str,
                                page: int, page_size: int) -> dict:
    """Merge PM and CTG results, sort by BM25, and paginate"""
    logger.info("=== MERGE AND PAGINATE START ===")
    try:
        pm_results  = results.get("pm",  {}).get("results", [])
        ctg_results = results.get("ctg", {}).get("results", [])
        logger.info(f"Input results - PM: {len(pm_results)}, CTG: {len(ctg_results)}")

        # Create unified list
        unified_results = []

        # PubMed results
        for item in pm_results:
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
                "abstract": item.get("abstract"),
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
                "bm25_score": item.get("bm25_score")
            }
            unified_results.append(unified_item)

        # CTG results
        for item in ctg_results:
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
                "bm25_score": item.get("bm25_score")
            }
            unified_results.append(unified_item)

        # Find MERGED pairs (bidirectional matching)
        pm_by_pmid   = {d["pmid"]: d for d in unified_results if d["type"] == "PM" and d["pmid"]}
        merged_items = []
        used_pmids, used_nctids = set(), set()

        for ctg_item in (d for d in unified_results if d["type"] == "CTG"):
            ref_pmids = ctg_item.get("pmids", [])
            if len(ref_pmids) == 1:
                ref_pmid = str(ref_pmids[0])
                if ref_pmid in pm_by_pmid:
                    pm_item = pm_by_pmid[ref_pmid]
                    pm_ref_nctids = pm_item.get("ref_nctids", [])
                    
                    if len(pm_ref_nctids) == 1 and str(pm_ref_nctids[0]) == ctg_item["nctid"]:
                        score = pm_item.get("bm25_score") or ctg_item.get("bm25_score")
                        
                        merged_classification = {
                            "study_type": ctg_item.get("study_type", pm_item.get("study_type", "NA")),
                            "phase": ctg_item.get("phase", pm_item.get("phase", "NA")),
                            "design_allocation": ctg_item.get("design_allocation", pm_item.get("design_allocation", "NA")),
                            "observational_model": ctg_item.get("observational_model", pm_item.get("observational_model", "NA"))
                        }
                        
                        merged_items.append({
                            "type": "MERGED",
                            "id": f"{ref_pmid}|{ctg_item['nctid']}",
                            "pmid": ref_pmid,
                            "nctid": ctg_item["nctid"],
                            "bm25_score": score,
                            "pm_data": pm_item,
                            "ctg_data": ctg_item,
                            "study_type": merged_classification["study_type"],
                            "phase": merged_classification["phase"],
                            "design_allocation": merged_classification["design_allocation"],
                            "observational_model": merged_classification["observational_model"]
                        })
                        used_pmids.add(ref_pmid)
                        used_nctids.add(ctg_item["nctid"])

        # Remaining standalone results
        pm_only_items  = [d for d in unified_results if d["type"] == "PM"  and d["pmid"]  not in used_pmids]
        ctg_only_items = [d for d in unified_results if d["type"] == "CTG" and d["nctid"] not in used_nctids]

        final_results = merged_items + pm_only_items + ctg_only_items

        # MERGED bonus and None value handling
        merge_bonus = 0.3
        for item in final_results:
            if item.get("bm25_score") is None:
                item["bm25_score"] = 0.0
            
            if item.get("type") == "MERGED":
                item["bm25_score"] = item["bm25_score"] + merge_bonus

        # Final sorting
        final_results.sort(
            key=lambda x: x.get("bm25_score", 0.0),
            reverse=True
        )

        # Counts
        merged_count   = len(merged_items)
        pm_only_count  = len(pm_only_items)
        ctg_only_count = len(ctg_only_items)
        total_count    = len(final_results)

        # Page slice
        start_idx = (page - 1) * page_size
        end_idx   = start_idx + page_size
        page_results = final_results[start_idx:end_idx]
        total_pages  = (total_count + page_size - 1) // page_size

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
        logger.error(traceback.format_exc())
        return {
            "results": [],
            "counts": {"total": 0, "merged": 0, "pm_only": 0, "ctg_only": 0},
            "total": 0,
            "totalPages": 0
        }

def _get_full_merged_results_for_csv(results: dict, query: str) -> List[Dict]:
    """Generate full merged results for CSV logging"""
    try:
        pm_results = results.get("pm", {}).get("results", [])
        ctg_results = results.get("ctg", {}).get("results", [])
        
        unified_results = []
        
        for item in pm_results:
            unified_results.append({
                "type": "PM",
                "id": item.get("pmid"),
                "pmid": item.get("pmid"),
                "title": item.get("title", ""),
                "bm25_score": item.get("bm25_score")
            })
        
        for item in ctg_results:
            unified_results.append({
                "type": "CTG",
                "id": item.get("id"),
                "nctid": item.get("id"),
                "title": item.get("title", ""),
                "pmids": item.get("pmids", []),
                "bm25_score": item.get("bm25_score")
            })
        
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
                        "id": f"{ref_pmid}|{ctg_item['nctid']}",
                        "pmid": ref_pmid,
                        "nctid": ctg_item["nctid"],
                        "title": f"{pm_item['title']} / {ctg_item['title']}",
                        "bm25_score": score,
                        "pmids": [ref_pmid]
                    })
                    used_pmids.add(ref_pmid)
                    used_nctids.add(ctg_item["nctid"])
        
        pm_only_items = [d for d in unified_results if d["type"] == "PM" and d["pmid"] not in used_pmids]
        ctg_only_items = [d for d in unified_results if d["type"] == "CTG" and d["nctid"] not in used_nctids]
        
        final_results = merged_items + pm_only_items + ctg_only_items
        
        merge_bonus = 0.3
        for item in final_results:
            if item.get("bm25_score") is None:
                item["bm25_score"] = 0.0
                
            if item.get("type") == "MERGED":
                item["bm25_score"] = item["bm25_score"] + merge_bonus
        
        final_results.sort(
            key=lambda x: x.get("bm25_score", 0.0),
            reverse=True
        )
        
        return final_results
        
    except Exception as e:
        logger.error(f"Error in _get_full_merged_results_for_csv: {e}")
        return []