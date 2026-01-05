"""
CTG filter builder for query.term AREA filters.
Converts UI filter selections to CTG API v2 AREA format.
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CTGFilterBuilder:
    """Build CTG query.term AREA filters from filter selections"""
    
    @staticmethod
    def build_study_type_filter(filters: Dict[str, Any]) -> Optional[str]:
        """
        Build study type filter using AREA syntax.
        
        Examples:
        - RCT only: AREA[protocolSection.designModule.studyType] Interventional AND AREA[protocolSection.designModule.designInfo.allocation] Randomized
        - Observational only: AREA[protocolSection.designModule.studyType] Observational
        - Both: AREA[protocolSection.designModule.studyType] Interventional OR AREA[protocolSection.designModule.studyType] Observational
        
        Args:
            filters: Dictionary with filter selections
            
        Returns:
            AREA filter string or None
        """
        article_types = filters.get('article_type', [])
        
        has_rct = 'randomized_controlled_trial' in article_types
        has_interventional = 'interventional' in article_types
        has_observational = 'observational' in article_types
        
        # RCT implies interventional
        is_interventional = has_rct or has_interventional
        
        if is_interventional and has_observational:
            # Both selected
            return "AREA[protocolSection.designModule.studyType] Interventional OR AREA[protocolSection.designModule.studyType] Observational"
        elif is_interventional:
            # Only interventional/RCT
            if has_rct:
                # Specific RCT requirement
                return "AREA[protocolSection.designModule.studyType] Interventional AND AREA[protocolSection.designModule.designInfo.allocation] Randomized"
            else:
                # General interventional
                return "AREA[protocolSection.designModule.studyType] Interventional"
        elif has_observational:
            # Only observational
            return "AREA[protocolSection.designModule.studyType] Observational"
        
        return None
    
    @staticmethod
    def build_age_filter(filters: Dict[str, Any]) -> Optional[str]:
        """
        Build age filter using AREA syntax.
        Each age must be in a separate AREA clause joined with OR.
        Format: AREA[protocolSection.eligibilityModule.stdAges] CHILD OR AREA[...] ADULT
        """
        ages = filters.get('age', [])
        if not ages:
            return None
        
        age_clauses = []
        if 'child_0_18' in ages:
            age_clauses.append('AREA[protocolSection.eligibilityModule.stdAges] CHILD')
        if 'adult_19_plus' in ages:
            age_clauses.append('AREA[protocolSection.eligibilityModule.stdAges] ADULT')
        if 'aged_65_plus' in ages:
            age_clauses.append('AREA[protocolSection.eligibilityModule.stdAges] OLDER_ADULT')
        
        if age_clauses:
            return " OR ".join(age_clauses)
        
        return None
    
    @staticmethod
    def build_phase_filter(filters: Dict[str, Any]) -> Optional[str]:
        """
        Build phase filter using AREA syntax.
        Each phase must be in a separate AREA clause joined with OR.
        Format: AREA[protocolSection.designModule.phases] PHASE1 OR AREA[protocolSection.designModule.phases] PHASE2
        """
        article_types = filters.get('article_type', [])
        
        phase_map = {
            'phase_i': 'PHASE1',
            'phase_ii': 'PHASE2',
            'phase_iii': 'PHASE3',
            'phase_iv': 'PHASE4',
        }
        
        phase_clauses = []
        for at in article_types:
            if at in phase_map:
                phase_clauses.append(f"AREA[protocolSection.designModule.phases] {phase_map[at]}")
        
        if phase_clauses:
            return " OR ".join(phase_clauses)
        
        return None
    
    @staticmethod
    def build_combined_filter(filters: Dict[str, Any]) -> Optional[str]:
        """
        Build combined filter query by joining all AREA filters with AND.
        Phase and Study Type are treated as separate categories.
        Within each category, filters are OR'd together.
        Between categories, filters are AND'd together.
        
        Args:
            filters: Dictionary with filter selections
            
        Returns:
            Combined AREA filter string or None
        """
        filter_parts = []
        
        # Study type filter (Clinical Trial, RCT, Observational)
        study_type_filter = CTGFilterBuilder.build_study_type_filter(filters)
        if study_type_filter:
            filter_parts.append(f"({study_type_filter})")
        
        # Phase filter (Phase I, II, III, IV) - separate category
        phase_filter = CTGFilterBuilder.build_phase_filter(filters)
        if phase_filter:
            # Wrap in parentheses if multiple phases (contains OR)
            if ' OR ' in phase_filter:
                filter_parts.append(f"({phase_filter})")
            else:
                filter_parts.append(phase_filter)
        
        # Age filter (wrap in parentheses if it contains OR)
        age_filter = CTGFilterBuilder.build_age_filter(filters)
        if age_filter:
            # Wrap in parentheses if multiple ages (contains OR)
            if ' OR ' in age_filter:
                filter_parts.append(f"({age_filter})")
            else:
                filter_parts.append(age_filter)
        
        # Has Results filter
        has_results_filter = CTGFilterBuilder.build_has_results_filter(filters)
        if has_results_filter:
            filter_parts.append(has_results_filter)
        
        # Date filter using AREA syntax
        date_filter = CTGFilterBuilder.build_last_update_date_area_filter(filters.get('publication_date'))
        if date_filter:
            filter_parts.append(date_filter)
        
        if filter_parts:
            combined = ' AND '.join(filter_parts)
            logger.info(f"Built CTG AREA filter: {combined}")
            return combined
        
        return None
    
    @staticmethod
    def build_has_results_filter(filters: Dict[str, Any]) -> Optional[str]:
        """
        Build has results filter using AREA syntax.
        Format: AREA[hasResults]true
        
        Args:
            filters: Dictionary with filter selections
            
        Returns:
            AREA filter string or None
        """
        has_results = filters.get('ctg_has_results', False)
        if has_results:
            return 'AREA[hasResults]true'
        return None
    
    @staticmethod
    def build_status_param(filters: Dict[str, Any]) -> Optional[str]:
        """
        Build status parameter for CTG API.
        Format: RECRUITING|COMPLETED (pipe-separated for multiple)
        
        Args:
            filters: Dictionary with filter selections
            
        Returns:
            Status parameter string or None
        """
        status_list = filters.get('ctg_status', [])
        if status_list:
            return '|'.join(status_list)
        return None
    
    @staticmethod
    def build_last_update_date_area_filter(pub_date: Dict[str, Any]) -> Optional[str]:
        """
        Build LastUpdatePostDate AREA filter using RANGE syntax.
        Format: AREA[LastUpdatePostDate]RANGE[from_date,to_date]
        
        Example: AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX]
        
        Args:
            pub_date: Publication date filter dict
            
        Returns:
            AREA filter string or None
        """
        if not pub_date:
            return None
        
        from datetime import datetime
        
        date_type = pub_date.get('type')
        
        if date_type == 'custom':
            from_year = pub_date.get('from_year') or pub_date.get('from')
            to_year = pub_date.get('to_year') or pub_date.get('to')
            
            if from_year and to_year:
                return f"AREA[LastUpdatePostDate]RANGE[{from_year}-01-01,{to_year}-12-31]"
            elif from_year:
                return f"AREA[LastUpdatePostDate]RANGE[{from_year}-01-01,MAX]"
            elif to_year:
                return f"AREA[LastUpdatePostDate]RANGE[MIN,{to_year}-12-31]"

        elif date_type == '1_year':
            current_year = datetime.now().year
            return f"AREA[LastUpdatePostDate]RANGE[{current_year}-01-01,MAX]"

        elif date_type == '5_years':
            current_year = datetime.now().year
            from_year = current_year - 5
            return f"AREA[LastUpdatePostDate]RANGE[{from_year}-01-01,MAX]"

        elif date_type == '10_years':
            current_year = datetime.now().year
            from_year = current_year - 10
            return f"AREA[LastUpdatePostDate]RANGE[{from_year}-01-01,MAX]"

        return None
    
    @staticmethod
    def build_study_completion_date_filter(pub_date: Dict[str, Any]) -> Optional[str]:
        """
        DEPRECATED: Use build_last_update_date_area_filter instead.
        This function is kept for backward compatibility.
        
        Build lastUpdatePostDate parameter (not aggFilters).
        Using lastUpdatePostDate instead of CompletionDate because:
        1. Many studies are ongoing and don't have CompletionDate yet
        2. CompletionDate doesn't correlate well with publication date
        3. lastUpdatePostDate better represents when a study was registered/active
        
        Format: YYYY-MM-DD_YYYY-MM-DD (date range)
        
        Args:
            pub_date: Publication date filter dict
            
        Returns:
            lastUpdatePostDate parameter value or None
        """
        if not pub_date:
            return None
        
        from datetime import datetime
        
        date_type = pub_date.get('type')
        
        if date_type == 'custom':
            from_year = pub_date.get('from_year') or pub_date.get('from')
            to_year = pub_date.get('to_year') or pub_date.get('to')
            
            if from_year and to_year:
                return f"{from_year}-01-01_{to_year}-12-31"
            elif from_year:
                current_year = datetime.now().year
                return f"{from_year}-01-01_{current_year}-12-31"
            elif to_year:
                return f"1900-01-01_{to_year}-12-31"

        elif date_type == '1_year':
            current_year = datetime.now().year
            return f"{current_year}-01-01_{current_year}-12-31"

        elif date_type == '5_years':
            current_year = datetime.now().year
            from_year = current_year - 5
            return f"{from_year}-01-01_{current_year}-12-31"

        elif date_type == '10_years':
            current_year = datetime.now().year
            from_year = current_year - 10
            return f"{from_year}-01-01_{current_year}-12-31"

        return None
    
    @staticmethod
    def build_study_completion_date(pub_date: Dict[str, Any]) -> str:
        """
        DEPRECATED: Use build_study_completion_date_filter instead.
        Build studyComp parameter from publication_date filter.
        Format: YYYY-MM-DD_YYYY-MM-DD
        
        Args:
            pub_date: Publication date filter dict
            
        Returns:
            studyComp string or empty string
        """
        if not pub_date:
            return ""
        
        from datetime import datetime
        
        date_type = pub_date.get('type')
        
        if date_type == 'custom':
            from_year = pub_date.get('from_year') or pub_date.get('from')
            to_year = pub_date.get('to_year') or pub_date.get('to')
            
            if from_year and to_year:
                return f"{from_year}-01-01_{to_year}-12-31"
            elif from_year:
                current_year = datetime.now().year
                return f"{from_year}-01-01_{current_year}-12-31"
            elif to_year:
                return f"1900-01-01_{to_year}-12-31"
        
        elif date_type == '1_year':
            current_year = datetime.now().year
            return f"{current_year}-01-01_{current_year}-12-31"
        
        elif date_type == '5_years':
            current_year = datetime.now().year
            from_year = current_year - 5
            return f"{from_year}-01-01_{current_year}-12-31"
        
        elif date_type == '10_years':
            current_year = datetime.now().year
            from_year = current_year - 10
            return f"{from_year}-01-01_{current_year}-12-31"
        
        return ""
