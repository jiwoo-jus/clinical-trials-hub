"""
Systematic Review Service

This service handles eligibility criteria checking for systematic reviews.
It analyzes paper abstracts against user-defined inclusion and exclusion criteria.
"""

import json
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from services.openai_service import OpenAIService
from services.pmc_service import get_pmc_full_text_xml
from services.ctg_client import get_ctg_detail

logger = logging.getLogger(__name__)


def extract_abstract_from_xml(xml_content: str) -> Optional[str]:
    """
    Extract abstract from PMC XML content.
    Returns the abstract text or None if not found.
    """
    try:
        soup = BeautifulSoup(xml_content, 'xml')
        
        # Try to find abstract in the front matter
        abstract_element = soup.find('abstract')
        if abstract_element:
            # Get all text, joining paragraphs with newlines
            paragraphs = abstract_element.find_all('p')
            if paragraphs:
                abstract_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
            else:
                abstract_text = abstract_element.get_text(strip=True)
            
            if abstract_text:
                return abstract_text
        
        logger.warning("No abstract found in XML")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting abstract from XML: {e}")
        return None


def get_abstract_by_pmcid(pmcid: str) -> str:
    """
    Fetch and extract abstract from PMC by PMCID.
    Raises ValueError if abstract cannot be retrieved.
    """
    try:
        xml_content = get_pmc_full_text_xml(pmcid)
        if not xml_content or xml_content.startswith("Error"):
            raise ValueError(f"Failed to fetch XML for {pmcid}")
        
        abstract = extract_abstract_from_xml(xml_content)
        if not abstract:
            raise ValueError(f"No abstract found in {pmcid}")
        
        return abstract
        
    except Exception as e:
        logger.error(f"Error getting abstract for {pmcid}: {e}")
        raise


def get_description_by_nctid(nctid: str) -> str:
    """
    Fetch and extract brief summary/description from ClinicalTrials.gov by NCT ID.
    Raises ValueError if description cannot be retrieved.
    """
    try:
        ctg_detail = get_ctg_detail(nctid)
        if not ctg_detail:
            raise ValueError(f"Failed to fetch CTG detail for {nctid}")
        
        # Extract brief summary from the structured info
        description = ""
        
        # Try to get brief summary
        if isinstance(ctg_detail, dict) and 'brief_summary' in ctg_detail:
            description = ctg_detail.get('brief_summary', '')
        
        # If no brief summary, try to construct from other fields
        if not description:
            parts = []
            if isinstance(ctg_detail, dict):
                if 'brief_title' in ctg_detail:
                    parts.append(f"Title: {ctg_detail['brief_title']}")
                if 'official_title' in ctg_detail:
                    parts.append(f"Official Title: {ctg_detail['official_title']}")
                if 'conditions' in ctg_detail and ctg_detail['conditions']:
                    parts.append(f"Conditions: {', '.join(ctg_detail['conditions'])}")
                if 'intervention_names' in ctg_detail and ctg_detail['intervention_names']:
                    parts.append(f"Interventions: {', '.join(ctg_detail['intervention_names'])}")
                if 'primary_outcomes' in ctg_detail and ctg_detail['primary_outcomes']:
                    parts.append(f"Primary Outcomes: {', '.join(ctg_detail['primary_outcomes'][:3])}")  # Limit to first 3
            
            description = '\n\n'.join(parts)
        
        if not description:
            raise ValueError(f"No description found for {nctid}")
        
        return description
        
    except Exception as e:
        logger.error(f"Error getting description for {nctid}: {e}")
        raise



