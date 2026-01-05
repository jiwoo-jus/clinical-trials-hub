"""
Unified filter statistics service using PostgreSQL for CTG and Python for PubMed.
Combines both sources into a single filter stats structure.
"""

from typing import Dict, List, Any, Optional
from collections import defaultdict
import logging
import re
from .ctg_facets_service import get_ctg_facets

logger = logging.getLogger(__name__)


def calculate_filter_stats(pm_results: List[Dict], ctg_results: List[Dict]) -> Dict[str, Any]:
    """
    Calculate unified filter statistics combining PubMed and CTG results.
    Uses PostgreSQL function for CTG (efficient) and Python for PubMed.
    
    Returns structure matching frontend filter requirements.
    """
    # Get CTG facets from PostgreSQL function
    # Extract NCT IDs from CTG results (use nctid field)
    nct_ids = []
    for r in ctg_results:
        nct_id = r.get('nctid') or r.get('id')  # Fallback to 'id' for compatibility
        if nct_id:
            nct_ids.append(nct_id)
    
    logger.info(f"Extracting NCT IDs from {len(ctg_results)} CTG results: found {len(nct_ids)} IDs")
    if ctg_results and not nct_ids:
        logger.warning(f"CTG results present but no NCT IDs found. Sample keys: {list(ctg_results[0].keys())[:10]}")
    
    ctg_facets = get_ctg_facets(nct_ids) if nct_ids else {
        'data_source': {'clinicaltrials_gov': 0},
        'publication_date': {'within_1y': 0, 'within_5y': 0, 'within_10y': 0},
        'article_type': {
            'clinical_trial': 0, 
            'interventional': 0,
            'observational': 0,
            'phase_i': 0, 'phase_ii': 0, 'phase_iii': 0,
            'phase_iv': 0, 'randomized_controlled_trial': 0,
            'meta_analysis': 0, 'review': 0, 'systematic_review': 0
        },
        'additional_filters': {
            'species': {'humans': None, 'other_animals': None},
            'age': {'child_0_18': 0, 'adult_19_plus': 0, 'aged_65_plus': 0}
        }
    }
    
    # Calculate PubMed stats (Python-based, focusing on article_type from publication_types)
    pm_stats = _calculate_pm_stats(pm_results)
    
    # Build unified structure with separated PM/CTG counts for each filter
    unified = {
        'data_source': {
            'pubmed': pm_stats['total'],
            'clinicaltrials_gov': ctg_facets['data_source']['clinicaltrials_gov']
        },
        'publication_date': {
            'within_1y': {
                'pm': pm_stats['publication_date']['within_1y'],
                'ctg': ctg_facets['publication_date']['within_1y'],
                'total': pm_stats['publication_date']['within_1y'] + ctg_facets['publication_date']['within_1y']
            },
            'within_5y': {
                'pm': pm_stats['publication_date']['within_5y'],
                'ctg': ctg_facets['publication_date']['within_5y'],
                'total': pm_stats['publication_date']['within_5y'] + ctg_facets['publication_date']['within_5y']
            },
            'within_10y': {
                'pm': pm_stats['publication_date']['within_10y'],
                'ctg': ctg_facets['publication_date']['within_10y'],
                'total': pm_stats['publication_date']['within_10y'] + ctg_facets['publication_date']['within_10y']
            }
        },
        'article_type': {
            'clinical_trial': {
                'pm': pm_stats['article_type']['clinical_trial'],
                'ctg': ctg_facets['article_type']['clinical_trial'],
                'total': pm_stats['article_type']['clinical_trial'] + ctg_facets['article_type']['clinical_trial']
            },
            'phase_i': {
                'pm': pm_stats['article_type']['phase_i'],
                'ctg': ctg_facets['article_type']['phase_i'],
                'total': pm_stats['article_type']['phase_i'] + ctg_facets['article_type']['phase_i']
            },
            'phase_ii': {
                'pm': pm_stats['article_type']['phase_ii'],
                'ctg': ctg_facets['article_type']['phase_ii'],
                'total': pm_stats['article_type']['phase_ii'] + ctg_facets['article_type']['phase_ii']
            },
            'phase_iii': {
                'pm': pm_stats['article_type']['phase_iii'],
                'ctg': ctg_facets['article_type']['phase_iii'],
                'total': pm_stats['article_type']['phase_iii'] + ctg_facets['article_type']['phase_iii']
            },
            'phase_iv': {
                'pm': pm_stats['article_type']['phase_iv'],
                'ctg': ctg_facets['article_type']['phase_iv'],
                'total': pm_stats['article_type']['phase_iv'] + ctg_facets['article_type']['phase_iv']
            },
            'randomized_controlled_trial': {
                'pm': pm_stats['article_type']['randomized_controlled_trial'],
                'ctg': ctg_facets['article_type']['randomized_controlled_trial'],
                'total': pm_stats['article_type']['randomized_controlled_trial'] + ctg_facets['article_type']['randomized_controlled_trial']
            },
            'observational': {
                'pm': pm_stats['article_type']['observational'],
                'ctg': ctg_facets['article_type']['observational'],
                'total': pm_stats['article_type']['observational'] + ctg_facets['article_type']['observational']
            },
            'meta_analysis': {
                'pm': pm_stats['article_type']['meta_analysis'],
                'ctg': 0,
                'total': pm_stats['article_type']['meta_analysis']
            },
            'review': {
                'pm': pm_stats['article_type']['review'],
                'ctg': 0,
                'total': pm_stats['article_type']['review']
            },
            'systematic_review': {
                'pm': pm_stats['article_type']['systematic_review'],
                'ctg': 0,
                'total': pm_stats['article_type']['systematic_review']
            }
        },
        'additional_filters': {
            'species': {
                'humans': {
                    'pm': pm_stats['species']['humans'],
                    'ctg': None,
                    'total': pm_stats['species']['humans']
                },
                'other_animals': {
                    'pm': pm_stats['species']['other_animals'],
                    'ctg': None,
                    'total': pm_stats['species']['other_animals']
                }
            },
            'age': {
                'child_0_18': {
                    'pm': pm_stats['age']['child_0_18'],
                    'ctg': ctg_facets['additional_filters']['age']['child_0_18'],
                    'total': pm_stats['age']['child_0_18'] + ctg_facets['additional_filters']['age']['child_0_18']
                },
                'adult_19_plus': {
                    'pm': pm_stats['age']['adult_19_plus'],
                    'ctg': ctg_facets['additional_filters']['age']['adult_19_plus'],
                    'total': pm_stats['age']['adult_19_plus'] + ctg_facets['additional_filters']['age']['adult_19_plus']
                },
                'aged_65_plus': {
                    'pm': pm_stats['age']['aged_65_plus'],
                    'ctg': ctg_facets['additional_filters']['age']['aged_65_plus'],
                    'total': pm_stats['age']['aged_65_plus'] + ctg_facets['additional_filters']['age']['aged_65_plus']
                }
            }
        },
        'ctg_filters': {
            'has_results': ctg_facets.get('ctg_filters', {}).get('has_results', 0),
            'status': ctg_facets.get('ctg_filters', {}).get('status', {'recruiting': 0, 'completed': 0})
        }
    }
    
    logger.info(f"Calculated unified filter stats: PM={pm_stats['total']}, CTG={ctg_facets['data_source']['clinicaltrials_gov']}")
    return unified


