# services/ctg_service.py
from __future__ import annotations

import logging, os, psycopg2, psycopg2.extras
from typing import Optional, Dict, Any, List
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

def _fetch_ctg_details(ids: List[str], gender: Optional[str] = None, 
                      ages: Optional[str] = None, sponsor: Optional[str] = None, 
                      location: Optional[str] = None, status: Optional[str] = None,
                      phase: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch CTG study details from AACT database with accurate filters"""
    if not ids:
        return []

    conditions = ["s.nct_id = ANY(%s)"]
    params = [ids]

    # Phase filter
    if phase:
        conditions.append("s.phase = %s")
        params.append(phase)

    # Status filter - map enum values
    if status:
        status_mapping = {
            'NOT_YET_RECRUITING': 'Not yet recruiting',
            'RECRUITING': 'Recruiting',
            'ENROLLING_BY_INVITATION': 'Enrolling by invitation',
            'ACTIVE_NOT_RECRUITING': 'Active, not recruiting',
            'SUSPENDED': 'Suspended',
            'TERMINATED': 'Terminated',
            'COMPLETED': 'Completed',
            'WITHDRAWN': 'Withdrawn',
            'UNKNOWN': 'Unknown status'
        }
        mapped_status = status_mapping.get(status, status)
        conditions.append("s.overall_status = %s")
        params.append(mapped_status)

    # Sponsor filter
    if sponsor:
        conditions.append("s.source ILIKE %s")
        params.append(f"%{sponsor}%")

    # Location filter (using facilities table)
    location_join = ""
    if location:
        location_join = "JOIN ctgov.facilities f ON f.nct_id = s.nct_id"
        conditions.append("(f.city ILIKE %s OR f.state ILIKE %s OR f.country ILIKE %s)")
        params.extend([f"%{location}%", f"%{location}%", f"%{location}%"])

    # Gender and age filters (using eligibilities table)
    eligibility_join = ""
    if gender or ages:
        eligibility_join = "JOIN ctgov.eligibilities e ON e.nct_id = s.nct_id"
        
        if gender and gender != 'ALL':
            gender_mapping = {
                'MALE': 'Male',
                'FEMALE': 'Female'
            }
            mapped_gender = gender_mapping.get(gender, gender)
            conditions.append("e.gender = %s")
            params.append(mapped_gender)
        
        if ages:
            # Age filtering logic based on minimum/maximum age
            if ages == 'Child':
                conditions.append("(e.minimum_age_num IS NULL OR e.minimum_age_num <= 17)")
            elif ages == 'Adult':
                conditions.append("(e.minimum_age_num IS NULL OR e.minimum_age_num <= 64) AND (e.maximum_age_num IS NULL OR e.maximum_age_num >= 18)")
            elif ages == 'Older Adult':
                conditions.append("(e.maximum_age_num IS NULL OR e.maximum_age_num >= 65)")

    # Build optimized SQL query
    sql = f"""
        SELECT DISTINCT
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
            
            -- Design information
            d.allocation as design_allocation,
            d.observational_model,
            d.intervention_model,
            d.masking,
            d.primary_purpose,
            
            -- Location information (countries)
            COALESCE(
                array_agg(DISTINCT f.country) FILTER (WHERE f.country IS NOT NULL),
                ARRAY[]::text[]
            ) as countries,
            
            -- Aggregate related data
            COALESCE(
                array_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL),
                ARRAY[]::text[]
            ) as conditions,
            
            COALESCE(
                array_agg(DISTINCT k.name) FILTER (WHERE k.name IS NOT NULL),
                ARRAY[]::text[]
            ) as keywords,
            
            COALESCE(
                array_agg(DISTINCT sr.pmid) FILTER (WHERE sr.pmid IS NOT NULL),
                ARRAY[]::text[]
            ) as pmids,
            
            COALESCE(
                array_agg(DISTINCT po.title) FILTER (WHERE po.title IS NOT NULL),
                ARRAY[]::text[]
            ) as primary_outcomes,
            
            COALESCE(
                array_agg(DISTINCT so.title) FILTER (WHERE so.title IS NOT NULL),
                ARRAY[]::text[]
            ) as secondary_outcomes,
            
            -- Intervention information
            COALESCE(
                array_agg(DISTINCT i.name) FILTER (WHERE i.name IS NOT NULL),
                ARRAY[]::text[]
            ) as intervention_names,
            
            -- Sponsor information
            COALESCE(
                array_agg(DISTINCT sp.name) FILTER (WHERE sp.name IS NOT NULL AND sp.lead_or_collaborator = 'collaborator'),
                ARRAY[]::text[]
            ) as collaborators
            
        FROM ctgov.studies s
        {eligibility_join}
        LEFT JOIN ctgov.designs d ON d.nct_id = s.nct_id
        LEFT JOIN ctgov.facilities f ON f.nct_id = s.nct_id {location_join.replace('JOIN ctgov.facilities f ON f.nct_id = s.nct_id', '') if location_join else ''}
        LEFT JOIN ctgov.brief_summaries bs ON bs.nct_id = s.nct_id
        LEFT JOIN ctgov.conditions c ON c.nct_id = s.nct_id
        LEFT JOIN ctgov.keywords k ON k.nct_id = s.nct_id
        LEFT JOIN ctgov.study_references sr ON sr.nct_id = s.nct_id
        LEFT JOIN ctgov.outcomes po ON po.nct_id = s.nct_id AND po.outcome_type = 'primary'
        LEFT JOIN ctgov.outcomes so ON so.nct_id = s.nct_id AND so.outcome_type = 'secondary'
        LEFT JOIN ctgov.interventions i ON i.nct_id = s.nct_id
        LEFT JOIN ctgov.sponsors sp ON sp.nct_id = s.nct_id
        WHERE {' AND '.join(conditions)}
        GROUP BY s.nct_id, s.brief_title, s.official_title, s.overall_status, 
                 s.phase, s.source, s.start_date, s.completion_date, s.primary_completion_date, 
                 s.study_type, s.results_first_submitted_date, s.enrollment, s.enrollment_type, 
                 bs.description, d.allocation, d.observational_model, d.intervention_model, 
                 d.masking, d.primary_purpose
    """
    
    log.debug(f"[_fetch_ctg_details] CTG DB query: {sql}")
    log.debug(f"[_fetch_ctg_details] Number of parameters(nctids) on query: {len(params)}")

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
def search_ctg(*, term: Optional[str] = None, cond: Optional[str] = None,
               intr: Optional[str] = None, study_type: Optional[str] = None,
               phase: Optional[str] = None, gender: Optional[str] = None, 
               ages: Optional[str] = None, sponsor: Optional[str] = None, 
               location: Optional[str] = None, status: Optional[str] = None, 
               page_size: int = 25, page_token: Optional[str] = None,
               fetch_all: bool = False) -> Dict[str, Any]:
    """
    Search ClinicalTrials.gov using API for IDs and database for details with proper filters
    """
    try:
        # Step 1: Get study IDs from CTG API
        log.info(f"Searching CTG API with term='{term}', cond='{cond}', intr='{intr}', fetch_all={fetch_all}")
        
        if fetch_all:
            # Fetch all IDs up to limit
            ids, total, next_token = ctg_client.search_ids(
                term=term,
                cond=cond,
                intr=intr,
                fetch_all=True
            )
            log.info(f"Fetched {len(ids)} CTG IDs (fetch_all mode)")
        else:
            # Normal paginated search
            ids, total, next_token = ctg_client.search_ids(
                term=term,
                cond=cond,
                intr=intr,
                page_size=page_size,
                page_token=page_token
            )
        
        if not ids:
            return {
                "results": [],
                "total": 0,
                "nextPageToken": None,
                "applied_query": term or ""
            }
        
        # Step 2: Get details from database with filters
        db_results = _fetch_ctg_details(
            ids=ids, 
            gender=gender, 
            ages=ages, 
            sponsor=sponsor, 
            location=location, 
            status=status,
            phase=phase
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
        
        return {
            "results": formatted_results,
            "total": total,
            "nextPageToken": next_token,
            "applied_query": term or ""
        }
        
    except Exception as e:
        log.error(f"CTG search failed: {e}")
        return {
            "results": [],
            "total": 0,
            "nextPageToken": None,
            "applied_query": term or ""
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
