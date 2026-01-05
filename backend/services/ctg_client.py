# services/ctg_client.py
from __future__ import annotations

import logging, requests, asyncio, aiohttp
import urllib.parse
from typing import Optional, Tuple, List
from time import sleep
from config import MAX_FETCH_SIZE

log = logging.getLogger(__name__)

CT_API = "https://clinicaltrials.gov/api/v2/studies"
TIMEOUT = 15
CTG_MAX_PAGE_SIZE = 1000  # Maximum page size for CTG API

class CtgApiError(RuntimeError):
    """CTG API error (4xx/5xx responses)"""

async def fetch_all_ctg_ids(term: Optional[str] = None, cond: Optional[str] = None,
                           intr: Optional[str] = None, max_limit: int = MAX_FETCH_SIZE,
                           area_filter: Optional[str] = None,
                           last_update_post_date: Optional[str] = None,
                           overall_status: Optional[str] = None) -> List[str]:
    """
    Fetch all CTG study IDs using paginated requests.
    Based on the test file approach but with async support.
    
    Args:
        term: General search term (can include AREA filters)
        cond: Condition/disease
        intr: Intervention
        max_limit: Maximum number of IDs to fetch
        area_filter: AREA filter string to append to query.term (e.g., 'AREA[protocolSection.designModule.studyType] Interventional')
        last_update_post_date: Date range filter (e.g., '2023-01-01_2024-12-31')
        overall_status: Overall status filter (e.g., 'RECRUITING|COMPLETED')
    """
    all_ids = []
    page_size = CTG_MAX_PAGE_SIZE
    
    params = {
        "fields": "NCTId",
        "pageSize": page_size,
        "countTotal": "true"
    }
    
    # Build combined query.term with AREA filters
    query_term_parts = []
    if term and term != 'None' and str(term).strip():
        query_term_parts.append(str(term).strip())
    if area_filter:
        query_term_parts.append(area_filter)
    
    if query_term_parts:
        params["query.term"] = " AND ".join(query_term_parts)
        log.info(f"🔍 CTG query.term: {params['query.term']}")
    else:
        log.warning("⚠️ No query.term built! Both 'term' and 'area_filter' are empty.")
    
    # Add search parameters - only add non-None, non-empty values
    if cond and cond != 'None' and str(cond).strip():
        params["query.cond"] = cond
        log.info(f"  query.cond: {cond}")
    if intr and intr != 'None' and str(intr).strip():
        params["query.intr"] = intr
        log.info(f"  query.intr: {intr}")
    
    # Add overall status filter
    if overall_status:
        params["filter.overallStatus"] = overall_status
        log.info(f"  filter.overallStatus: {overall_status}")
    
    # Add date filter parameter (backward compatibility, but should be in area_filter now)
    if last_update_post_date:
        params["lastUpdatePostDate"] = last_update_post_date
        log.warning(f"⚠️ Using deprecated lastUpdatePostDate parameter: {last_update_post_date}")
        log.warning("   Date filtering should be in area_filter using AREA[LastUpdatePostDate]RANGE syntax")
    
    try:
        # Try async first
        async with aiohttp.ClientSession() as session:
            page_token = None
            
            while True:
                current_params = params.copy()
                if page_token:
                    current_params["pageToken"] = page_token
                
                try:
                    async with session.get(CT_API, params=current_params, timeout=TIMEOUT) as response:
                        if response.status >= 400:
                            raise CtgApiError(f"CTG API error {response.status}: {await response.text()}")
                        
                        data = await response.json()
                        studies = data.get("studies", [])
                        
                        # Extract NCT IDs
                        batch_ids = []
                        for study in studies:
                            try:
                                nct_id = study["protocolSection"]["identificationModule"]["nctId"]
                                batch_ids.append(nct_id)
                            except KeyError:
                                log.warning("Missing NCT ID in study data")
                                continue
                        
                        all_ids.extend(batch_ids)
                        log.info(f"✅ Retrieved {len(batch_ids)} CTG IDs (total so far: {len(all_ids)})")
                        
                        # Check if we've reached the limit
                        if len(all_ids) >= max_limit:
                            all_ids = all_ids[:max_limit]
                            log.info(f"Reached limit of {max_limit} CTG IDs")
                            break
                        
                        # Check for next page
                        page_token = data.get("nextPageToken")
                        if not page_token:
                            log.info("✅ CTG retrieval complete - no more pages")
                            break
                        
                        await asyncio.sleep(0.3)  # Rate limiting
                        
                except Exception as e:
                    log.error(f"⚠️ Error fetching CTG page: {e}")
                    break
                    
    except ImportError:
        # Fallback to synchronous requests
        log.info("aiohttp not available, falling back to synchronous CTG requests")
        all_ids = _fetch_all_ctg_ids_sync(term, cond, intr, max_limit, area_filter, last_update_post_date)
    
    log.info(f"🎉 Done. Total collected CTG IDs: {len(all_ids)}")
    return all_ids

