from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from services import ctg_service, ctg_client, pmc_service
from services.extraction.extraction_pipeline import get_extraction_pipeline
from services.extraction.extraction_logger import get_extraction_logger
from services.validation.validation_pipeline import ValidationPipeline
from services.validation.validation_types import ValidationConfig, ValidationContext
from services.systematic_review_service import SystematicReviewService
import json
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class SystematicReviewRequest(BaseModel):
    """Request model for systematic review eligibility checking"""
    study_id: str  # Can be PMCID or NCT ID
    study_type: str = "PMC"  # "PMC" or "CTG"
    text_content: Optional[str] = None  # Optional: pre-extracted text content from frontend
    inclusion_criteria: List[str] = []
    exclusion_criteria: List[str] = []

async def extract_with_validation(pmc_id: str, paper_content: str) -> dict:
    extraction_pipeline = get_extraction_pipeline()
    logger = get_extraction_logger()
    
    structured_info, session_id = await extraction_pipeline.get_structured_info_with_session(pmc_id, paper_content)
    
    if "_validation" in structured_info:
        print(f"[extract_with_validation] Data already validated for {pmc_id}")
        logger.finalize_session(session_id)
        return structured_info
    
    print(f"[extract_with_validation] Applying validation pipeline for {pmc_id}")
    
    validation_config = ValidationConfig(
        enable_fieldlist_validation=True,
        enable_mesh_validation=False,
        enable_auto_fix=True,
        strict_mesh_validation=False,
        max_parallel_validations=10
    )
    
    validation_context = ValidationContext(
        source_type="PMC_EXTRACTION",
        source_file=f"paper_routes_{pmc_id}",
        extraction_timestamp=time.time()
    )
    
    validation_pipeline = ValidationPipeline(validation_config)
    validation_result = await validation_pipeline.validate_extracted_data(
        structured_info, 
        validation_context,
        session_id
    )
    
    if validation_result.errors:
        print(f"[extract_with_validation] Validation errors: {validation_result.errors}")
    if validation_result.warnings:
        print(f"[extract_with_validation] Validation warnings: {validation_result.warnings}")
    
    stats = validation_result.statistics
    print(f"[extract_with_validation] Validation completed: "
          f"{stats.valid_fields if stats else 0} valid fields, "
          f"{len(validation_result.errors)} errors, "
          f"{len(validation_result.warnings)} warnings")
    
    final_data = validation_result.cleaned_data
    
    if not validation_result.is_valid or validation_result.warnings:
        serializable_errors = []
        for error in validation_result.errors:
            try:
                if hasattr(error, 'field_path') and hasattr(error, 'message'):
                    error_dict = {
                        "field_path": error.field_path,
                        "message": error.message,
                    }
                    
                    if hasattr(error, 'level'):
                        if hasattr(error.level, 'value'):
                            error_dict["level"] = error.level.value
                        else:
                            error_dict["level"] = str(error.level)
                    else:
                        error_dict["level"] = "unknown"
                    
                    if hasattr(error, 'expected_value') and error.expected_value is not None:
                        error_dict["expected_value"] = error.expected_value
                    if hasattr(error, 'actual_value') and error.actual_value is not None:
                        error_dict["actual_value"] = error.actual_value
                        
                    serializable_errors.append(error_dict)
                else:
                    serializable_errors.append(str(error))
            except Exception as e:
                print(f"[extract_with_validation] Error serializing validation error: {e}")
                serializable_errors.append(f"Error serialization failed: {str(error)}")
        
        serializable_warnings = []
        for warning in validation_result.warnings:
            try:
                if hasattr(warning, 'field_path') and hasattr(warning, 'message'):
                    warning_dict = {
                        "field_path": warning.field_path,
                        "message": warning.message
                    }
                    
                    if hasattr(warning, 'original_value') and warning.original_value is not None:
                        warning_dict["original_value"] = warning.original_value
                    if hasattr(warning, 'corrected_value') and warning.corrected_value is not None:
                        warning_dict["corrected_value"] = warning.corrected_value
                        
                    serializable_warnings.append(warning_dict)
                else:
                    serializable_warnings.append(str(warning))
            except Exception as e:
                print(f"[extract_with_validation] Error serializing validation warning: {e}")
                serializable_warnings.append(f"Warning serialization failed: {str(warning)}")
        
        stats_dict = {}
        if validation_result.statistics:
            try:
                stats_dict = {
                    "total_fields_input": getattr(validation_result.statistics, 'total_fields_input', 0),
                    "valid_fields": getattr(validation_result.statistics, 'valid_fields', 0),
                    "invalid_fields": getattr(validation_result.statistics, 'invalid_fields', 0),
                    "enum_violations": getattr(validation_result.statistics, 'enum_violations', 0),
                    "structure_violations": getattr(validation_result.statistics, 'structure_violations', 0),
                    "type_violations": getattr(validation_result.statistics, 'type_violations', 0),
                    "constraint_violations": getattr(validation_result.statistics, 'constraint_violations', 0),
                    "removed_fields": getattr(validation_result.statistics, 'removed_fields', 0),
                    "corrected_fields": getattr(validation_result.statistics, 'corrected_fields', 0),
                }
            except Exception as e:
                print(f"[extract_with_validation] Error serializing validation statistics: {e}")
                stats_dict = {"error": "Statistics serialization failed"}
        
        try:
            final_data["_validation"] = {
                "is_valid": validation_result.is_valid,
                "errors": serializable_errors,
                "warnings": serializable_warnings,
                "statistics": stats_dict,
                "validation_time": getattr(validation_result, 'validation_time', 0.0)
            }
        except Exception as e:
            print(f"[extract_with_validation] Error adding validation metadata: {e}")
            # Add minimal validation info if error occurs
            final_data["_validation"] = {
                "is_valid": validation_result.is_valid,
                "errors": [f"Validation metadata error: {str(e)}"],
                "warnings": [],
                "statistics": {},
                "validation_time": 0.0
            }
    
    try:
        logger.finalize_session(session_id, validation_result)
    except Exception as e:
        print(f"[extract_with_validation] Error finalizing session: {e}")
    
    return final_data

