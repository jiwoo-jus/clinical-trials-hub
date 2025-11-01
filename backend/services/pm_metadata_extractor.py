"""
PubMed Metadata Extractor

This module provides functions to extract study metadata from PubMed results
including study type, phase, design allocation, and observational model.
"""

from typing import Dict, List, Optional
import re
import logging

logger = logging.getLogger(__name__)

# Expanded pattern definitions
STUDY_TYPE_PATTERNS = {
    'INTERVENTIONAL': [
        # Clinical trial related
        r'clinical\s*trial',
        r'randomized\s*controlled\s*trial',
        r'rct\b',
        r'randomised\s*controlled\s*trial',
        r'controlled\s*clinical\s*trial',
        r'intervention(?:al)?\s*(?:study|trial)',
        r'treatment\s*(?:study|trial)',
        r'therapeutic\s*(?:study|trial)',
        r'efficacy\s*(?:study|trial)',
        r'effectiveness\s*(?:study|trial)',
        # Phase related (strong indicators of interventional)
        r'phase\s*[1-4iv]+\s*(?:study|trial)',
        r'dose[- ]?(?:escalation|finding|ranging)',
        r'first[- ]?in[- ]?human',
        r'proof[- ]?of[- ]?concept',
        # Design related
        r'double[- ]?blind',
        r'single[- ]?blind',
        r'open[- ]?label',
        r'placebo[- ]?controlled',
        r'active[- ]?controlled',
        r'parallel[- ]?group',
        r'crossover\s*(?:study|trial|design)',
        r'factorial\s*(?:study|trial|design)',
        # Allocation related
        r'randomly\s*(?:assigned|allocated)',
        r'randomization',
        r'randomisation',
        # Experimental treatment
        r'experimental\s*(?:treatment|therapy|intervention)',
        r'investigational\s*(?:drug|device|product)',
        r'novel\s*(?:treatment|therapy|intervention)',
    ],
    'OBSERVATIONAL': [
        # Explicit observational
        r'observational\s*(?:study|research)',
        r'non[- ]?interventional',
        r'naturalistic\s*(?:study|observation)',
        # Cohort studies
        r'cohort\s*(?:study|design|analysis)',
        r'prospective\s*cohort',
        r'retrospective\s*cohort',
        r'longitudinal\s*(?:study|cohort|follow[- ]?up)',
        r'follow[- ]?up\s*study',
        # Case-control
        r'case[- ]?control\s*(?:study|design|analysis)',
        r'cases?\s*and\s*controls?',
        # Cross-sectional
        r'cross[- ]?sectional\s*(?:study|survey|analysis)',
        r'prevalence\s*(?:study|survey)',
        r'survey\s*(?:study|research)',
        # Registry/Database
        r'registry\s*(?:study|based|analysis)',
        r'database\s*(?:study|analysis)',
        r'claims\s*(?:database|analysis)',
        r'electronic\s*health\s*records?',
        r'ehr\s*(?:study|analysis)',
        r'real[- ]?world\s*(?:data|evidence|study)',
        # Epidemiological
        r'epidemiologic(?:al)?\s*(?:study|research)',
        r'population[- ]?based\s*(?:study|survey)',
        r'surveillance\s*(?:study|data|system)',
        # Descriptive
        r'descriptive\s*(?:study|analysis)',
        r'case\s*(?:series|reports?)',
        r'chart\s*review',
        r'medical\s*record\s*review',
        # Natural history
        r'natural\s*history\s*(?:study|course)',
        r'disease\s*progression\s*(?:study|analysis)',
        # Risk factors
        r'risk\s*factor\s*(?:study|analysis)',
        r'association\s*(?:study|analysis)',
        r'correlation\s*(?:study|analysis)',
    ]
}

