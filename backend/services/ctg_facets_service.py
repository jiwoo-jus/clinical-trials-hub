"""
CTG Facets Service - Uses PostgreSQL function for efficient filter statistics
"""
import logging
import os
import psycopg2
import psycopg2.extras
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def get_pg_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASS", ""),
        dbname=os.getenv("DB_NAME", "trials"),
    )


def get_ctg_facets(nct_ids: List[str]) -> Dict[str, Any]:
    """
    Get CTG filter facets using PostgreSQL function.
    
    Args:
        nct_ids: List of NCT IDs to calculate facets for
        
    Returns:
        Dictionary with facet counts matching frontend filter structure
    """
    if not nct_ids:
        return _empty_facets()
    
    try:
        conn = get_pg_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Call the PostgreSQL function
            cur.execute(
                "SELECT facets_for_nct_ids(%s) as facets",
                (nct_ids,)
            )
            result = cur.fetchone()
            
            if result and result['facets']:
                facets = result['facets']
                
                # Add CTG-specific filter statistics
                facets['ctg_filters'] = _get_ctg_specific_stats(cur, nct_ids)
                
                logger.info(f"CTG facets calculated for {len(nct_ids)} NCT IDs")
                return facets
            else:
                logger.warning(f"No facets returned for {len(nct_ids)} NCT IDs")
                return _empty_facets()
                
    except Exception as e:
        logger.error(f"Error getting CTG facets: {e}", exc_info=True)
        return _empty_facets()
    finally:
        if conn:
            conn.close()


def _get_ctg_specific_stats(cur, nct_ids: List[str]) -> Dict[str, Any]:
    """
    Calculate CTG-specific filter statistics (Has Results, Status)
    
    Args:
        cur: Database cursor
        nct_ids: List of NCT IDs to calculate stats for
        
    Returns:
        Dictionary with has_results count and status counts
    """
    stats = {
        'has_results': 0,
        'status': {
            'recruiting': 0,
            'completed': 0
        }
    }
    
    try:
        # Count studies with results
        cur.execute("""
            SELECT COUNT(DISTINCT cv.nct_id) as count
            FROM ctgov.calculated_values cv
            WHERE cv.nct_id = ANY(%s)
            AND cv.were_results_reported IS TRUE
        """, (nct_ids,))
        
        result = cur.fetchone()
        if result:
            stats['has_results'] = result['count'] or 0
            
        # Count by status (RECRUITING, COMPLETED)
        cur.execute("""
            SELECT 
                UPPER(TRIM(s.overall_status)) as status,
                COUNT(DISTINCT s.nct_id) as count
            FROM ctgov.studies s
            WHERE s.nct_id = ANY(%s)
            AND UPPER(TRIM(s.overall_status)) IN ('RECRUITING', 'COMPLETED')
            GROUP BY UPPER(TRIM(s.overall_status))
        """, (nct_ids,))
        
        status_results = cur.fetchall()
        for row in status_results:
            status = row['status'].lower()
            if status in stats['status']:
                stats['status'][status] = row['count'] or 0
                
        logger.info(f"CTG-specific stats: has_results={stats['has_results']}, recruiting={stats['status']['recruiting']}, completed={stats['status']['completed']}")
        
    except Exception as e:
        logger.error(f"Error calculating CTG-specific stats: {e}", exc_info=True)
    
    return stats


def _empty_facets() -> Dict[str, Any]:
    """Return empty facets structure"""
    return {
        'data_source': {
            'pubmed': 0,
            'clinicaltrials_gov': 0
        },
        'publication_date': {
            'within_1y': 0,
            'within_5y': 0,
            'within_10y': 0
        },
        'article_type': {
            'clinical_trial': 0,
            'interventional': 0,
            'observational': 0,
            'phase_i': 0,
            'phase_ii': 0,
            'phase_iii': 0,
            'phase_iv': 0,
            'randomized_controlled_trial': 0,
            'meta_analysis': 0,
            'review': 0,
            'systematic_review': 0
        },
        'additional_filters': {
            'species': {
                'humans': None,
                'other_animals': None
            },
            'age': {
                'child_0_18': 0,
                'adult_19_plus': 0,
                'aged_65_plus': 0
            }
        },
        'ctg_filters': {
            'has_results': 0,
            'status': {
                'recruiting': 0,
                'completed': 0
            }
        }
    }