class SystematicReviewService:
    """Service for checking systematic review eligibility criteria"""
    
    def __init__(self):
        self.openai_service = OpenAIService()
        self._load_prompts()
    
    def _load_prompts(self):
        """Load prompt templates from files"""
        try:
            with open('prompts/systematic_review_check_system.md', 'r', encoding='utf-8') as f:
                self.system_prompt = f.read()
            
            with open('prompts/systematic_review_check_user.md', 'r', encoding='utf-8') as f:
                self.user_prompt_template = f.read()
                
            logger.info("✅ Systematic review prompts loaded successfully")
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")
            raise
    
    def _build_criteria_list(self, inclusion_criteria: List[str], exclusion_criteria: List[str]) -> List[Dict]:
        """Build a structured list of all criteria with IDs and types"""
        all_criteria = []
        
        for idx, criterion in enumerate(inclusion_criteria):
            all_criteria.append({
                "id": f"inclusion_{idx}",
                "type": "inclusion",
                "criterion": criterion
            })
        
        for idx, criterion in enumerate(exclusion_criteria):
            all_criteria.append({
                "id": f"exclusion_{idx}",
                "type": "exclusion",
                "criterion": criterion
            })
        
        return all_criteria
    
    def _format_criteria_for_prompt(self, criteria_list: List[Dict]) -> str:
        """Format criteria list for the prompt"""
        formatted = []
        for c in criteria_list:
            # Important: provide only the raw statement to avoid biasing with inclusion/exclusion semantics
            formatted.append(f'{c["id"]}: {c["criterion"]}')
        return '\n'.join(formatted)
    
    def _parse_criterion_result(self, result: Dict, criterion: str, criterion_type: str) -> Dict:
        """Parse and structure a single criterion result

        The model returns truth-only judgments using the field `is_true` with values true/false/"unclear".
        We keep the raw truth under `is_true` and derive a status (met/not_met/unclear).
        `meets_criterion` is kept for backward compatibility and equals `is_true`.
        """
        meets = result.get("is_true", result.get("meets_criterion", "unclear"))
        confidence = result.get("confidence", 0.0)
        evidence = result.get("evidence", "undeterminable")
        
        # Convert string "unclear" to actual unclear status based on confidence
        # If LLM returns "unclear" but has high confidence and evidence, it likely means "true"
        if meets == "unclear":
            if confidence >= 0.6 and evidence and evidence != "undeterminable":
                # High confidence with evidence -> treat as true
                meets = True
            else:
                # Low confidence or no evidence -> genuinely unclear
                status = "unclear"
                truth_bool = None
                return {
                    "criterion": criterion,
                    "type": criterion_type,
                    "status": status,
                    "meets_criterion": truth_bool,
                    "is_true": truth_bool,
                    "confidence": round(confidence, 2),
                    "evidence": evidence,
                    "reasoning": result.get("reasoning", "")
                }
        
        # Handle true/false cases
        if confidence < 0.6:
            status = "unclear"
            truth_bool = None
        else:
            status = "met" if bool(meets) else "not_met"
            truth_bool = bool(meets)
        
        return {
            "criterion": criterion,
            "type": criterion_type,
            "status": status,
            # Backward compatibility for downstream logic that uses this field
            "meets_criterion": truth_bool,
            # New explicit truth-only field for frontend display
            "is_true": truth_bool,
            "confidence": round(confidence, 2),
            "evidence": evidence,
            "reasoning": result.get("reasoning", "")
        }
    
    def _calculate_overall_recommendation(
        self, 
        inclusion_results: List[Dict], 
        exclusion_results: List[Dict]
    ) -> tuple[str, Dict]:
        """
        Calculate overall recommendation based on all criteria results.
        Returns (recommendation, summary_stats)
        """
        # Filter out unclear results for definite assessment
        inclusion_definite = [r for r in inclusion_results if r["status"] != "unclear"]
        exclusion_definite = [r for r in exclusion_results if r["status"] != "unclear"]
        
        # Check if there are any unclear results
        has_unclear = any(r["status"] == "unclear" for r in inclusion_results + exclusion_results)
        
        # Check if all inclusion criteria are met and no exclusion criteria are met
        all_inclusion_met = all(r["meets_criterion"] for r in inclusion_definite) if inclusion_definite else True
        any_exclusion_met = any(r["meets_criterion"] for r in exclusion_definite) if exclusion_definite else False
        
        # Calculate average confidence scores
        avg_inclusion_confidence = (
            sum(r["confidence"] for r in inclusion_results) / len(inclusion_results) 
            if inclusion_results else 1.0
        )
        avg_exclusion_confidence = (
            sum(r["confidence"] for r in exclusion_results) / len(exclusion_results) 
            if exclusion_results else 1.0
        )
        
        # Determine overall recommendation (conservative approach)
        if has_unclear:
            recommendation = "UNCLEAR"
        elif any_exclusion_met and avg_exclusion_confidence >= 0.7:
            recommendation = "EXCLUDE"
        elif all_inclusion_met and avg_inclusion_confidence >= 0.7 and not any_exclusion_met:
            recommendation = "INCLUDE"
        else:
            recommendation = "UNCLEAR"
        
        summary = {
            "inclusion_met": all_inclusion_met,
            "exclusion_met": any_exclusion_met,
            "avg_inclusion_confidence": round(avg_inclusion_confidence, 2),
            "avg_exclusion_confidence": round(avg_exclusion_confidence, 2),
            "has_unclear": has_unclear,
            "total_criteria": len(inclusion_results) + len(exclusion_results),
            "unclear_count": sum(1 for r in inclusion_results + exclusion_results if r["status"] == "unclear")
        }
        
        return recommendation, summary
    
    async def check_eligibility_criteria(
        self,
        study_id: str,
        inclusion_criteria: List[str],
        exclusion_criteria: List[str],
        study_type: str = "PMC",  # "PMC" or "CTG"
        text_content: Optional[str] = None  # Optional pre-extracted text
    ) -> Dict:
        """
        Check if a study meets systematic review eligibility criteria.
        
        Args:
            study_id: PubMed Central ID (PMCID) or ClinicalTrials.gov ID (NCT ID)
            inclusion_criteria: List of inclusion criteria
            exclusion_criteria: List of exclusion criteria
            study_type: Type of study - "PMC" for PubMed papers or "CTG" for clinical trials
            text_content: Optional pre-extracted text content (if provided, skips fetching)
            
        Returns:
            Dictionary containing:
            - study_id: The study identifier (PMCID or NCT ID)
            - study_type: Type of study (PMC or CTG)
            - inclusion_results: List of results for each inclusion criterion
            - exclusion_results: List of results for each exclusion criterion
            - overall_recommendation: INCLUDE/EXCLUDE/UNCLEAR
            - summary: Summary statistics
        """
        try:
            # Validate inputs
            if not inclusion_criteria and not exclusion_criteria:
                return {
                    "study_id": study_id,
                    "study_type": study_type,
                    "inclusion_results": [],
                    "exclusion_results": [],
                    "overall_recommendation": "UNCLEAR",
                    "summary": {
                        "inclusion_met": False,
                        "exclusion_met": False,
                        "avg_inclusion_confidence": 0.0,
                        "avg_exclusion_confidence": 0.0,
                        "has_unclear": True,
                        "total_criteria": 0,
                        "unclear_count": 0
                    },
                    "message": "No criteria provided"
                }
            
            # Use provided text_content or fetch based on study type
            if text_content:
                logger.info(f"Using pre-extracted text content for {study_id} ({study_type})")
                content_label = "provided content"
            elif study_type.upper() == "CTG":
                text_content = get_description_by_nctid(study_id)
                content_label = "clinical trial description"
            else:  # Default to PMC
                text_content = get_abstract_by_pmcid(study_id)
                content_label = "abstract"
            
            # Build criteria list
            all_criteria = self._build_criteria_list(inclusion_criteria, exclusion_criteria)
            criteria_formatted = self._format_criteria_for_prompt(all_criteria)
            
            # Build prompt (template uses "abstract" but works for any text description)
            user_prompt = self.user_prompt_template.format(
                abstract=text_content,
                criteria_list=criteria_formatted
            )
            
            # Call LLM
            logger.info(f"Checking eligibility criteria for {study_id} ({study_type})")
            response = self.openai_service.generate_completion(
                prompt=user_prompt,
                system_message=self.system_prompt,
                max_tokens=2000,
                temperature=0.1,
                response_format="json"
            )
            
            # Parse response
            parsed_response = json.loads(response)
            results_map = {r["id"]: r for r in parsed_response.get("results", [])}
            
            # Process inclusion criteria results
            inclusion_results = []
            for idx, criterion in enumerate(inclusion_criteria):
                result_id = f"inclusion_{idx}"
                result = results_map.get(result_id, {})
                inclusion_results.append(
                    self._parse_criterion_result(result, criterion, "inclusion")
                )
            
            # Process exclusion criteria results
            exclusion_results = []
            for idx, criterion in enumerate(exclusion_criteria):
                result_id = f"exclusion_{idx}"
                result = results_map.get(result_id, {})
                exclusion_results.append(
                    self._parse_criterion_result(result, criterion, "exclusion")
                )
            
            # Calculate overall recommendation
            recommendation, summary = self._calculate_overall_recommendation(
                inclusion_results, 
                exclusion_results
            )
            
            logger.info(f"✅ Eligibility check complete for {study_id} ({study_type}): {recommendation}")
            
            return {
                "study_id": study_id,
                "study_type": study_type,
                "inclusion_results": inclusion_results,
                "exclusion_results": exclusion_results,
                "overall_recommendation": recommendation,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error checking eligibility criteria for {study_id}: {e}")
            raise