# Phase pattern expansion
PHASE_PATTERNS = {
    'EARLY_PHASE1': [
        r'early\s*phase\s*(?:1|i|one)',
        r'phase\s*0',
        r'phase\s*zero',
        r'first[- ]?in[- ]?human',
        r'fih\s*(?:study|trial)',
    ],
    'PHASE1': [
        r'phase\s*(?:1|i|one)\b(?![/\s]*(?:2|ii))',
        r'dose[- ]?(?:escalation|finding)\s*study',
        r'dose[- ]?ranging\s*study',
        r'safety\s*and\s*tolerability',
        r'maximum\s*tolerated\s*dose',
        r'mtd\s*study',
        r'pharmacokinetic\s*study',
        r'pk\s*study',
    ],
    'PHASE2': [
        r'phase\s*(?:2|ii|two)\b(?![/\s]*(?:3|iii))',
        r'proof[- ]?of[- ]?concept',
        r'dose[- ]?response',
        r'efficacy\s*and\s*safety',
        r'pilot\s*(?:study|trial)',
    ],
    'PHASE3': [
        r'phase\s*(?:3|iii|three)\b(?![/\s]*(?:4|iv))',
        r'pivotal\s*(?:trial|study)',
        r'confirmatory\s*(?:trial|study)',
        r'comparative\s*effectiveness',
        r'superiority\s*(?:trial|study)',
        r'non[- ]?inferiority\s*(?:trial|study)',
        r'equivalence\s*(?:trial|study)',
    ],
    'PHASE4': [
        r'phase\s*(?:4|iv|four)',
        r'post[- ]?marketing\s*surveillance',
        r'post[- ]?approval',
        r'real[- ]?world\s*effectiveness',
        r'pharmacovigilance',
    ]
}

# Design allocation patterns
DESIGN_ALLOCATION_PATTERNS = {
    'RANDOMIZED': [
        r'randomiz(?:ed|ation)',
        r'randomis(?:ed|ation)',
        r'randomly\s*(?:assigned|allocated|divided)',
        r'random\s*(?:allocation|assignment)',
        r'rct\b',
        r'randomized\s*controlled',
        r'randomised\s*controlled',
    ],
    'NON_RANDOMIZED': [
        r'non[- ]?randomiz(?:ed|ation)',
        r'non[- ]?randomis(?:ed|ation)',
        r'quasi[- ]?experimental',
        r'quasi[- ]?randomized',
        r'pseudo[- ]?randomized',
        r'systematic\s*allocation',
        r'alternate\s*allocation',
        r'historical\s*control',
        r'concurrent\s*control',
        r'matched\s*control',
    ]
}

# Observational model patterns
OBSERVATIONAL_MODEL_PATTERNS = {
    'COHORT': [
        r'cohort\s*(?:study|design|analysis)?',
        r'longitudinal\s*(?:study|cohort|follow[- ]?up)',
        r'prospective\s*(?:cohort|study|follow[- ]?up)',
        r'retrospective\s*cohort',
        r'follow[- ]?up\s*study',
        r'inception\s*cohort',
        r'birth\s*cohort',
        r'population\s*cohort',
    ],
    'CASE_CONTROL': [
        r'case[- ]?control',
        r'case[- ]?controlled',
        r'cases?\s*(?:and|versus|vs\.?)\s*controls?',
        r'matched\s*case[- ]?control',
        r'nested\s*case[- ]?control',
    ],
    'CASE_ONLY': [
        r'case[- ]?only',
        r'case\s*series',
        r'case\s*reports?',
        r'clinical\s*case\s*(?:series|reports?)',
        r'consecutive\s*cases',
    ],
    'CASE_CROSSOVER': [
        r'case[- ]?crossover',
        r'self[- ]?controlled\s*case\s*series',
        r'within[- ]?subject\s*comparison',
    ],
    'ECOLOGIC_OR_COMMUNITY_STUDY': [
        r'ecologic(?:al)?\s*study',
        r'community[- ]?based\s*study',
        r'population[- ]?level\s*study',
        r'aggregate\s*data\s*study',
    ],
    'FAMILY_BASED': [
        r'family[- ]?based\s*study',
        r'familial\s*(?:study|analysis)',
        r'pedigree\s*(?:study|analysis)',
        r'twin\s*study',
        r'sibling\s*study',
    ],
    'CROSS_SECTIONAL': [
        r'cross[- ]?sectional',
        r'prevalence\s*(?:study|survey)',
        r'point[- ]?prevalence',
        r'snapshot\s*study',
    ],
    'TIME_SERIES': [
        r'time[- ]?series',
        r'interrupted\s*time[- ]?series',
        r'temporal\s*(?:analysis|trend)',
    ]
}


