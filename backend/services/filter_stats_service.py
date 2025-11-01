from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ResultClassifier:
    """
    Unified module for result classification and filtering.
    Ensures consistency by using the same logic for statistics calculation and filtering.
    """
    
    @staticmethod
    def classify_result(result: Dict) -> Dict[str, Any]:
        """
        Extracts all classification information for a single result.
        Commonly used for both statistics calculation and filtering.
        """
        classification = {
            'source_type': result.get('type', 'UNKNOWN'),
            'study_type': 'NA',
            'phase': 'NA',
            'design_allocation': 'NA',
            'observational_model': 'NA',
            'year': None
        }
        
        try:
            # Classification by Source Type
            if result['type'] == 'PM':
                # Classification for PM results
                study_type = result.get('_meta', {}).get('study_type') or result.get('study_type', 'NA')
                if study_type == 'UNKNOWN' or not study_type:
                    study_type = 'NA'
                classification['study_type'] = study_type
                
                # For INTERVENTIONAL type
                if study_type == 'INTERVENTIONAL':
                    # Extract Phase
                    phase = result.get('_meta', {}).get('phase') or result.get('phase', 'NA')
                    if phase == 'UNKNOWN' or not phase:
                        phase = 'NA'
                    classification['phase'] = phase
                    
                    # Extract Design Allocation
                    design_allocation = result.get('design_allocation', 'NA')
                    if not design_allocation or design_allocation == '':
                        design_allocation = 'NA'
                    classification['design_allocation'] = design_allocation
                
                # For OBSERVATIONAL type
                elif study_type == 'OBSERVATIONAL':
                    # Extract Observational Model
                    obs_model = result.get('observational_model', 'NA')
                    if not obs_model or obs_model == '':
                        obs_model = 'NA'
                    classification['observational_model'] = obs_model
                
                # Extract year
                classification['year'] = ResultClassifier._extract_year_from_pm(result)
                
            elif result['type'] == 'CTG':
                # Classification for CTG results
                study_type = ResultClassifier._normalize_ctg_study_type(result.get('study_type'))
                classification['study_type'] = study_type
                
                # For INTERVENTIONAL type
                if study_type == 'INTERVENTIONAL':
                    # Extract Phase (CTG supports multiple phases, use the first one)
                    phases = ResultClassifier._normalize_ctg_phases(result.get('phase'))
                    classification['phase'] = list(phases)[0] if phases else 'NA'
                    
                    # Extract Design Allocation
                    design_allocation = result.get('design_allocation', '')
                    normalized_allocation = ResultClassifier._normalize_design_allocation(design_allocation)
                    classification['design_allocation'] = normalized_allocation
                
                # For OBSERVATIONAL type
                elif study_type == 'OBSERVATIONAL':
                    # Extract Observational Model
                    obs_model = result.get('observational_model', '')
                    normalized_model = ResultClassifier._normalize_observational_model(obs_model)
                    classification['observational_model'] = normalized_model
                
                # Extract year
                classification['year'] = ResultClassifier._extract_year_from_ctg(result)
                
        except Exception as e:
            logger.warning(f"Error classifying result: {e}")
            # Retain default values in case of errors
            
        return classification
    
    @staticmethod
    def _normalize_ctg_study_type(study_type: Optional[str]) -> str:
        """Standardize CTG study type values."""
        if not study_type or study_type.strip() == '':
            return 'NA'
        
        study_type_upper = study_type.upper()
        
        if 'INTERVENTIONAL' in study_type_upper:
            return 'INTERVENTIONAL'
        elif 'OBSERVATIONAL' in study_type_upper:
            return 'OBSERVATIONAL'
        elif 'EXPANDED' in study_type_upper and 'ACCESS' in study_type_upper:
            return 'EXPANDED_ACCESS'
        else:
            return 'NA'
    
    @staticmethod
    def _normalize_ctg_phases(phase: Optional[str]) -> Set[str]:
        """Standardize CTG phase values."""
        if not phase or phase.strip() == '':
            return {'NA'}
        
        phase_upper = phase.upper().replace(' ', '')
        normalized = ResultClassifier._normalize_single_ctg_phase(phase_upper)
        if normalized:
            return {normalized}
        
        return {'NA'}
    
    @staticmethod
    def _normalize_single_ctg_phase(phase: str) -> Optional[str]:
        """Standardize a single CTG phase value."""
        phase_mapping = {
            'PHASE1': 'PHASE1',
            'PHASE2': 'PHASE2',
            'PHASE3': 'PHASE3',
            'PHASE4': 'PHASE4',
            'EARLYPHASE1': 'EARLY_PHASE1',
            'EARLY_PHASE1': 'EARLY_PHASE1',
            'NOT_APPLICABLE': 'NA',
            'NA': 'NA',
            'UNKNOWN': 'NA'
        }
        
        if phase in phase_mapping:
            return phase_mapping[phase]
        
        for key, value in phase_mapping.items():
            if key in phase:
                return value
        
        return 'NA'
    
    @staticmethod
    def _normalize_design_allocation(allocation: Optional[str]) -> str:
        """Standardize design allocation values."""
        if not allocation or allocation.strip() == '':
            return 'NA'
        
        allocation_upper = allocation.upper()
        
        if 'RANDOMIZED' in allocation_upper and 'NON' not in allocation_upper:
            return 'RANDOMIZED'
        elif 'NON' in allocation_upper and 'RANDOMIZED' in allocation_upper:
            return 'NON_RANDOMIZED'
        else:
            return 'NA'
    
    @staticmethod
    def _normalize_observational_model(model: Optional[str]) -> str:
        """Standardize observational model values."""
        if not model or model.strip() == '':
            return 'NA'
        
        model_upper = model.upper()
        
        if 'COHORT' in model_upper:
            return 'COHORT'
        elif 'CASE' in model_upper and 'CONTROL' in model_upper:
            return 'CASE_CONTROL'
        elif 'CASE' in model_upper and 'ONLY' in model_upper:
            return 'CASE_ONLY'
        elif 'CASE' in model_upper and 'CROSSOVER' in model_upper:
            return 'CASE_CROSSOVER'
        elif 'CROSS' in model_upper and 'SECTIONAL' in model_upper:
            return 'CROSS_SECTIONAL'
        elif 'TIME' in model_upper and 'SERIES' in model_upper:
            return 'TIME_SERIES'
        elif 'ECOLOGIC' in model_upper or 'COMMUNITY' in model_upper:
            return 'ECOLOGIC_OR_COMMUNITY_STUDY'
        elif 'FAMILY' in model_upper and 'BASED' in model_upper:
            return 'FAMILY_BASED'
        elif 'OTHER' in model_upper:
            return 'OTHER'
        else:
            return 'NA'
    
    @staticmethod
    def _extract_year_from_pm(result: Dict) -> Optional[int]:
        """Extract year from PubMed results."""
        if result.get('pub_year'):
            return result['pub_year']
        
        pub_date = result.get('pubDate', '')
        if pub_date:
            try:
                if len(pub_date) >= 4:
                    year_str = pub_date[:4]
                    if year_str.isdigit():
                        return int(year_str)
            except:
                pass
        
        article_date = result.get('article_date', '')
        if article_date:
            try:
                if len(article_date) >= 4:
                    year_str = article_date[:4]
                    if year_str.isdigit():
                        return int(year_str)
            except:
                pass
        
        return None
    
    @staticmethod
    def _extract_year_from_ctg(result: Dict) -> Optional[int]:
        """Extract year from CTG results (prioritize completion date)."""
        completion_date = result.get('completion_date')
        if completion_date:
            try:
                date_obj = datetime.strptime(str(completion_date), '%Y-%m-%d')
                return date_obj.year
            except:
                try:
                    if len(str(completion_date)) >= 4:
                        year_str = str(completion_date)[:4]
                        if year_str.isdigit():
                            return int(year_str)
                except:
                    pass
        
        primary_completion_date = result.get('primary_completion_date')
        if primary_completion_date:
            try:
                date_obj = datetime.strptime(str(primary_completion_date), '%Y-%m-%d')
                return date_obj.year
            except:
                try:
                    if len(str(primary_completion_date)) >= 4:
                        year_str = str(primary_completion_date)[:4]
                        if year_str.isdigit():
                            return int(year_str)
                except:
                    pass
        
        start_date = result.get('start_date')
        if start_date:
            try:
                date_obj = datetime.strptime(str(start_date), '%Y-%m-%d')
                return date_obj.year
            except:
                try:
                    if len(str(start_date)) >= 4:
                        year_str = str(start_date)[:4]
                        if year_str.isdigit():
                            return int(year_str)
                except:
                    pass
        
        return None
    
    @staticmethod
    def matches_filters(classification: Dict[str, Any], filters: Dict) -> bool:
        """
        Check if the classification result matches the filter conditions.
        """
        # Source Type filter
        if filters.get('source_type'):
            if classification['source_type'] not in filters['source_type']:
                return False
        
        # Study Type filter
        if filters.get('study_type'):
            if classification['study_type'] not in filters['study_type']:
                return False
        
        # Filters specific to INTERVENTIONAL type
        if classification['study_type'] == 'INTERVENTIONAL':
            # Phase filter
            if filters.get('phase'):
                if classification['phase'] not in filters['phase']:
                    return False
            
            # Design Allocation filter
            if filters.get('design_allocation'):
                if classification['design_allocation'] not in filters['design_allocation']:
                    return False
        
        # Filters specific to OBSERVATIONAL type
        elif classification['study_type'] == 'OBSERVATIONAL':
            # Observational Model filter
            if filters.get('observational_model'):
                if classification['observational_model'] not in filters['observational_model']:
                    return False
        
        # Year filter
        if filters.get('year_range'):
            year = classification['year']
            if year:
                year_from = filters['year_range'].get('from', 0)
                year_to = filters['year_range'].get('to', 9999)
                
                if year < year_from or year > year_to:
                    return False
            # If year is None, treat it as UNKNOWN and pass
        
        return True