def _calculate_pm_stats(pm_results: List[Dict]) -> Dict[str, Any]:
    """Calculate PubMed-specific statistics from publication_types and MeSH terms"""
    from datetime import datetime
    
    stats = {
        'total': len(pm_results),
        'publication_date': {
            'within_1y': 0,
            'within_5y': 0,
            'within_10y': 0
        },
        'article_type': {
            'clinical_trial': 0,
            'phase_i': 0,
            'phase_ii': 0,
            'phase_iii': 0,
            'phase_iv': 0,
            'randomized_controlled_trial': 0,
            'observational': 0,
            'meta_analysis': 0,
            'review': 0,
            'systematic_review': 0
        },
        'species': {
            'humans': 0,
            'other_animals': 0
        },
        'age': {
            'child_0_18': 0,
            'adult_19_plus': 0,
            'aged_65_plus': 0
        }
    }
    
    current_year = datetime.now().year
    
    for result in pm_results:
        # Publication date - try both 'pubDate' and 'date' fields
        year = _extract_year(result.get('pubDate') or result.get('date', ''))
        if year:
            if current_year - year <= 1:
                stats['publication_date']['within_1y'] += 1
            if current_year - year <= 5:
                stats['publication_date']['within_5y'] += 1
            if current_year - year <= 10:
                stats['publication_date']['within_10y'] += 1
        
        # Article type from publication_types
        pub_types = result.get('publication_types', [])
        if isinstance(pub_types, str):
            pub_types = [pub_types]
        pub_types_lower = [pt.lower() for pt in pub_types]
        
        if any('clinical trial' in pt for pt in pub_types_lower):
            stats['article_type']['clinical_trial'] += 1
            
            # Check for specific phases
            if any('phase i' in pt and 'phase ii' not in pt and 'phase iii' not in pt and 'phase iv' not in pt for pt in pub_types_lower):
                stats['article_type']['phase_i'] += 1
            if any('phase ii' in pt and 'phase iii' not in pt for pt in pub_types_lower):
                stats['article_type']['phase_ii'] += 1
            if any('phase iii' in pt for pt in pub_types_lower):
                stats['article_type']['phase_iii'] += 1
            if any('phase iv' in pt for pt in pub_types_lower):
                stats['article_type']['phase_iv'] += 1
        
        if any('observational study' in pt for pt in pub_types_lower):
            stats['article_type']['observational'] += 1
        if any('meta-analysis' in pt for pt in pub_types_lower):
            stats['article_type']['meta_analysis'] += 1
        if any('randomized controlled trial' in pt for pt in pub_types_lower):
            stats['article_type']['randomized_controlled_trial'] += 1
        if any('review' in pt and 'systematic review' not in pt for pt in pub_types_lower):
            stats['article_type']['review'] += 1
        if any('systematic review' in pt for pt in pub_types_lower):
            stats['article_type']['systematic_review'] += 1
        
        # Extract species and age from MeSH headings
        mesh_headings = result.get('mesh_headings', [])
        if mesh_headings:
            mesh_terms_lower = []
            for mesh in mesh_headings:
                if isinstance(mesh, dict):
                    descriptor = mesh.get('descriptor', '')
                    if descriptor:
                        mesh_terms_lower.append(descriptor.lower())
                elif isinstance(mesh, str):
                    mesh_terms_lower.append(mesh.lower())
            
            # Species detection
            if any('human' in term for term in mesh_terms_lower):
                stats['species']['humans'] += 1
            if any(animal in term for term in mesh_terms_lower 
                   for animal in ['animal', 'mouse', 'mice', 'rat', 'rabbit', 'dog', 'cat', 
                                  'monkey', 'primate', 'rodent', 'swine', 'pig']):
                stats['species']['other_animals'] += 1
            
            # Age detection
            if any(age_term in term for term in mesh_terms_lower 
                   for age_term in ['child', 'infant', 'adolescent', 'pediatric', 'newborn']):
                stats['age']['child_0_18'] += 1
            if any(age_term in term for term in mesh_terms_lower 
                   for age_term in ['adult', 'middle aged', 'young adult']):
                stats['age']['adult_19_plus'] += 1
            if any(age_term in term for term in mesh_terms_lower 
                   for age_term in ['aged', 'elderly', '80 and over']):
                stats['age']['aged_65_plus'] += 1
    
    return stats