def extract_from_structured_abstract(abstract: Dict, field_names: List[str]) -> Optional[str]:
    """Extract specific field content from structured abstract"""
    if not isinstance(abstract, dict):
        return None
    
    for field_name in field_names:
        for key, value in abstract.items():
            if field_name.lower() in key.lower():
                return str(value)
    return None


def extract_study_type_from_pm(result: Dict) -> str:
    """Extract Study Type from PubMed result - Advanced version"""
    
    # Initialize _meta if not present
    if '_meta' not in result:
        result['_meta'] = {}
    
    extraction_source = None
    study_type = None
    confidence_score = 0
    
    # 1. Analyze Publication Types
    pub_types = result.get('publication_types', []) or []
    pub_types = [str(pt).lower() for pt in pub_types if pt is not None]
    pub_types_text = ' '.join(pub_types)
    
    # Strong indicators for Interventional
    interventional_pub_types = [
        'randomized controlled trial',
        'controlled clinical trial',
        'clinical trial',
        'clinical trial, phase i',
        'clinical trial, phase ii',
        'clinical trial, phase iii',
        'clinical trial, phase iv',
        'pragmatic clinical trial',
        'equivalence trial',
        'adaptive clinical trial'
    ]
    
    for ipt in interventional_pub_types:
        if ipt in pub_types_text:
            study_type = 'INTERVENTIONAL'
            extraction_source = 'publication_types'
            confidence_score = 0.9
            break
    
    # Strong indicators for Observational
    if not study_type:
        observational_pub_types = [
            'observational study',
            'cohort study',
            'longitudinal study',
            'cross-sectional study',
            'case-control study',
            'case reports',
            'epidemiologic study',
            'multicenter study'  # Sometimes can be observational
        ]
        
        for opt in observational_pub_types:
            if opt in pub_types_text:
                study_type = 'OBSERVATIONAL'
                extraction_source = 'publication_types'
                confidence_score = 0.9
                break
    
    # 2. Analyze MeSH Terms
    if not study_type or confidence_score < 0.9:
        mesh_headings = result.get('mesh_headings', [])
        mesh_text = []
        
        for mesh in mesh_headings:
            if isinstance(mesh, dict):
                descriptor = mesh.get('descriptor', '')
                mesh_text.append(str(descriptor).lower())
                # Also check qualifiers
                for qual in mesh.get('qualifiers', []):
                    if isinstance(qual, dict):
                        mesh_text.append(str(qual.get('name', '')).lower())
            elif mesh:
                mesh_text.append(str(mesh).lower())
        
        mesh_combined = ' '.join(mesh_text)
        
        # Interventional by MeSH
        if any(term in mesh_combined for term in ['clinical trial', 'randomized controlled trial', 'therapeutic use', 'drug therapy']):
            if not study_type or confidence_score < 0.8:
                study_type = 'INTERVENTIONAL'
                extraction_source = 'mesh_headings'
                confidence_score = 0.8
        
        # Observational by MeSH
        elif any(term in mesh_combined for term in ['epidemiologic studies', 'cohort studies', 'case-control studies', 'cross-sectional studies']):
            if not study_type or confidence_score < 0.8:
                study_type = 'OBSERVATIONAL'
                extraction_source = 'mesh_headings'
                confidence_score = 0.8
    
    # 3. Analyze Title
    title = result.get('title', '') or ''
    title_lower = title.lower()
    
    # Extract strong indicators from the title
    if not study_type or confidence_score < 0.7:
        # Interventional patterns
        for pattern in STUDY_TYPE_PATTERNS['INTERVENTIONAL']:
            if re.search(pattern, title_lower):
                study_type = 'INTERVENTIONAL'
                extraction_source = 'title'
                confidence_score = max(confidence_score, 0.7)
                break
        
        # Observational patterns
        if not study_type or confidence_score < 0.7:
            for pattern in STUDY_TYPE_PATTERNS['OBSERVATIONAL']:
                if re.search(pattern, title_lower):
                    study_type = 'OBSERVATIONAL'
                    extraction_source = 'title'
                    confidence_score = max(confidence_score, 0.7)
                    break
    
    # 4. Analyze Methods section of structured abstract
    abstract = result.get('abstract')
    if abstract and (not study_type or confidence_score < 0.6):
        # Extract Methods section
        methods_text = ''
        if isinstance(abstract, dict):
            methods_text = extract_from_structured_abstract(
                abstract, 
                ['METHODS', 'METHOD', 'DESIGN', 'STUDY DESIGN', 'METHODOLOGY']
            ) or ''
            # Also analyze full abstract
            full_abstract = ' '.join(str(v) for v in abstract.values() if v)
        else:
            full_abstract = str(abstract) if abstract else ''
            methods_text = full_abstract
        
        combined_text = f"{methods_text} {full_abstract}".lower()
        
        # Pattern matching
        interventional_score = 0
        observational_score = 0
        
        for pattern in STUDY_TYPE_PATTERNS['INTERVENTIONAL']:
            if re.search(pattern, combined_text):
                interventional_score += 1
        
        for pattern in STUDY_TYPE_PATTERNS['OBSERVATIONAL']:
            if re.search(pattern, combined_text):
                observational_score += 1
        
        # Decide based on score
        if interventional_score > observational_score:
            study_type = 'INTERVENTIONAL'
            extraction_source = 'abstract'
            confidence_score = max(confidence_score, 0.6)
        elif observational_score > interventional_score:
            study_type = 'OBSERVATIONAL'
            extraction_source = 'abstract'
            confidence_score = max(confidence_score, 0.6)
    
    # 5. Analyze Keywords
    if not study_type or confidence_score < 0.5:
        keywords = result.get('keywords', [])
        keywords_text = ' '.join(str(kw).lower() for kw in keywords)
        
        if any(term in keywords_text for term in ['clinical trial', 'randomized', 'intervention', 'treatment']):
            study_type = 'INTERVENTIONAL'
            extraction_source = 'keywords'
            confidence_score = max(confidence_score, 0.5)
        elif any(term in keywords_text for term in ['observational', 'cohort', 'epidemiology', 'surveillance']):
            study_type = 'OBSERVATIONAL'
            extraction_source = 'keywords'
            confidence_score = max(confidence_score, 0.5)
    
    # Save metadata
    result['_meta']['study_type_source'] = extraction_source or 'not_found'
    result['_meta']['study_type_confidence'] = confidence_score
    
    return study_type if study_type else 'NA'