def calculate_filter_stats(pm_results: List[Dict], ctg_results: List[Dict]) -> Dict[str, Any]:
    """
    Calculate statistical information for filtering from search results.
    Ensures the same logic as filtering by using the integrated classification module.
    """
    stats = {
        "pm": {
            "total": len(pm_results),
            "phase": defaultdict(int),
            "study_type": defaultdict(int),
            "year": defaultdict(int),
            "extraction_sources": defaultdict(lambda: defaultdict(int)),
            "design_allocation": defaultdict(int),
            "observational_model": defaultdict(int)
        },
        "ctg": {
            "total": len(ctg_results),
            "phase": defaultdict(int),
            "study_type": defaultdict(int),
            "year": defaultdict(int),
            "design_allocation": defaultdict(int),
            "observational_model": defaultdict(int)
        }
    }
    
    # PubMed statistics aggregation - using integrated classification module
    for result in pm_results:
        try:
            classification = ResultClassifier.classify_result(result)
            
            # Study Type aggregation
            stats['pm']['study_type'][classification['study_type']] += 1
            
            # For INTERVENTIONAL
            if classification['study_type'] == 'INTERVENTIONAL':
                # Phase aggregation
                stats['pm']['phase'][classification['phase']] += 1
                
                # Log extraction source (for PM only)
                extraction_source = result.get('_meta', {}).get('phase_source', 'not_found')
                stats['pm']['extraction_sources'][classification['phase']][extraction_source] += 1
                
                # Design Allocation aggregation
                stats['pm']['design_allocation'][classification['design_allocation']] += 1
            
            # For OBSERVATIONAL
            elif classification['study_type'] == 'OBSERVATIONAL':
                # Observational Model aggregation
                stats['pm']['observational_model'][classification['observational_model']] += 1
            
            # Aggregate year
            if classification['year']:
                stats['pm']['year'][str(classification['year'])] += 1
            else:
                stats['pm']['year']['UNKNOWN'] += 1
                
        except Exception as e:
            logger.warning(f"Error processing PM result for stats: {e}")
            # Aggregate default values in case of errors
            stats['pm']['study_type']['NA'] += 1
    
    # CTG statistics aggregation - using integrated classification module
    for result in ctg_results:
        try:
            classification = ResultClassifier.classify_result(result)
            
            # Study Type aggregation
            stats['ctg']['study_type'][classification['study_type']] += 1
            
            # For INTERVENTIONAL
            if classification['study_type'] == 'INTERVENTIONAL':
                # Phase aggregation (CTG supports multiple phases, aggregate all phases)
                phases = ResultClassifier._normalize_ctg_phases(result.get('phase'))
                for phase in phases:
                    stats['ctg']['phase'][phase] += 1
                
                # Design Allocation aggregation
                stats['ctg']['design_allocation'][classification['design_allocation']] += 1
            
            # For OBSERVATIONAL
            elif classification['study_type'] == 'OBSERVATIONAL':
                # Observational Model aggregation
                stats['ctg']['observational_model'][classification['observational_model']] += 1
            
            # Aggregate year
            if classification['year']:
                stats['ctg']['year'][str(classification['year'])] += 1
            else:
                stats['ctg']['year']['UNKNOWN'] += 1
                
        except Exception as e:
            logger.warning(f"Error processing CTG result for stats: {e}")
            # Aggregate default values in case of errors
            stats['ctg']['study_type']['NA'] += 1
    
    # Convert defaultdict to regular dict
    return {
        "pm": {
            "total": stats['pm']['total'],
            "phase": dict(stats['pm']['phase']),
            "study_type": dict(stats['pm']['study_type']),
            "year": dict(stats['pm']['year']),
            "extraction_sources": {k: dict(v) for k, v in stats['pm']['extraction_sources'].items()},
            "design_allocation": dict(stats['pm']['design_allocation']),
            "observational_model": dict(stats['pm']['observational_model'])
        },
        "ctg": {
            "total": stats['ctg']['total'],
            "phase": dict(stats['ctg']['phase']),
            "study_type": dict(stats['ctg']['study_type']),
            "year": dict(stats['ctg']['year']),
            "design_allocation": dict(stats['ctg']['design_allocation']),
            "observational_model": dict(stats['ctg']['observational_model'])
        }
    }