@router.get("/pmc_full_text_html")
async def get_pmc_full_text_html(pmcid: str):
    try:
        html_content = pmc_service.get_pmc_full_text_html(pmcid)
        return HTMLResponse(content=html_content, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/structured_info")
async def get_structured_info(
    pmcid: str,
    pmid: Optional[str] = Query(None, description="Original PMID (Optional)"),
    ref_nctids: Optional[str] = Query(
        None,
        description="Comma-separated NCT IDs or JSON-encoded list provided by client",
    ),
    page: Optional[int] = Query(None, description="Search page (Optional)"),
    index: Optional[int] = Query(None, description="Index of clicked result in current page (Optional)")
):
    try:
        provided_refs: list[str] = []
        if ref_nctids:
            try:
                provided_refs = json.loads(ref_nctids)
                if not isinstance(provided_refs, list):
                    raise ValueError
            except Exception:
                provided_refs = [rid.strip() for rid in ref_nctids.split(",") if rid.strip()]

        print(f"debug: pmcid={pmcid}, pmid={pmid}, provided_refs={provided_refs}, page={page}, index={index}")

        if provided_refs and len(provided_refs) == 1:
            structured_info = ctg_client.get_ctg_detail(provided_refs[0])
        else:
            content = pmc_service.get_pmc_full_text_xml(pmcid)
            structured_info = await extract_with_validation(pmcid, content)

        return {
            "pmcid": pmcid,
            "pmid": pmid,
            "ref_nctids": provided_refs,
            "page": page,
            "index": index,
            "structured_info": structured_info
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ctg_detail")
async def get_ctg_detail(
    nctId: Optional[str] = Query(None, description="NCT ID (preferred param name)"),
    nct_id: Optional[str] = Query(None, description="Alternative param name: nct_id"),
    nctid: Optional[str] = Query(None, description="Alternative param name: nctid"),
    id: Optional[str] = Query(None, description="Fallback param name: id")
):
    try:
        effective_nctid = nctId or nct_id or nctid or id
        if not effective_nctid:
            raise HTTPException(
                status_code=422,
                detail="Missing NCT identifier. Provide one of: nctId, nct_id, nctid, id"
            )
        detail = ctg_client.get_ctg_detail(effective_nctid)
        return {"nctId": effective_nctid, "structured_info": detail, "full_text": ""}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check_systematic_review")
async def check_systematic_review(body: SystematicReviewRequest):
    """
    Check if a study meets systematic review inclusion/exclusion criteria.
    
    This endpoint analyzes a paper's abstract or clinical trial description against 
    user-defined eligibility criteria and returns compliance status, confidence scores, 
    and evidence for each criterion.
    
    Args:
        body: Request containing:
            - study_id: PMCID (e.g., "PMC9669925") or NCT ID (e.g., "NCT01740206")
            - study_type: "PMC" for PubMed papers or "CTG" for clinical trials
            - inclusion_criteria: List of inclusion criteria
            - exclusion_criteria: List of exclusion criteria
        
    Returns:
        Dictionary with:
        - study_id: The study identifier
        - study_type: Type of study (PMC or CTG)
        - inclusion_results: Assessment of each inclusion criterion
        - exclusion_results: Assessment of each exclusion criterion
        - overall_recommendation: INCLUDE/EXCLUDE/UNCLEAR
        - summary: Summary statistics
    """
    try:
        # Validate that study_id is provided
        if not body.study_id:
            raise HTTPException(status_code=422, detail="study_id is required")
        
        # Validate study_type
        if body.study_type.upper() not in ["PMC", "CTG"]:
            raise HTTPException(status_code=422, detail="study_type must be 'PMC' or 'CTG'")
        
        # Check if any criteria provided
        if not body.inclusion_criteria and not body.exclusion_criteria:
            return {
                "study_id": body.study_id,
                "study_type": body.study_type,
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
        
        # Initialize service and check eligibility
        review_service = SystematicReviewService()
        result = await review_service.check_eligibility_criteria(
            study_id=body.study_id,
            inclusion_criteria=body.inclusion_criteria,
            exclusion_criteria=body.exclusion_criteria,
            study_type=body.study_type,
            text_content=body.text_content  # Pass pre-extracted text if provided
        )
        
        logger.info(f"✅ Systematic review check completed for {body.study_id} ({body.study_type}): {result['overall_recommendation']}")
        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        # Handle cases where abstract/description cannot be retrieved
        logger.error(f"Failed to fetch content for {body.study_id}: {e}")
        raise HTTPException(status_code=404, detail=f"Could not fetch study content: {str(e)}")
    except Exception as e:
        logger.error(f"Error in systematic review check: {e}")
        raise HTTPException(status_code=500, detail=str(e))