def _fetch_all_ctg_ids_sync(term: Optional[str] = None, cond: Optional[str] = None,
                           intr: Optional[str] = None, max_limit: int = MAX_FETCH_SIZE,
                           area_filter: Optional[str] = None,
                           last_update_post_date: Optional[str] = None,
                           overall_status: Optional[str] = None) -> List[str]:
    """Synchronous fallback for fetching all CTG IDs."""
    all_ids = []
    page_size = CTG_MAX_PAGE_SIZE
    
    params = {
        "fields": "NCTId",
        "pageSize": page_size,
        "countTotal": "true"
    }
    
    # Build combined query.term with AREA filters
    query_term_parts = []
    if term and term != 'None' and str(term).strip():
        query_term_parts.append(str(term).strip())
    if area_filter:
        query_term_parts.append(area_filter)
    
    if query_term_parts:
        params["query.term"] = " AND ".join(query_term_parts)
        log.info(f"🔍 CTG query.term (sync): {params['query.term']}")
    else:
        log.warning("⚠️ No query.term built (sync)! Both 'term' and 'area_filter' are empty.")
    
    # Add search parameters - only add non-None, non-empty values
    if cond and cond != 'None' and str(cond).strip():
        params["query.cond"] = cond
        log.info(f"  query.cond: {cond}")
    if intr and intr != 'None' and str(intr).strip():
        params["query.intr"] = intr
        log.info(f"  query.intr: {intr}")
    
    # Add overall status filter
    if overall_status:
        params["filter.overallStatus"] = overall_status
        log.info(f"  filter.overallStatus: {overall_status}")
    
    # Add date filter parameter (backward compatibility, but should be in area_filter now)
    if last_update_post_date:
        params["lastUpdatePostDate"] = last_update_post_date
        log.warning(f"⚠️ Using deprecated lastUpdatePostDate parameter (sync): {last_update_post_date}")
        log.warning("   Date filtering should be in area_filter using AREA[LastUpdatePostDate]RANGE syntax")
    
    page_token = None
    
    while True:
        current_params = params.copy()
        if page_token:
            current_params["pageToken"] = page_token
        
        try:
            response = requests.get(CT_API, params=current_params, timeout=TIMEOUT)
            
            if response.status_code >= 400:
                raise CtgApiError(f"CTG API error {response.status_code}: {response.text[:200]}")
            
            data = response.json()
            studies = data.get("studies", [])
            
            # Extract NCT IDs
            batch_ids = []
            for study in studies:
                try:
                    nct_id = study["protocolSection"]["identificationModule"]["nctId"]
                    batch_ids.append(nct_id)
                except KeyError:
                    log.warning("Missing NCT ID in study data")
                    continue
            
            all_ids.extend(batch_ids)
            log.info(f"✅ Retrieved {len(batch_ids)} CTG IDs (total so far: {len(all_ids)})")
            
            # Check if we've reached the limit
            if len(all_ids) >= max_limit:
                all_ids = all_ids[:max_limit]
                log.info(f"Reached limit of {max_limit} CTG IDs")
                break
            
            # Check for next page
            page_token = data.get("nextPageToken")
            if not page_token:
                log.info("✅ CTG retrieval complete - no more pages")
                break
            
            sleep(0.3)  # Rate limiting
            
        except Exception as e:
            log.error(f"⚠️ Error fetching CTG page: {e}")
            break
    
    return all_ids