def apply_filter_stats_to_results(all_results: List[Dict], filters: Dict) -> List[Dict]:
    """
    Filter results based on statistical information.
    Ensures the same logic as statistics calculation by using the integrated classification module.
    """
    
    # Check if all filters are inclusive of all possible values
    def _is_filter_all_inclusive(filter_values, all_possible_values):
        if not filter_values:
            return True
        return set(filter_values) >= set(all_possible_values)
    
    # Define all possible values for each filter
    ALL_PHASES = ['NA', 'EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4']
    ALL_STUDY_TYPES = ['INTERVENTIONAL', 'OBSERVATIONAL', 'EXPANDED_ACCESS', 'NA']
    ALL_DESIGN_ALLOCATIONS = ['RANDOMIZED', 'NON_RANDOMIZED', 'NA']
    ALL_OBSERVATIONAL_MODELS = ['COHORT', 'CASE_CONTROL', 'CASE_ONLY', 'CASE_CROSSOVER', 
                               'ECOLOGIC_OR_COMMUNITY_STUDY', 'FAMILY_BASED', 'OTHER', 
                               'CROSS_SECTIONAL', 'TIME_SERIES', 'NA']
    ALL_SOURCE_TYPES = ['PM', 'CTG']
    
    # Check if all filters are inclusive
    is_all_inclusive = (
        _is_filter_all_inclusive(filters.get('phase'), ALL_PHASES) and
        _is_filter_all_inclusive(filters.get('study_type'), ALL_STUDY_TYPES) and
        _is_filter_all_inclusive(filters.get('design_allocation'), ALL_DESIGN_ALLOCATIONS) and
        _is_filter_all_inclusive(filters.get('observational_model'), ALL_OBSERVATIONAL_MODELS) and
        _is_filter_all_inclusive(filters.get('source_type'), ALL_SOURCE_TYPES) and
        not filters.get('year_range')
    )
    
    # If all filters are inclusive, return original results without filtering
    if is_all_inclusive:
        logger.info("All filters are inclusive, returning original results without filtering")
        return all_results
    
    logger.info(f"Applying filters to {len(all_results)} results")
    filtered_results = []
    
    for result in all_results:
        try:
            
            # Extract classification information
            classification = ResultClassifier.classify_result(result)
            
            # Check if the classification matches the filter conditions
            if ResultClassifier.matches_filters(classification, filters):
                filtered_results.append(result)
                
        except Exception as e:
            logger.warning(f"Error filtering result: {e}")
            # Exclude results with errors
            continue
    
    logger.info(f"Filtering completed: {len(filtered_results)} results from {len(all_results)} original results")
    return filtered_results