def _extract_year(date_str: str) -> Optional[int]:
    """Extract year from date string"""
    if not date_str:
        return None
    match = re.search(r'\b(19|20)\d{2}\b', str(date_str))
    if match:
        return int(match.group(0))
    return None


def apply_filters(results: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    """
    Apply filters to results based on filter criteria.
    
    Args:
        results: List of result dictionaries
        filters: Filter criteria from frontend
        
    Returns:
        Filtered list of results
    """
    if not filters:
        return results
    
    filtered = []
    for result in results:
        if _matches_filters(result, filters):
            filtered.append(result)
    
    return filtered


def _matches_filters(result: Dict, filters: Dict[str, Any]) -> bool:
    """
    Check if a result matches the filter criteria.
    Simplified version that works with available data.
    """
    source_type = result.get('type', 'UNKNOWN')
    
    # Source type filter
    source_filter = filters.get('source_type', [])
    if source_filter and source_type not in source_filter:
        return False
    
    # Article type filter
    article_filter = filters.get('article_type', [])
    if article_filter:
        if source_type == 'PM':
            pub_types = result.get('publication_types', [])
            if isinstance(pub_types, str):
                pub_types = [pub_types]
            pub_types_lower = [pt.lower() for pt in pub_types]
            
            matches = False
            if 'clinical_trial' in article_filter and any('clinical trial' in pt for pt in pub_types_lower):
                matches = True
            if 'observational' in article_filter and any('Observational Study' in pt for pt in pub_types_lower):
                matches = True
            if 'meta_analysis' in article_filter and any('meta-analysis' in pt for pt in pub_types_lower):
                matches = True
            if 'randomized_controlled_trial' in article_filter and any('randomized controlled trial' in pt for pt in pub_types_lower):
                matches = True
            if 'review' in article_filter and any('review' in pt for pt in pub_types_lower):
                matches = True
            if 'systematic_review' in article_filter and any('systematic review' in pt for pt in pub_types_lower):
                matches = True
            
            if not matches:
                return False
                
        elif source_type == 'CTG':
            study_type = result.get('study_type', '').upper()
            print(f"[FilterStats] CTG study type: {study_type}")
            matches = False
            
            # if 'clinical_trial' in article_filter and study_type == 'INTERVENTIONAL':
            if 'clinical_trial' in article_filter:
                matches = True

            if 'observational' in article_filter and study_type == 'OBSERVATIONAL':
                matches = True

            # Phase filtering for CTG
            phases = result.get('phase', [])
            if isinstance(phases, str):
                phases = [phases]
            phases_upper = [p.upper().replace(' ', '_') for p in phases]
            
            if 'phase_i' in article_filter and any('PHASE1' in p or 'EARLY_PHASE1' in p for p in phases_upper):
                matches = True
            if 'phase_ii' in article_filter and any('PHASE2' in p for p in phases_upper):
                matches = True
            if 'phase_iii' in article_filter and any('PHASE3' in p for p in phases_upper):
                matches = True
            if 'phase_iv' in article_filter and any('PHASE4' in p for p in phases_upper):
                matches = True
            
            if not matches:
                return False
    
    # Publication date filter
    pub_date = filters.get('publication_date', {})
    if pub_date:
        year = _extract_year(result.get('date', ''))
        
        if year:
            from_year = pub_date.get('from_year')
            to_year = pub_date.get('to_year')
            
            if from_year and year < from_year:
                return False
            if to_year and year > to_year:
                return False
    
    return True
