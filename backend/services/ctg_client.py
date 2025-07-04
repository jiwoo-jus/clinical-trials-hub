# services/ctg_client.py
from __future__ import annotations

import logging, requests, asyncio, aiohttp
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
                           intr: Optional[str] = None, max_limit: int = MAX_FETCH_SIZE) -> List[str]:
    """
    Fetch all CTG study IDs using paginated requests.
    Based on the test file approach but with async support.
    """
    all_ids = []
    page_size = CTG_MAX_PAGE_SIZE
    
    params = {
        "fields": "NCTId",
        "pageSize": page_size,
        "countTotal": "true"
    }
    
    # Add search parameters
    if term:
        params["query.term"] = term
    if cond:
        params["query.cond"] = cond
    if intr:
        params["query.intr"] = intr
    
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
        all_ids = _fetch_all_ctg_ids_sync(term, cond, intr, max_limit)
    
    log.info(f"🎉 Done. Total collected CTG IDs: {len(all_ids)}")
    return all_ids

def _fetch_all_ctg_ids_sync(term: Optional[str] = None, cond: Optional[str] = None,
                           intr: Optional[str] = None, max_limit: int = MAX_FETCH_SIZE) -> List[str]:
    """Synchronous fallback for fetching all CTG IDs."""
    all_ids = []
    page_size = CTG_MAX_PAGE_SIZE
    
    params = {
        "fields": "NCTId",
        "pageSize": page_size,
        "countTotal": "true"
    }
    
    # Add search parameters
    if term:
        params["query.term"] = term
    if cond:
        params["query.cond"] = cond
    if intr:
        params["query.intr"] = intr
    
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
               intr: Optional[str] = None, page_size: int = 25,
               page_token: Optional[str] = None, fetch_all: bool = False) -> Tuple[List[str], int, Optional[str]]:
    """
    Search CTG API for study IDs.
    If fetch_all=True, ignores pagination and fetches all IDs up to max limit.
    """
    if fetch_all:
        # Use the new fetch_all function
        try:
            # Try async version first in asyncio context
            import asyncio
            if asyncio.get_event_loop().is_running():
                # We're already in an async context, but can't await here
                # Fall back to sync version
                all_ids = _fetch_all_ctg_ids_sync(term, cond, intr, max_limit=MAX_FETCH_SIZE)
            else:
                # Create new event loop
                all_ids = asyncio.run(fetch_all_ctg_ids(term, cond, intr, max_limit=MAX_FETCH_SIZE))
        except Exception:
            # Fallback to sync version
            all_ids = _fetch_all_ctg_ids_sync(term, cond, intr, max_limit=MAX_FETCH_SIZE)
        
        return all_ids, len(all_ids), None
    
    # Original paginated search for regular use
    params = {
        "fields": "NCTId",
        "pageSize": page_size,
        "countTotal": "true"
    }
    
    if page_token:
        params["pageToken"] = page_token
    
    # Add search parameters
    if term:
        params["query.term"] = term
    if cond:
        params["query.cond"] = cond
    if intr:
        params["query.intr"] = intr
    
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