# Legacy functions for backward compatibility (deprecated)
def normalize_ctg_phases(phase: Optional[str]) -> Set[str]:
    """Standardize CTG phase values (deprecated: use ResultClassifier instead)."""
    return ResultClassifier._normalize_ctg_phases(phase)

def normalize_single_ctg_phase(phase: str) -> Optional[str]:
    """Standardize a single CTG phase value (deprecated: use ResultClassifier instead)."""
    return ResultClassifier._normalize_single_ctg_phase(phase)

def normalize_ctg_study_type(study_type: Optional[str]) -> str:
    """Standardize CTG study type values (deprecated: use ResultClassifier instead)."""
    return ResultClassifier._normalize_ctg_study_type(study_type)

def normalize_design_allocation(allocation: Optional[str]) -> str:
    """Standardize design allocation values (deprecated: use ResultClassifier instead)."""
    return ResultClassifier._normalize_design_allocation(allocation)

def normalize_observational_model(model: Optional[str]) -> str:
    """Standardize observational model values (deprecated: use ResultClassifier instead)."""
    return ResultClassifier._normalize_observational_model(model)

def extract_year_from_pm(result: Dict) -> Optional[int]:
    """Extract year from PubMed results (deprecated: use ResultClassifier instead)."""
    return ResultClassifier._extract_year_from_pm(result)

def extract_year_from_ctg(result: Dict) -> Optional[int]:
    """Extract year from CTG results (deprecated: use ResultClassifier instead)."""
    return ResultClassifier._extract_year_from_ctg(result)