def search_ids(term: Optional[str] = None, cond: Optional[str] = None,
               intr: Optional[str] = None, area_filter: Optional[str] = None,
               last_update_post_date: Optional[str] = None,
               overall_status: Optional[str] = None,
               page_size: int = 25,
               page_token: Optional[str] = None, fetch_all: bool = False) -> Tuple[List[str], int, Optional[str]]:
    """
    Search CTG API for study IDs.
    If fetch_all=True, ignores pagination and fetches all IDs up to max limit.
    
    Args:
        term: General search term (can include AREA filters)
        cond: Condition/disease
        intr: Intervention
        area_filter: AREA filter string (e.g., 'AREA[protocolSection.designModule.studyType] Interventional')
        last_update_post_date: Date range filter
        overall_status: Status filter (e.g., 'RECRUITING', 'RECRUITING|COMPLETED')
        page_size: Results per page
        page_token: Pagination token
        fetch_all: Whether to fetch all results
    """
    if fetch_all:
        # Use the new fetch_all function
        try:
            # Try async version first in asyncio context
            import asyncio
            if asyncio.get_event_loop().is_running():
                # We're already in an async context, but can't await here
                # Fall back to sync version
                all_ids = _fetch_all_ctg_ids_sync(term, cond, intr, max_limit=MAX_FETCH_SIZE,
                                                 area_filter=area_filter,
                                                 last_update_post_date=last_update_post_date,
                                                 overall_status=overall_status)
            else:
                # Create new event loop
                all_ids = asyncio.run(fetch_all_ctg_ids(term, cond, intr, max_limit=MAX_FETCH_SIZE,
                                                        area_filter=area_filter,
                                                        last_update_post_date=last_update_post_date,
                                                        overall_status=overall_status))
        except Exception:
            # Fallback to sync version
            all_ids = _fetch_all_ctg_ids_sync(term, cond, intr, max_limit=MAX_FETCH_SIZE,
                                             area_filter=area_filter,
                                             last_update_post_date=last_update_post_date,
                                             overall_status=overall_status)
        
        return all_ids, len(all_ids), None
    
    # Original paginated search for regular use
    params = {
        "fields": "NCTId",
        "pageSize": page_size,
        "countTotal": "true"
    }
    
    if page_token:
        params["pageToken"] = page_token    # Build combined query.term with AREA filters
    query_term_parts = []
    if term and term != 'None' and str(term).strip():
        query_term_parts.append(str(term).strip())
    if area_filter:
        query_term_parts.append(area_filter)
    
    if query_term_parts:
        params["query.term"] = " AND ".join(query_term_parts)
    
    # Add search parameters - only add non-None, non-empty values
    if cond and cond != 'None' and str(cond).strip():
        params["query.cond"] = cond
    if intr and intr != 'None' and str(intr).strip():
        params["query.intr"] = intr
    
    # Add date filter parameter
    if last_update_post_date:
        params["lastUpdatePostDate"] = last_update_post_date
    
    try:
        log.debug(f"CTG API call: {CT_API} with params: {params}")
        response = requests.get(CT_API, params=params, timeout=TIMEOUT)
        
        if response.status_code >= 400:
            raise CtgApiError(f"CTG API error {response.status_code}: {response.text[:200]}")
        
        data = response.json()
        studies = data.get("studies", [])
        
        # Extract NCT IDs
        ids = []
        for study in studies:
            try:
                nct_id = study["protocolSection"]["identificationModule"]["nctId"]
                ids.append(nct_id)
            except KeyError:
                log.warning("Missing NCT ID in study data")
                continue
        
        total = int(data.get("totalCount", 0))
        next_token = data.get("nextPageToken")
        
        log.info(f"CTG API returned {len(ids)} IDs (total: {total}, next: {next_token})")
        return ids, total, next_token
        
    except requests.RequestException as e:
        log.error(f"CTG API request failed: {e}")
        raise CtgApiError(f"Network error: {e}")
    except (ValueError, KeyError) as e:
        log.error(f"CTG API response parsing failed: {e}")
        raise CtgApiError(f"Invalid response format: {e}")