def extract_phase_from_pm(result: Dict) -> str:
    """Extract Phase from PubMed result - Advanced version"""
    
    # Initialize _meta if not present
    if '_meta' not in result:
        result['_meta'] = {}
    
    # If the study type is not INTERVENTIONAL, the phase is NA
    study_type = result.get('study_type') or result.get('_meta', {}).get('study_type')
    if study_type != 'INTERVENTIONAL':
        result['_meta']['phase_source'] = 'not_applicable'
        return 'NA'
    
    extraction_source = None
    phase = None
    confidence_score = 0
    
    # 1. Check explicit phase in publication types
    pub_types = result.get('publication_types', []) or []
    pub_types_text = ' '.join(str(pt).lower() for pt in pub_types if pt)
    
    # Explicit phase notation
    phase_pub_type_map = {
        'clinical trial, phase i': 'PHASE1',
        'clinical trial, phase ii': 'PHASE2',
        'clinical trial, phase iii': 'PHASE3',
        'clinical trial, phase iv': 'PHASE4'
    }
    
    for pub_pattern, phase_value in phase_pub_type_map.items():
        if pub_pattern in pub_types_text:
            phase = phase_value
            extraction_source = 'publication_types'
            confidence_score = 1.0
            break
    
    # 2. Extract phase from title
    if not phase or confidence_score < 0.9:
        title = result.get('title', '') or ''
        title_lower = title.lower()
        
        # Various phase patterns
        for phase_name, patterns in PHASE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, title_lower):
                    phase = phase_name
                    extraction_source = 'title'
                    confidence_score = max(confidence_score, 0.9)
                    break
            if phase and confidence_score >= 0.9:
                break
    
    # 3. Analyze abstract
    abstract = result.get('abstract')
    if abstract and (not phase or confidence_score < 0.8):
        # Check Methods section first
        methods_text = ''
        if isinstance(abstract, dict):
            methods_text = extract_from_structured_abstract(
                abstract,
                ['METHODS', 'METHOD', 'DESIGN', 'STUDY DESIGN', 'OBJECTIVE', 'PURPOSE']
            ) or ''
            full_abstract = ' '.join(str(v) for v in abstract.values() if v)
        else:
            full_abstract = str(abstract) if abstract else ''
        
        search_text = f"{methods_text} {full_abstract}".lower()
        
        # Phase pattern matching
        for phase_name, patterns in PHASE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, search_text):
                    if not phase or confidence_score < 0.8:
                        phase = phase_name
                        extraction_source = 'abstract'
                        confidence_score = 0.8
                    break
    
    # 4. Extract phase info from MeSH terms
    if not phase or confidence_score < 0.7:
        mesh_headings = result.get('mesh_headings', [])
        mesh_text = []
        
        for mesh in mesh_headings:
            if isinstance(mesh, dict):
                mesh_text.append(str(mesh.get('descriptor', '')).lower())
            elif mesh:
                mesh_text.append(str(mesh).lower())
        
        mesh_combined = ' '.join(mesh_text)
        
        # Phase-related MeSH terms
        if 'phase i' in mesh_combined or 'phase 1' in mesh_combined:
            phase = 'PHASE1'
            extraction_source = 'mesh_headings'
            confidence_score = max(confidence_score, 0.7)
        elif 'phase ii' in mesh_combined or 'phase 2' in mesh_combined:
            phase = 'PHASE2'
            extraction_source = 'mesh_headings'
            confidence_score = max(confidence_score, 0.7)
        elif 'phase iii' in mesh_combined or 'phase 3' in mesh_combined:
            phase = 'PHASE3'
            extraction_source = 'mesh_headings'
            confidence_score = max(confidence_score, 0.7)
        elif 'phase iv' in mesh_combined or 'phase 4' in mesh_combined:
            phase = 'PHASE4'
            extraction_source = 'mesh_headings'
            confidence_score = max(confidence_score, 0.7)
    
    # 5. Find phase hints in keywords
    if not phase or confidence_score < 0.6:
        keywords = result.get('keywords', [])
        keywords_text = ' '.join(str(kw).lower() for kw in keywords)
        
        for phase_name, patterns in PHASE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, keywords_text):
                    phase = phase_name
                    extraction_source = 'keywords'
                    confidence_score = max(confidence_score, 0.6)
                    break
    
    # Save metadata
    result['_meta']['phase_source'] = extraction_source or 'not_found'
    result['_meta']['phase_confidence'] = confidence_score
    
    return phase if phase else 'NA'


