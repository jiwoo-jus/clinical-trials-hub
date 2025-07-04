from fastapi import APIRouter, HTTPException, Query
from utils import convert_pmid_to_pmcid # Keep existing import
from typing import List, Dict, Any # Import typing helpers
from services.cache_service import get_cache_info, test_redis_connection

router = APIRouter()

@router.get("/cache/status")
async def get_cache_status():
    try:
        cache_info = get_cache_info()
        redis_test = test_redis_connection()
        
        return {
            "cache_info": cache_info,
            "redis_connection_test": redis_test,
            "status": "Redis available" if redis_test else "Using memory cache only"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache status check failed: {str(e)}")


@router.get("/convert_pmid_to_pmcid")
async def convert_single_pmid(pmid: str = Query(..., description="The PubMed ID (PMID) to convert.")):
    """
    Converts a SINGLE PMID to its corresponding PMCID using the NCBI ID Converter API.
    Note: The underlying utility function now handles multiple PMIDs.
    """
    try:
        records = convert_pmid_to_pmcid(pmid) # Util function returns a list
        if records and records[0].get("pmcid"):
            # Return the first record's PMCID for single lookup compatibility
            return {"pmid": pmid, "pmcid": records[0]["pmcid"]}
        elif records and records[0].get("status") == 'error':
             # Handle specific error from NCBI if available
             raise HTTPException(status_code=404, detail=f"Error converting PMID {pmid}: {records[0].get('errmsg', 'Unknown error')}")
        else:
            # General case if no PMCID found or empty list returned
            raise HTTPException(status_code=404, detail=f"No PMCID found or conversion failed for PMID {pmid}")
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly
        raise http_exc
    except Exception as e:
        print(f"Error in /convert_pmid_to_pmcid endpoint for single PMID {pmid}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during single ID conversion.")


# Add the new batch endpoint
@router.get("/pmid_to_pmcid_batch", response_model=List[Dict[str, Any]])
async def pmid_to_pmcid_batch_route(pmids: str = Query(..., description="Comma-separated list of PubMed IDs (PMIDs) to convert.")):
    """
    Converts a comma-separated list of PMIDs to their corresponding PMC records
    (including PMCID if available) using the NCBI ID Converter API.
    """
    if not pmids:
        return [] # Return empty list if input is empty
    try:
        # Call the utility function directly with the comma-separated string
        records = convert_pmid_to_pmcid(pmids)
        # Return the list of records received from the utility function
        return records
    except Exception as e:
        # Log the error for debugging
        print(f"Error in /pmid_to_pmcid_batch endpoint for PMIDs '{pmids}': {e}")
        # Raise a generic 500 error to the client
        raise HTTPException(status_code=500, detail="Internal server error during batch ID conversion.")
