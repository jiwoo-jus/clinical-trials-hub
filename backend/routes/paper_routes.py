from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from services import ctg_service, ctg_client, pmc_service
from services.extraction.extraction_pipeline import get_extraction_pipeline
from services.extraction.extraction_logger import get_extraction_logger
from services.validation.validation_pipeline import ValidationPipeline
from services.validation.validation_types import ValidationConfig, ValidationContext
import json
import time

router = APIRouter()

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
async def get_ctg_detail(nctId: str):
    try:
        detail = ctg_client.get_ctg_detail(nctId)
        return {"nctId": nctId, "structured_info": detail, "full_text": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))