def normalize_design_allocation_from_pm(doc: Dict) -> str:
    """Extract design allocation from PM document - Advanced version"""
    # Return NA if study type is not INTERVENTIONAL
    study_type = doc.get('study_type') or doc.get('_meta', {}).get('study_type')
    if study_type != 'INTERVENTIONAL':
        return 'NA'
    
    confidence_score = 0
    allocation = None
    
    # 1. Check publication types
    pub_types = doc.get('publication_types', []) or []
    pub_types_text = ' '.join(str(pt).lower() for pt in pub_types if pt)
    
    if 'randomized controlled trial' in pub_types_text:
        allocation = 'RANDOMIZED'
        confidence_score = 1.0
    
    # 2. Check title
    if not allocation or confidence_score < 0.9:
        title = doc.get('title', '') or ''
        title_lower = title.lower()
        
        for alloc_type, patterns in DESIGN_ALLOCATION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, title_lower):
                    allocation = alloc_type
                    confidence_score = max(confidence_score, 0.9)
                    break
    
    # 3. Check abstract
    if not allocation or confidence_score < 0.8:
        abstract = doc.get('abstract')
        if abstract:
            if isinstance(abstract, dict):
                # Check Methods section first
                methods_text = extract_from_structured_abstract(
                    abstract,
                    ['METHODS', 'METHOD', 'DESIGN', 'STUDY DESIGN']
                ) or ''
                full_abstract = ' '.join(str(v) for v in abstract.values() if v)
                search_text = f"{methods_text} {full_abstract}".lower()
            else:
                search_text = str(abstract).lower()
            
            # Randomized pattern score
            randomized_score = 0
            non_randomized_score = 0
            
            for pattern in DESIGN_ALLOCATION_PATTERNS['RANDOMIZED']:
                if re.search(pattern, search_text):
                    randomized_score += 1
            
            for pattern in DESIGN_ALLOCATION_PATTERNS['NON_RANDOMIZED']:
                if re.search(pattern, search_text):
                    non_randomized_score += 1
            
            if randomized_score > non_randomized_score:
                allocation = 'RANDOMIZED'
                confidence_score = max(confidence_score, 0.8)
            elif non_randomized_score > 0:
                allocation = 'NON_RANDOMIZED'
                confidence_score = max(confidence_score, 0.8)
    
    # 4. Check MeSH terms
    if not allocation or confidence_score < 0.7:
        mesh_headings = doc.get('mesh_headings', [])
        mesh_text = []
        
        for mesh in mesh_headings:
            if isinstance(mesh, dict):
                mesh_text.append(str(mesh.get('descriptor', '')).lower())
            elif mesh:
                mesh_text.append(str(mesh).lower())
        
        mesh_combined = ' '.join(mesh_text)
        
        if 'random allocation' in mesh_combined or 'randomized controlled trial' in mesh_combined:
            allocation = 'RANDOMIZED'
            confidence_score = max(confidence_score, 0.7)
    
    # Save
    if '_meta' not in doc:
        doc['_meta'] = {}
    doc['_meta']['design_allocation_confidence'] = confidence_score
    
    return allocation if allocation else 'NA'


