"""
PubMed filter query builder.
Converts UI filter selections to PubMed API filter syntax.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PubMedFilterBuilder:
    """Build PubMed filter query strings from filter selections"""
    
    # Fixed filter that is always applied (PMC Open Access)
    FIXED_FILTER = 'pubmed pmc open access[Filter]'
    
    # PubMed filter mappings - separated into Phase and Study Type
    PHASE_FILTERS = {
        'phase_i': 'clinicaltrialphasei[Filter]',
        'phase_ii': 'clinicaltrialphaseii[Filter]',
        'phase_iii': 'clinicaltrialphaseiii[Filter]',
        'phase_iv': 'clinicaltrialphaseiv[Filter]',
    }
    
    STUDY_TYPE_FILTERS = {
        'clinical_trial': 'clinicaltrial[Filter]',
        'randomized_controlled_trial': 'randomizedcontrolledtrial[Filter]',
        'observational': 'observationalstudy[Filter]',
    }
    
    # Other article types (PubMed-only)
    OTHER_ARTICLE_TYPE_FILTERS = {
        'meta_analysis': 'meta-analysis[Filter]',
        'review': 'review[Filter]',
        'systematic_review': 'systematicreview[Filter]',
    }
    
    SPECIES_FILTERS = {
        'humans': 'humans[Filter]',
        'other_animals': 'animal[Filter]',
    }
    
    AGE_FILTERS = {
        'child_0_18': 'allchild[Filter]',
        'adult_19_plus': 'alladult[Filter]',
        'aged_65_plus': 'aged[Filter]',
    }
    
    @staticmethod
    def build_filter_query(filters: Dict[str, Any]) -> str:
        """
        Build PubMed filter query from filter selections.
        Phase filters are OR'd within their category.
        Study Type filters are OR'd within their category.
        Categories are AND'd together.
        
        Args:
            filters: Dictionary with filter selections
            
        Returns:
            PubMed filter query string (to be appended to base query with AND)
        """
        filter_parts = []
        
        # PMC Open Access filter (only apply if explicitly True)
        pmc_open_access = filters.get('pmc_open_access', False)
        if pmc_open_access is True:
            filter_parts.append(PubMedFilterBuilder.FIXED_FILTER)
        
        # Article Type filters - now separated into Phase and Study Type
        article_types = filters.get('article_type', [])
        if article_types:
            # Phase filters (OR within category)
            phase_filters = [
                PubMedFilterBuilder.PHASE_FILTERS.get(at)
                for at in article_types
                if at in PubMedFilterBuilder.PHASE_FILTERS
            ]
            if phase_filters:
                filter_parts.append(f"({' OR '.join(phase_filters)})")
            
            # Study Type filters (OR within category)
            study_type_filters = [
                PubMedFilterBuilder.STUDY_TYPE_FILTERS.get(at)
                for at in article_types
                if at in PubMedFilterBuilder.STUDY_TYPE_FILTERS
            ]
            if study_type_filters:
                filter_parts.append(f"({' OR '.join(study_type_filters)})")
            
            # Other article types (OR within category)
            other_filters = [
                PubMedFilterBuilder.OTHER_ARTICLE_TYPE_FILTERS.get(at)
                for at in article_types
                if at in PubMedFilterBuilder.OTHER_ARTICLE_TYPE_FILTERS
            ]
            if other_filters:
                filter_parts.append(f"({' OR '.join(other_filters)})")
        
        # Species filters (OR within category)
        species = filters.get('species', [])
        if species:
            species_filters = [
                PubMedFilterBuilder.SPECIES_FILTERS.get(s)
                for s in species
                if s in PubMedFilterBuilder.SPECIES_FILTERS
            ]
            if species_filters:
                filter_parts.append(f"({' OR '.join(species_filters)})")
        
        # Age filters (OR within category)
        ages = filters.get('age', [])
        if ages:
            age_filters = [
                PubMedFilterBuilder.AGE_FILTERS.get(a)
                for a in ages
                if a in PubMedFilterBuilder.AGE_FILTERS
            ]
            if age_filters:
                filter_parts.append(f"({' OR '.join(age_filters)})")
        
        # Publication date filter
        pub_date = filters.get('publication_date', {})
        if pub_date and isinstance(pub_date, dict):
            date_filter = PubMedFilterBuilder._build_date_filter(pub_date)
            if date_filter:
                filter_parts.append(date_filter)
        
        # Combine all filters with AND
        # Note: PMC Open Access filter is optional
        if filter_parts:
            return ' AND '.join(filter_parts)
        return ''
    
    @staticmethod
    def _build_date_filter(pub_date: Dict[str, Any]) -> Optional[str]:
        """Build publication date filter"""
        date_type = pub_date.get('type')
        
        if date_type == 'custom':
            # Support both from_year/to_year and from/to formats
            from_year = pub_date.get('from_year') or pub_date.get('from')
            to_year = pub_date.get('to_year') or pub_date.get('to')
            
            logger.info(f"[PubMedFilter] Custom date filter - from: {from_year}, to: {to_year}")
            
            if from_year and to_year:
                return f"({from_year}/1/1:{to_year}/12/31[pdat])"
            elif from_year:
                current_year = datetime.now().year
                return f"({from_year}/1/1:{current_year}/12/31[pdat])"
            elif to_year:
                # If only to_year is specified, use from beginning
                return f"(1900/1/1:{to_year}/12/31[pdat])"
        
        elif date_type == '1_year':
            current_year = datetime.now().year
            return f"({current_year}/1/1:{current_year}/12/31[pdat])"
        
        elif date_type == '5_years':
            current_year = datetime.now().year
            from_year = current_year - 5
            return f"({from_year}/1/1:{current_year}/12/31[pdat])"
        
        elif date_type == '10_years':
            current_year = datetime.now().year
            from_year = current_year - 10
            return f"({from_year}/1/1:{current_year}/12/31[pdat])"
        
        return None
    
    @staticmethod
    def append_filters_to_query(base_query: str, filters: Dict[str, Any]) -> str:
        """
        Append filter query to base search query.
        
        Args:
            base_query: Original search query
            filters: Filter selections
            
        Returns:
            Combined query with filters
        """
        filter_query = PubMedFilterBuilder.build_filter_query(filters)
        
        if filter_query:
            # Wrap base query in parentheses if it contains operators
            if ' AND ' in base_query or ' OR ' in base_query:
                combined = f"({base_query}) AND {filter_query}"
            else:
                combined = f"{base_query} AND {filter_query}"
            
            logger.info(f"Combined query with filters: {combined}")
            return combined
        
        return base_query
