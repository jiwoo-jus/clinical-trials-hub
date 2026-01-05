# services/ctg_service.py
from __future__ import annotations

import logging, os, psycopg2, psycopg2.extras
from typing import Optional, Dict, Any, List, Union
from . import ctg_client
from rank_bm25 import BM25Okapi

log = logging.getLogger(__name__)

# ---------- PostgreSQL --------------------------------------------------------
def _pg():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASS", ""),
        dbname=os.getenv("DB_NAME", "trials"),
    )

def _fetch_ctg_details(ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch CTG study details from AACT database using optimized subqueries"""
    if not ids:
        return []

    # params는 그대로 유지
    params = [ids]

    # 🚀 최적화된 SQL: JOIN 폭발을 막기 위해 1:N 관계는 스칼라 서브쿼리(ARRAY)로 변경
    # GROUP BY와 DISTINCT를 제거하여 Sort 부하를 99% 감소시킴
    sql = """
        SELECT
            s.nct_id,
            s.brief_title,
            s.official_title,
            s.overall_status,
            s.phase,
            s.source as lead_sponsor,
            s.start_date,
            s.completion_date,
            s.primary_completion_date,
            s.study_type,
            CASE WHEN s.results_first_submitted_date IS NOT NULL THEN TRUE ELSE FALSE END as has_results,
            s.enrollment,
            s.enrollment_type,
            COALESCE(bs.description, '') as brief_summary,
            
            -- Design information (1:1 관계는 JOIN 유지)
            d.allocation as design_allocation,
            d.observational_model,
            d.intervention_model,
            d.masking,
            d.primary_purpose,
            
            -- Location information (countries) - Subquery
            COALESCE(
                ARRAY(
                    SELECT DISTINCT country 
                    FROM ctgov.facilities 
                    WHERE nct_id = s.nct_id AND country IS NOT NULL
                ),
                ARRAY[]::text[]
            ) as countries,
            
            -- Conditions - Subquery
            COALESCE(
                ARRAY(
                    SELECT DISTINCT name 
                    FROM ctgov.conditions 
                    WHERE nct_id = s.nct_id AND name IS NOT NULL
                ),
                ARRAY[]::text[]
            ) as conditions,
            
            -- Keywords - Subquery
            COALESCE(
                ARRAY(
                    SELECT DISTINCT name 
                    FROM ctgov.keywords 
                    WHERE nct_id = s.nct_id AND name IS NOT NULL
                ),
                ARRAY[]::text[]
            ) as keywords,
            
            -- PMIDs - Subquery
            COALESCE(
                ARRAY(
                    SELECT DISTINCT pmid 
                    FROM ctgov.study_references 
                    WHERE nct_id = s.nct_id AND pmid IS NOT NULL
                ),
                ARRAY[]::text[]
            ) as pmids,
            
            -- Primary Outcomes - Subquery
            COALESCE(
                ARRAY(
                    SELECT DISTINCT title 
                    FROM ctgov.outcomes 
                    WHERE nct_id = s.nct_id AND outcome_type = 'primary' AND title IS NOT NULL
                ),
                ARRAY[]::text[]
            ) as primary_outcomes,
            
            -- Secondary Outcomes - Subquery
            COALESCE(
                ARRAY(
                    SELECT DISTINCT title 
                    FROM ctgov.outcomes 
                    WHERE nct_id = s.nct_id AND outcome_type = 'secondary' AND title IS NOT NULL
                ),
                ARRAY[]::text[]
            ) as secondary_outcomes,
            
            -- Intervention information - Subquery
            COALESCE(
                ARRAY(
                    SELECT DISTINCT name 
                    FROM ctgov.interventions 
                    WHERE nct_id = s.nct_id AND name IS NOT NULL
                ),
                ARRAY[]::text[]
            ) as intervention_names,
            
            -- Collaborators - Subquery
            COALESCE(
                ARRAY(
                    SELECT DISTINCT name 
                    FROM ctgov.sponsors 
                    WHERE nct_id = s.nct_id AND lead_or_collaborator = 'collaborator' AND name IS NOT NULL
                ),
                ARRAY[]::text[]
            ) as collaborators
            
        FROM ctgov.studies s
        -- 1:1 관계인 테이블만 JOIN (데이터 뻥튀기 없음)
        LEFT JOIN ctgov.designs d ON d.nct_id = s.nct_id
        LEFT JOIN ctgov.brief_summaries bs ON bs.nct_id = s.nct_id
        
        WHERE s.nct_id = ANY(%s)
        -- 🚫 GROUP BY 제거: 서브쿼리를 썼기 때문에 이제 GROUP BY가 필요 없습니다!
    """
    
    log.debug(f"[_fetch_ctg_details] Optimized CTG DB query executed.")

    try:
        with _pg() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        # Maintain original order from API
        nct_order = {nct_id: idx for idx, nct_id in enumerate(ids)}
        rows.sort(key=lambda r: nct_order.get(r["nct_id"], len(ids)))
        
        log.info(f"Fetched {len(rows)} CTG studies from DB for {len(ids)} requested IDs")
        return rows
        
    except Exception as e:
        log.error(f"Database error fetching CTG details: {e}")
        return []

def _build_corpus_for_bm25(results: List[Dict]) -> List[str]:
    """Build text corpus for BM25 ranking"""
    corpus = []
    for doc in results:
        text_parts = []
        
        # Title (highest weight)
        title = doc.get("title", "").strip()
        if title:
            text_parts.append(title)
        
        # Conditions (high weight)
        conditions = doc.get("conditions", [])
        if conditions:
            text_parts.append(" ".join(conditions))
        
        # Brief summary (medium weight)
        summary = doc.get("brief_summary", "").strip()
        if summary:
            text_parts.append(summary)
        
        # Keywords (low weight)
        keywords = doc.get("keywords", [])
        if keywords:
            text_parts.append(" ".join(keywords))
        
        corpus.append(" ".join(text_parts))
    
    return corpus

def _rerank_with_bm25(query: str, results: List[Dict]) -> List[Dict]:
    """Rerank CTG results using BM25"""
    if not query or not results:
        for d in results: d["bm25_score"] = None
        return results

    corpus = _build_corpus_for_bm25(results)
    valid = [(i, t) for i, t in enumerate(corpus) if t.strip()]
    if not valid:
        for d in results: d["bm25_score"] = None
        return results

    tokenized = [t.lower().split() for _, t in valid]
    bm25 = BM25Okapi(tokenized)
    raw = bm25.get_scores(query.lower().split())

    # normalize
    max_s, min_s = max(raw), min(raw)
    norm = [(s - min_s) / (max_s - min_s) if max_s > min_s else 0.0 for s in raw]

    original_weight = 0.2
    N = len(results)
    for idx, doc in enumerate(results):
        if idx in dict(valid):
            pos = [v[0] for v in valid].index(idx)
            bonus = (N - idx) / N * original_weight
            doc["bm25_score"] = norm[pos] + bonus
        else:
            doc["bm25_score"] = 0.0

    # Sort
    return sorted(results, key=lambda x: x.get("bm25_score", 0.0), reverse=True)

# ---------- Public API ---------------------------------------------------------
async def search_ctg(*, term: Optional[str] = None, cond: Optional[str] = None,
               intr: Optional[str] = None, other_term: Optional[str] = None,
               area_filter: Optional[str] = None,
               last_update_post_date: Optional[str] = None,
               overall_status: Optional[str] = None,
               page_size: int = 25, page_token: Optional[str] = None,
               fetch_all: bool = False) -> Dict[str, Any]:
    """
    Search ClinicalTrials.gov using API for IDs and database for details without pre-filtering
    
    Args:
        term: General search term
        cond: Condition/disease
        intr: Intervention
        other_term: Additional search terms
        area_filter: AREA filter string (e.g., 'AREA[protocolSection.designModule.studyType] Interventional')
        last_update_post_date: Date range filter (e.g., '2023-01-01_2024-12-31')
        overall_status: Status filter (e.g., 'RECRUITING', 'RECRUITING|COMPLETED')
        page_size: Results per page
        page_token: Pagination token
        fetch_all: Whether to fetch all results
    """
    try:
        # Step 1: Get study IDs from CTG API
        log.debug(f"Searching CTG API with term='{term}', cond='{cond}', intr='{intr}', status='{overall_status}', fetch_all={fetch_all}")
        
        if fetch_all:
            ids, total, next_token = ctg_client.search_ids(
                term=term,
                cond=cond,
                intr=intr,
                area_filter=area_filter,
                overall_status=overall_status,
                last_update_post_date=last_update_post_date,
                fetch_all=True
            )
            log.info(f"Fetched {len(ids)} CTG IDs (fetch_all mode)")
        else:
            # Normal paginated search
            ids, total, next_token = ctg_client.search_ids(
                term=term,
                cond=cond,
                intr=intr,
                area_filter=area_filter,
                last_update_post_date=last_update_post_date,
                page_size=page_size,
                page_token=page_token
            )
        
        if not ids:
            # Build the full query string showing what was actually searched
            full_query_parts = []
            if cond:
                full_query_parts.append(f"Condition: {cond}")
            if intr:
                full_query_parts.append(f"Intervention: {intr}")
            if other_term:
                full_query_parts.append(f"Other terms: {other_term}")
            if area_filter:
                full_query_parts.append(f"AREA Filters: {area_filter}")
            if overall_status:
                full_query_parts.append(f"Status: {overall_status}")
            full_query = " | ".join(full_query_parts) if full_query_parts else ""
            
            return {
                "results": [],
                "total": 0,
                "nextPageToken": None,
                "applied_query": full_query
            }
        
        # Step 2: Get details from database without pre-filters
        db_results = _fetch_ctg_details(ids=ids)
        
        # Step 3: Format results (same as before)
        formatted_results = []
        for row in db_results:
            study_type = row.get("study_type") or ""
            
            # Set design_allocation and observational_model based on study type
            design_allocation = None
            observational_model = None
            
            if "interventional" in study_type.lower():
                design_allocation = row.get("design_allocation") or ""
            elif "observational" in study_type.lower():
                observational_model = row.get("observational_model") or ""
            
            formatted_results.append({
                "source": "CTG",
                "type": "CTG",  # Add type field for filtering
                "id": row["nct_id"],
                "nct_id": row["nct_id"],  # Keep nct_id for filter stats calculation
                "title": row.get("brief_title") or "",
                "official_title": row.get("official_title") or "",
                "status": row.get("overall_status") or "",
                "brief_summary": row.get("brief_summary") or "",
                "phase": row.get("phase") or "",
                "lead_sponsor": row.get("lead_sponsor") or "",
                "start_date": row.get("start_date"),
                "completion_date": row.get("completion_date"),
                "primary_completion_date": row.get("primary_completion_date"),
                "study_type": study_type,
                "has_results": row.get("has_results") or False,
                "enrollment": row.get("enrollment"),
                "enrollment_type": row.get("enrollment_type") or "",
                "countries": row.get("countries") or [],
                "conditions": row.get("conditions") or [],
                "keywords": row.get("keywords") or [],
                "pmids": row.get("pmids") or [],
                "primary_outcomes": row.get("primary_outcomes") or [],
                "secondary_outcomes": row.get("secondary_outcomes") or [],
                # include study design fields conditionally
                "design_allocation": design_allocation,
                "observational_model": observational_model,
                "intervention_names": row.get("intervention_names") or [],
                "collaborators": row.get("collaborators") or [],
            })
        
        # Step 4: Apply BM25 reranking if query provided
        if term and formatted_results:
            formatted_results = _rerank_with_bm25(term, formatted_results)
        else:
            for result in formatted_results:
                result["bm25_score"] = None
        
        # Build the full query string showing what was actually searched
        log.debug(f"🔍 Building applied_query: cond={cond}, intr={intr}, term={term}, other_term={other_term}, area_filter={area_filter}, overall_status={overall_status}")
        full_query_parts = []
        if cond:
            full_query_parts.append(f"Condition: {cond}")
        if intr:
            full_query_parts.append(f"Intervention: {intr}")
        # Use term if other_term is not provided (common in filter endpoint)
        if other_term:
            full_query_parts.append(f"Other terms: {other_term}")
        elif term and not cond and not intr:
            # If only term is provided without cond/intr, use it as main query
            full_query_parts.append(f"Query: {term}")
        if area_filter:
            full_query_parts.append(f"AREA Filters: {area_filter}")
        if overall_status:
            full_query_parts.append(f"Status: {overall_status}")
        full_query = " | ".join(full_query_parts) if full_query_parts else (term or "")
        log.info(f"✅ Built applied_query: {full_query}")
        
        return {
            "results": formatted_results,
            "total": total,
            "nextPageToken": next_token,
            "applied_query": full_query
        }
        
    except Exception as e:
        log.error(f"CTG search failed: {e}")
        # Build the full query string for error case too
        full_query_parts = []
        if cond:
            full_query_parts.append(f"Condition: {cond}")
        if intr:
            full_query_parts.append(f"Intervention: {intr}")
        # Use term if other_term is not provided (common in filter endpoint)
        if other_term:
            full_query_parts.append(f"Other terms: {other_term}")
        elif term and not cond and not intr:
            # If only term is provided without cond/intr, use it as main query
            full_query_parts.append(f"Query: {term}")
        if area_filter:
            full_query_parts.append(f"AREA Filters: {area_filter}")
        if overall_status:
            full_query_parts.append(f"Status: {overall_status}")
        full_query = " | ".join(full_query_parts) if full_query_parts else (term or "")
        
        return {
            "results": [],
            "total": 0,
            "nextPageToken": None,
            "applied_query": full_query
        }

async def get_patient_results(data: dict) -> List[str]:
    gender_mapping = {
        'MALE': 'm',
        'FEMALE': 'f'
    }
    phase_mapping = {
        'Early Phase 1': '0',
        'Phase 1': '1',
        'Phase 2':'2',
        'Phase 3': '3',
        'Phase 4': '4',
    }
    types_mapping = {
        "Interventional": "int" ,
        "Observational": "obs" ,
        "Expanded Access": "exp"
    }
    sponsor_mapping = {
        "NIH": "nih" ,
        "U.S. federal agency": "fed" ,
        "Industry": "industry",
        "All others (individuals, universities, organizations)": "other"
    }

    refined_params = {
        "cond": data.get("cond", ""),
        "intr": data.get("intr", ""),
        "locStr": data.get("locStr", ""),
        "city": data.get("city", ""),
        "state": data.get("state", ""),
        "country": data.get("country", ""),
        "other_term": data.get("other_term", ""),
        "aggFilters": []
    }
    # Transform mapped fields
    if data.get("sex") in gender_mapping:
        refined_params["aggFilters"].append(f"sex:{gender_mapping[data['sex']]}")
    if data.get("age"):
        refined_params["aggFilters"].append(f"ages:{data['age']}")
    
    if data.get("phase"):
        phases = []
        for p in data['phase']:
            if p in phase_mapping:
                phases.append(phase_mapping[p])
        refined_params["aggFilters"].append(f"phase:{' '.join(phases)}")
    if data.get("study_type"):
        types = []
        for t in data['study_type']:
            if t in types_mapping:
                types.append(types_mapping[t])
        refined_params["aggFilters"].append(f"studyType:{' '.join(types)}")
    if data.get("sponsor"):
        spons = []
        for s in data['sponsor']:
            if s in sponsor_mapping:
                spons.append(sponsor_mapping[s])
        refined_params["aggFilters"].append(f"funderType:{' '.join(spons)}")

    # Status is always "not rec"
    refined_params["aggFilters"].append("status:not rec")
    ids = await ctg_client.get_ctg_ids_from_patient_search(refined_params)

    try:
        db_results = _fetch_ctg_details(
            ids=ids
        )
        # Step 3: Format results (same as before)
        formatted_results = []
        for row in db_results:
            study_type = row.get("study_type") or ""
            
            # Set design_allocation and observational_model based on study type
            design_allocation = None
            observational_model = None
            
            if "interventional" in study_type.lower():
                design_allocation = row.get("design_allocation") or ""
            elif "observational" in study_type.lower():
                observational_model = row.get("observational_model") or ""
            
            formatted_results.append({
                "source": "CTG",
                "type": "CTG",  # Add type field for filtering
                "id": row["nct_id"],
                "nct_id": row["nct_id"],  # Keep nct_id for filter stats calculation
                "title": row.get("brief_title") or "",
                "official_title": row.get("official_title") or "",
                "status": row.get("overall_status") or "",
                "brief_summary": row.get("brief_summary") or "",
                "phase": row.get("phase") or "",
                "lead_sponsor": row.get("lead_sponsor") or "",
                "start_date": row.get("start_date"),
                "completion_date": row.get("completion_date"),
                "primary_completion_date": row.get("primary_completion_date"),
                "study_type": study_type,
                "has_results": row.get("has_results") or False,
                "enrollment": row.get("enrollment"),
                "enrollment_type": row.get("enrollment_type") or "",
                "countries": row.get("countries") or [],
                "conditions": row.get("conditions") or [],
                "keywords": row.get("keywords") or [],
                "pmids": row.get("pmids") or [],
                "primary_outcomes": row.get("primary_outcomes") or [],
                "secondary_outcomes": row.get("secondary_outcomes") or [],
                # include study design fields conditionally
                "design_allocation": design_allocation,
                "observational_model": observational_model,
                "intervention_names": row.get("intervention_names") or [],
                "collaborators": row.get("collaborators") or [],
            })
        
        return {
           # "params": refined_params,
           # "ids": ids
            "results": formatted_results,
            "total": len(ids),
            "nextPageToken": None,
            "applied_query": ""
        }
        
    except Exception as e:
        log.error(f"CTG search failed: {e}")
        return {
            "results": [],
            "total": 0,
            "nextPageToken": None,
            "applied_query": ""
        }

# Add CTGService class at the end of the file
class CTGService:
    """CTG Service class wrapper for function-based CTG operations"""
    
    def get_study_details(self, nct_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed study information for a specific NCT ID"""
        try:
            # Use the existing _fetch_ctg_details function
            results = _fetch_ctg_details([nct_id])
            if results:
                return results[0]
            return None
        except Exception as e:
            log.error(f"Error fetching CTG details for {nct_id}: {str(e)}")
            return None