def normalize_observational_model_from_pm(doc: Dict) -> str:
    """Extract observational model from PM document - Advanced version"""
    # Return 'NA' if study type is not OBSERVATIONAL
    study_type = doc.get('study_type') or doc.get('_meta', {}).get('study_type')
    if study_type != 'OBSERVATIONAL':
        return 'NA'
    
    confidence_score = 0
    model = None
    
    # 1. Check publication types
    pub_types = doc.get('publication_types', []) or []
    pub_types_text = ' '.join(str(pt).lower() for pt in pub_types if pt)
    
    pub_type_model_map = {
        'cohort study': 'COHORT',
        'longitudinal study': 'COHORT',
        'case-control study': 'CASE_CONTROL',
        'cross-sectional study': 'CROSS_SECTIONAL',
        'case reports': 'CASE_ONLY'
    }
    
    for pub_pattern, model_value in pub_type_model_map.items():
        if pub_pattern in pub_types_text:
            model = model_value
            confidence_score = 0.9
            break
    
    # 2. Check title
    if not model or confidence_score < 0.8:
        title = doc.get('title', '') or ''
        title_lower = title.lower()
        
        for model_type, patterns in OBSERVATIONAL_MODEL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, title_lower):
                    model = model_type
                    confidence_score = max(confidence_score, 0.8)
                    break
    
    # 3. Check abstract
    abstract = doc.get('abstract')
    if abstract and (not model or confidence_score < 0.7):
        if isinstance(abstract, dict):
            # Methods/Design section first
            methods_text = extract_from_structured_abstract(
                abstract,
                ['METHODS', 'METHOD', 'DESIGN', 'STUDY DESIGN', 'METHODOLOGY']
            ) or ''
            full_abstract = ' '.join(str(v) for v in abstract.values() if v)
            search_text = f"{methods_text} {full_abstract}".lower()
        else:
            search_text = str(abstract).lower() if abstract else ''
        
        # Calculate score for each model type
        model_scores = {}
        for model_type, patterns in OBSERVATIONAL_MODEL_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, search_text):
                    score += 1
            if score > 0:
                model_scores[model_type] = score
        
        # Select the model with the highest score
        if model_scores:
            best_model = max(model_scores.items(), key=lambda x: x[1])
            model = best_model[0]
            confidence_score = max(confidence_score, 0.7)
    
    # 4. Check MeSH terms
    if not model or confidence_score < 0.6:
        mesh_headings = doc.get('mesh_headings', [])
        mesh_text = []
        
        for mesh in mesh_headings:
            if isinstance(mesh, dict):
                mesh_text.append(str(mesh.get('descriptor', '')).lower())
            elif mesh:
                mesh_text.append(str(mesh).lower())
        
        mesh_combined = ' '.join(mesh_text)
        
        mesh_model_map = {
            'cohort studies': 'COHORT',
            'case-control studies': 'CASE_CONTROL',
            'cross-sectional studies': 'CROSS_SECTIONAL',
            'longitudinal studies': 'COHORT'
        }
        
        for mesh_pattern, model_value in mesh_model_map.items():
            if mesh_pattern in mesh_combined:
                model = model_value
                confidence_score = max(confidence_score, 0.6)
                break
    
    # 5. Check keywords
    if not model or confidence_score < 0.5:
        keywords = doc.get('keywords', [])
        keywords_text = ' '.join(str(kw).lower() for kw in keywords)
        
        for model_type, patterns in OBSERVATIONAL_MODEL_PATTERNS.items():
            for pattern in patterns[:3]:  # Check only main patterns
                if re.search(pattern, keywords_text):
                    model = model_type
                    confidence_score = max(confidence_score, 0.5)
                    break
    
    # Save
    if '_meta' not in doc:
        doc['_meta'] = {}
    doc['_meta']['observational_model_confidence'] = confidence_score
    
    return model if model else 'NA'