def get_ctg_detail(nctId: str) -> dict:
    print(f"Fetching CTG detail for nctId: {nctId}")
    params = {
        "query.id": nctId,
        "format": "json"
    }
    response = requests.get(CT_API, params=params)
    if response.status_code != 200:
        logging.error(f"CTG API returned status {response.status_code}")
        logging.error(f"Response content: {response.text}")
        raise Exception("CTG API returned non-200 status")
    json_data = response.json()
    studies = json_data.get("studies", [])
    if not studies:
        raise Exception(f"No CTG detail found for nctId {nctId}")
    return studies[0]

async def get_ctg_ids_from_patient_search(refined_params: dict) -> List[str]:
    base_url = "https://clinicaltrials.gov/api/int/studies"
    params = {
        "cond": refined_params.get("cond", ""),
        "term": refined_params.get("other_term", ""),
        "intr": refined_params.get("intr", ""),
        "locStr": refined_params.get("locStr", ""),
        "city": refined_params.get("city", ""),
        "state": refined_params.get("state", ""),
        "country": refined_params.get("country", ""),
        "aggFilters": "",
        "checkSpell": "true",
        "from": "0",
        "limit": str(1000),
        "fields": "OverallStatus,LastKnownStatus,StatusVerifiedDate,HasResults,BriefTitle,Condition,InterventionType,InterventionName,LocationFacility,LocationCity,LocationState,LocationCountry,LocationStatus,LocationZip,LocationGeoPoint,LocationContactName,LocationContactRole,LocationContactPhone,LocationContactPhoneExt,LocationContactEMail,CentralContactName,CentralContactRole,CentralContactPhone,CentralContactPhoneExt,CentralContactEMail,Gender,MinimumAge,MaximumAge,StdAge,NCTId,StudyType,LeadSponsorName,Acronym,EnrollmentCount,StartDate,PrimaryCompletionDate,CompletionDate,StudyFirstPostDate,ResultsFirstPostDate,LastUpdatePostDate,OrgStudyId,SecondaryId,Phase,LargeDocLabel,LargeDocFilename,PrimaryOutcomeMeasure,SecondaryOutcomeMeasure,DesignAllocation,DesignInterventionModel,DesignMasking,DesignWhoMasked,DesignPrimaryPurpose,DesignObservationalModel,DesignTimePerspective,LeadSponsorClass,CollaboratorClass", 
        "columns": "conditions,interventions,collaborators",
        "highlight": "true",
        "sort": "@relevance"
       # "term": refined_params.get("other_term", "")
    }

    # Append aggFilters into query string
    agg_filters = ",".join(refined_params.get("aggFilters", []))
    if agg_filters:
        params["aggFilters"] = agg_filters

    params = {k: v for k, v in params.items() if v is not None and len(v) > 0}

    from urllib.parse import urlencode
    full_url = f"{base_url}?{urlencode(params)}"
    print(full_url)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(base_url, params=params, timeout=TIMEOUT) as response:
                if response.status >= 400:
                    raise CtgApiError(f"CTG API error {response.status}: {await response.text()}")
                
                data = await response.json()
                return [hit["id"] for hit in data.get("hits", [])]
        except Exception as e:
            log.error(f"⚠️ Error fetching CTG page: {e}")
            return []

    # Extract NCT IDs
   