def extract_all_metadata_from_pm(doc: Dict) -> None:
    """Extract all metadata from PM result and store in _meta field and direct fields"""
    if '_meta' not in doc:
        doc['_meta'] = {}
    
    # Extract study type
    study_type = extract_study_type_from_pm(doc)
    doc['_meta']['study_type'] = study_type
    doc['study_type'] = study_type  # Also store in direct field
    
    # If INTERVENTIONAL, extract phase and design_allocation
    if study_type == 'INTERVENTIONAL':
        # extract_phase_from_pm returns a string
        phase = extract_phase_from_pm(doc)
        doc['_meta']['phase'] = phase
        doc['phase'] = phase  # Also store in direct field
        
        # phase_source is set in _meta by extract_phase_from_pm
        doc['_meta']['phase_source'] = doc.get('_meta', {}).get('phase_source', 'not_found')
        
        design_allocation = normalize_design_allocation_from_pm(doc)
        doc['design_allocation'] = design_allocation if design_allocation else 'NA'
        
        # observational_model is NA for INTERVENTIONAL
        doc['observational_model'] = 'NA'
        
    # If OBSERVATIONAL, extract observational_model
    elif study_type == 'OBSERVATIONAL':
        observational_model = normalize_observational_model_from_pm(doc)
        # Ensure default value 'NA' if None or empty string
        if not observational_model or observational_model == '':
            observational_model = 'NA'
        doc['observational_model'] = observational_model
        
        # phase and design_allocation are NA for OBSERVATIONAL
        doc['phase'] = 'NA'
        doc['_meta']['phase'] = 'NA'
        doc['design_allocation'] = 'NA'
    
    # For other study_type ('NA', etc.), set all fields to 'NA'
    else:
        doc['study_type'] = 'NA'
        doc['observational_model'] = 'NA'
        doc['design_allocation'] = 'NA'
        doc['phase'] = 'NA'
        doc['_meta']['phase'] = 'NA'