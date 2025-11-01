"""
Integrated Validation Pipeline

Performs schema validation based on ClinicalTrials.gov FieldList.json.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, AsyncIterator
from pathlib import Path

from .validation_types import (
    ValidationResult, ValidationConfig, ValidationLevel,
    FieldValidationResult, ValidationContext, ValidationWarning,
    ValidationError, ValidationStatistics, ValidationStatus
)
from .async_fieldlist_validator import AsyncFieldListValidator
from .async_mesh_validator import AsyncMeshValidator

# Import logging system
try:
    from ..extraction.extraction_logger import get_extraction_logger, ValidationRecord, DetailedValidationRecord
    LOGGING_AVAILABLE = True
    DETAILED_LOGGING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Advanced logging not available: {e}")
    try:
        from ..extraction.extraction_logger import get_extraction_logger, ValidationRecord
        LOGGING_AVAILABLE = True
        DETAILED_LOGGING_AVAILABLE = False
    except ImportError:
        LOGGING_AVAILABLE = False
        DETAILED_LOGGING_AVAILABLE = False
        print("Warning: Extraction logger not available, validation logging disabled")

# Import validation issue types
try:
    from .validation_issue_types import (
        ValidationIssueType, ValidationSeverity, classify_validation_issue, 
        determine_severity
    )
    ISSUE_CLASSIFICATION_AVAILABLE = True
except ImportError:
    ISSUE_CLASSIFICATION_AVAILABLE = False
    print("Warning: Issue classification not available, using basic logging")


class ValidationPipeline:
    """Integrated validation pipeline class"""
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()

        # Set paths for FieldList.json and Enums.json files
        base_path = Path(__file__).parent.parent.parent / "CTGOV"
        fieldlist_path = str(base_path / "FieldList.json")
        enums_path = str(base_path / "Enums.json")
        
        try:
            self.fieldlist_validator = AsyncFieldListValidator(
                fieldlist_file=fieldlist_path,
                enums_file=enums_path,
                config=self.config
            )
        except Exception as e:
            print(f"⚠️  Warning: AsyncFieldListValidator initialization failed: {e}")
            self.fieldlist_validator = None
        
        try:
            self.mesh_validator = AsyncMeshValidator()
        except Exception as e:
            print(f"⚠️  Warning: AsyncMeshValidator initialization failed: {e}")
            self.mesh_validator = None
        
    async def validate_extracted_data(
        self, 
        data: Dict[str, Any],
        context: Optional[ValidationContext] = None,
        session_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Perform comprehensive validation on extracted data.

        Args:
            data: Clinical trial data to validate.
            context: Validation context (e.g., source, filename).
            session_id: Session ID for logging (optional).

        Returns:
            Integrated validation result.
        """
        start_time = time.time()
        context = context or ValidationContext()
        
        print(f"[ValidationPipeline] Starting validation for context: {context.source_file}")
        
        # Log validation start
        if LOGGING_AVAILABLE and session_id:
            logger = get_extraction_logger()
            logger.log_validation_start(session_id)
        
        # 1. Schema validation based on FieldList (asynchronous)
        if self.fieldlist_validator and self.config.enable_fieldlist_validation:
            fieldlist_task = self.fieldlist_validator.validate_async(data)
        else:
            fieldlist_task = self._create_mock_validation_result(data, "FieldList validator not available or disabled")
        
        # 2. MeSH term validation (asynchronous) - enabled based on settings
        if self.mesh_validator and self.config.enable_mesh_validation:
            mesh_task = self._validate_mesh_terms_async(data, context)
        else:
            # When MeSH validation is disabled, return empty result (no messages)
            mesh_task = self._create_empty_mesh_result()
        
        # 3. Parallel execution
        fieldlist_result, mesh_result = await asyncio.gather(
            fieldlist_task, 
            mesh_task,
            return_exceptions=True
        )
        
        # Process results
        if isinstance(fieldlist_result, Exception):
            print(f"[ValidationPipeline] FieldList validation error: {fieldlist_result}")
            from .validation_types import ValidationError, ValidationStatistics, ValidationStatus
            fieldlist_result = ValidationResult(
                status=ValidationStatus.FAILED,
                cleaned_data=data,
                errors=[ValidationError(
                    field_path="system",
                    message=f"FieldList validation failed: {str(fieldlist_result)}",
                    level=ValidationLevel.CRITICAL
                )],
                warnings=[],
                removed_fields=[],
                statistics=ValidationStatistics()
            )
            
        if isinstance(mesh_result, Exception):
            print(f"[ValidationPipeline] MeSH validation error: {mesh_result}")
            mesh_result = {
                "errors": [f"MeSH validation failed: {str(mesh_result)}"],
                "warnings": [],
                "normalized_data": data,
                "validation_info": {"processed_fields": 0, "normalized_fields": 0}
            }
        
        # Combine results
        combined_result = self._combine_validation_results(
            fieldlist_result, mesh_result, context
        )
        
        end_time = time.time()
        combined_result.validation_time = end_time - start_time
        
        # Log individual validation records
        if LOGGING_AVAILABLE and session_id:
            self._log_validation_details(session_id, combined_result, context)
            logger = get_extraction_logger()
            logger.log_validation_end(session_id)
        
        print(f"[ValidationPipeline] Validation completed in {combined_result.validation_time:.2f}s")
        
        return combined_result
    
    async def _create_mock_validation_result(
        self, 
        data: Dict[str, Any], 
        message: str
    ) -> ValidationResult:
        """Create a mock ValidationResult."""
        
        return ValidationResult(
            status=ValidationStatus.PARTIAL,
            cleaned_data=data,
            errors=[],
            warnings=[ValidationWarning(field_path="system", message=message)],
            removed_fields=[],
            statistics=ValidationStatistics()
        )
    
    async def _create_empty_mesh_result(self) -> Dict[str, Any]:
        """Create an empty MeSH validation result (used when disabled)."""
        return {
            "errors": [],
            "warnings": [],
            "normalized_data": {},  # This value is not used
            "validation_info": {"processed_fields": 0, "normalized_fields": 0}
        }
    
    async def _create_mock_mesh_result(
        self, 
        data: Dict[str, Any], 
        message: str
    ) -> Dict[str, Any]:
        """Create a mock MeSH validation result."""
        return {
            "errors": [],
            "warnings": [message],
            "normalized_data": data,
            "validation_info": {"processed_fields": 0, "normalized_fields": 0}
        }
    
    async def _validate_mesh_terms_async(
        self, 
        data: Dict[str, Any], 
        context: ValidationContext
    ) -> Dict[str, Any]:
        """Validate MeSH terms (asynchronous)."""
        
        # Extract fields requiring MeSH validation
        mesh_fields = self._extract_mesh_fields(data)
        print(f"[ValidationPipeline] Extracted MeSH fields: {mesh_fields.keys()}")
        
        if not mesh_fields:
            return {
                "errors": [],
                "warnings": [],
                "normalized_data": data,
                "validation_info": {"processed_fields": 0, "normalized_fields": 0}
            }
        
        # Parallel MeSH validation
        validation_tasks = []
        for field_path, terms in mesh_fields.items():
            if isinstance(terms, list):
                for term in terms:
                    if isinstance(term, str) and term.strip():
                        task = self.mesh_validator.validate_term_async(term.strip())
                        validation_tasks.append((field_path, term, task))
            elif isinstance(terms, str) and terms.strip():
                task = self.mesh_validator.validate_term_async(terms.strip())
                validation_tasks.append((field_path, terms, task))
        
        if not validation_tasks:
            return {
                "errors": [],
                "warnings": [],
                "normalized_data": data,
                "validation_info": {"processed_fields": 0, "normalized_fields": 0}
            }
        
        print(f"[ValidationPipeline] Starting MeSH validation for {len(validation_tasks)} terms...")
        print(f"[ValidationPipeline] Validation tasks: {validation_tasks}")
        # Wait for all MeSH validations to complete
        results = await asyncio.gather(
            *(task for _, _, task in validation_tasks),
            return_exceptions=True
        )
        
        # Process results
        errors = []
        warnings = []
        normalized_data = data.copy()
        normalized_count = 0
        
        for i, (field_path, original_term, _) in enumerate(validation_tasks):
            print(f"[ValidationPipeline] Processing result for {field_path}: {original_term}")
            result = results[i]
            
            if isinstance(result, Exception):
                print(f"[ValidationPipeline] MeSH validation error for '{original_term}' in {field_path}: {result}")
                errors.append(f"MeSH validation error for '{original_term}' in {field_path}: {result}")
                continue
                
            if not result.get("is_valid", False):
                print(f"[ValidationPipeline] Invalid MeSH term '{original_term}' in {field_path}")
                if self.config.strict_mesh_validation:
                    errors.append(f"Invalid MeSH term '{original_term}' in {field_path}")
                else:
                    warnings.append(f"Unverified MeSH term '{original_term}' in {field_path}")
            
            # Apply normalized term if available
            if result.get("normalized") and result.get("mesh_term"):
                print(f"[ValidationPipeline] Normalizing term '{original_term}' to '{result['mesh_term']}' in {field_path}")
                normalized_term = result["mesh_term"]
                if normalized_term != original_term:
                    self._apply_mesh_normalization(
                        normalized_data, field_path, original_term, normalized_term
                    )
                    normalized_count += 1
        
        return {
            "errors": errors,
            "warnings": warnings,
            "normalized_data": normalized_data,
            "validation_info": {
                "processed_fields": len(validation_tasks),
                "normalized_fields": normalized_count
            }
        }
    
    def _should_validate_mesh(self, field_key: str) -> bool:
        """Determine if a field requires MeSH validation."""
        field_lower = field_key.lower()
        
        # 1. Fields containing the word 'mesh'
        if 'mesh' in field_lower:
            print(f"[ValidationPipeline] MeSH validation required for field: {field_key}")
            return True
        
        # 2. Additionally include core medical term fields
        core_medical_fields = [
            'conditions', 'condition',
            'interventions', 'intervention', 
            'keywords'
        ]
        
        return any(field in field_lower for field in core_medical_fields)

    def _extract_mesh_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields requiring MeSH validation - only fields containing the keyword 'mesh' or core medical terms."""
        mesh_fields = {}
        
        def extract_recursive(obj: Any, path: str = ""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Check if the field requires MeSH validation
                    if self._should_validate_mesh(key):
                        if isinstance(value, (str, list)):
                            print(f"[ValidationPipeline] [_extract_mesh_fields] Extracting MeSH field: {current_path} = {value}")
                            mesh_fields[current_path] = value
                    
                    extract_recursive(value, current_path)
                    
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_recursive(item, f"{path}[{i}]")
        
        extract_recursive(data)
        return mesh_fields
    
    def _apply_mesh_normalization(
        self, 
        data: Dict[str, Any], 
        field_path: str, 
        original_term: str, 
        normalized_term: str
    ) -> None:
        """Apply normalized MeSH terms to data."""
        # Simple implementation - actual implementation may require more sophisticated path parsing
        path_parts = field_path.split('.')
        current = data
        
        try:
            for part in path_parts[:-1]:
                if '[' in part and ']' in part:
                    # Handle array index
                    key = part.split('[')[0]
                    index = int(part.split('[')[1].split(']')[0])
                    current = current[key][index]
                else:
                    current = current[part]
            
            # Apply normalized value to the last key
            last_key = path_parts[-1]
            if isinstance(current[last_key], str):
                if current[last_key] == original_term:
                    current[last_key] = normalized_term
            elif isinstance(current[last_key], list):
                for i, item in enumerate(current[last_key]):
                    if item == original_term:
                        current[last_key][i] = normalized_term
                        
        except (KeyError, IndexError, ValueError) as e:
            print(f"[ValidationPipeline] Failed to apply MeSH normalization for {field_path}: {e}")
    
    def _combine_validation_results(
        self, 
        fieldlist_result: ValidationResult, 
        mesh_result: Dict[str, Any],
        context: ValidationContext
    ) -> ValidationResult:
        """Combine FieldList and MeSH validation results."""
        
        # Combine errors and warnings - normalize all errors to ValidationError objects
        combined_errors = []
        combined_warnings = []
        
        # Handle FieldList errors - convert string errors to ValidationError objects
        for error in fieldlist_result.errors:
            if isinstance(error, ValidationError):
                combined_errors.append(error)
            elif isinstance(error, str):
                # Convert string errors to ValidationError objects
                combined_errors.append(self._convert_string_error_to_validation_error(error))
            else:
                print(f"[ValidationPipeline] Warning: Unknown error type: {type(error)}")
                combined_errors.append(ValidationError(
                    field_path="unknown",
                    message=str(error),
                    level=ValidationLevel.CRITICAL
                ))
        
        # Handle FieldList warnings
        for warning in fieldlist_result.warnings:
            if isinstance(warning, ValidationWarning):
                combined_warnings.append(warning)
            elif isinstance(warning, str):
                combined_warnings.append(ValidationWarning(
                    field_path="unknown",
                    message=warning
                ))
        
        # Convert MeSH errors to ValidationError objects
        for error_msg in mesh_result["errors"]:
            error = ValidationError(
                field_path="mesh_validation" if self.config.enable_mesh_validation else "system",
                message=error_msg,
                level=ValidationLevel.CRITICAL
            )
            combined_errors.append(error)
        
        # Convert MeSH warnings to ValidationWarning objects
        for warning_msg in mesh_result["warnings"]:
            # If MeSH is disabled, treat as system warning
            field_path = "mesh_validation" if self.config.enable_mesh_validation else "system"
            warning = ValidationWarning(
                field_path=field_path,
                message=warning_msg
            )
            combined_warnings.append(warning)
        
        # Integrate data (use data with MeSH normalization applied, use original data if empty result)
        final_data = mesh_result["normalized_data"] if mesh_result["normalized_data"] else fieldlist_result.cleaned_data
        
        # Determine overall validity - ensure all errors are now ValidationError objects
        has_critical_errors = any(error.level == ValidationLevel.CRITICAL for error in combined_errors)
        
        if has_critical_errors:
            status = ValidationStatus.FAILED
        elif combined_warnings or mesh_result["warnings"]:
            status = ValidationStatus.PARTIAL
        else:
            status = ValidationStatus.PASSED
        
        # Integrate statistics information
        from dataclasses import replace
        statistics = fieldlist_result.statistics
        
        if statistics:
            # Add new mesh fields to the dataclass
            try:
                # Create new dict with additional mesh fields
                stats_dict = {
                    'total_fields_input': statistics.total_fields_input,
                    'valid_fields': statistics.valid_fields,
                    'invalid_fields': statistics.invalid_fields,
                    'enum_violations': statistics.enum_violations,
                    'structure_violations': statistics.structure_violations,
                    'type_violations': statistics.type_violations,
                    'constraint_violations': statistics.constraint_violations,
                    'removed_fields': statistics.removed_fields,
                    'corrected_fields': statistics.corrected_fields,
                }
                
                # Create new ValidationStatistics object
                updated_statistics = ValidationStatistics(**stats_dict)
                
            except Exception as e:
                print(f"[ValidationPipeline] Error updating statistics: {e}")
                updated_statistics = statistics
        else:
            updated_statistics = ValidationStatistics()
        
        return ValidationResult(
            status=status,
            cleaned_data=final_data,
            errors=combined_errors,
            warnings=combined_warnings,
            removed_fields=fieldlist_result.removed_fields,
            statistics=updated_statistics
        )
    
    async def validate_streaming_data(
        self,
        data_stream: asyncio.Queue,
        context: Optional[ValidationContext] = None
    ) -> AsyncIterator[ValidationResult]:
        """Validate streaming data (for real-time validation)."""
        context = context or ValidationContext()
        
        while True:
            try:
                # Wait for data with timeout
                data_chunk = await asyncio.wait_for(
                    data_stream.get(), 
                    timeout=self.config.timeout_seconds
                )
                
                if data_chunk is None:  # Termination signal
                    break
                
                # Validate chunk
                result = await self.validate_extracted_data(data_chunk, context)
                yield result
                
                data_stream.task_done()
                
            except asyncio.TimeoutError:
                print("[ValidationPipeline] Streaming validation timeout")
                break
            except Exception as e:
                print(f"[ValidationPipeline] Streaming validation error: {e}")
                error_result = ValidationResult(
                    status=ValidationStatus.FAILED,
                    cleaned_data={},
                    errors=[ValidationError(
                        field_path="streaming",
                        message=f"Streaming validation error: {str(e)}",
                        level=ValidationLevel.CRITICAL
                    )],
                    warnings=[],
                    removed_fields=[],
                    statistics=ValidationStatistics()
                )
                yield error_result

    def _log_validation_details(self, session_id: str, result: ValidationResult, context: ValidationContext):
        """Log validation details (using detailed format)."""
        if not LOGGING_AVAILABLE:
            return
            
        logger = get_extraction_logger()
        pmc_id = session_id.split('_')[0] if '_' in session_id else "unknown"
        
        # Log errors
        for error in result.errors:
            if DETAILED_LOGGING_AVAILABLE:
                record = self._create_detailed_validation_record(
                    session_id, pmc_id, error, "error", context
                )
            else:
                record = ValidationRecord(
                    session_id=session_id,
                    pmc_id=pmc_id,
                    field_path=getattr(error, 'field_path', 'unknown'),
                    validation_type=self._determine_validation_type(error),
                    status="error",
                    original_value=getattr(error, 'original_value', None),
                    corrected_value=None,
                    error_message=getattr(error, 'message', str(error))
                )
            logger.log_validation_record(session_id, record)
        
        # Log warnings
        for warning in result.warnings:
            if DETAILED_LOGGING_AVAILABLE:
                record = self._create_detailed_validation_record(
                    session_id, pmc_id, warning, "warning", context
                )
            else:
                record = ValidationRecord(
                    session_id=session_id,
                    pmc_id=pmc_id,
                    field_path=getattr(warning, 'field_path', 'unknown'),
                    validation_type=self._determine_validation_type(warning),
                    status="warning",
                    original_value=getattr(warning, 'original_value', None),
                    corrected_value=getattr(warning, 'corrected_value', None),
                    warning_message=getattr(warning, 'message', str(warning))
                )
            logger.log_validation_record(session_id, record)
        
        # Log removed fields (indicates removal)
        for field_path in result.removed_fields:
            if DETAILED_LOGGING_AVAILABLE:
                record = DetailedValidationRecord(
                    session_id=session_id,
                    pmc_id=pmc_id,
                    field_path=field_path,
                    field_name=field_path.split('.')[-1] if '.' in field_path else field_path,
                    parent_path='.'.join(field_path.split('.')[:-1]) if '.' in field_path else None,
                    issue_type=ValidationIssueType.FIELD_REMOVED.value,
                    severity=ValidationSeverity.INFO.value,
                    validation_module="structure",
                    original_value="field_removed",
                    corrected_value=None,
                    error_message="Field removed during validation",
                    validation_timestamp=datetime.now().isoformat()
                )
            else:
                record = ValidationRecord(
                    session_id=session_id,
                    pmc_id=pmc_id,
                    field_path=field_path,
                    validation_type="structure",
                    status="corrected",
                    original_value="field_removed",
                    corrected_value=None,
                    warning_message="Field removed during validation"
                )
            logger.log_validation_record(session_id, record)
    
    def _create_detailed_validation_record(
        self, 
        session_id: str, 
        pmc_id: str, 
        issue, 
        status: str,
        context: ValidationContext
    ) -> DetailedValidationRecord:
        """Create a detailed validation record."""
        
        # Extract basic information
        field_path = getattr(issue, 'field_path', 'unknown')
        message = getattr(issue, 'message', str(issue))
        original_value = getattr(issue, 'original_value', getattr(issue, 'actual_value', None))
        corrected_value = getattr(issue, 'corrected_value', None)
        
        # Extract additional information from ValidationError object
        expected_value = getattr(issue, 'expected_value', None)
        actual_value = getattr(issue, 'actual_value', None)
        
        # Separate field name and parent path
        if '.' in field_path and field_path != 'unknown':
            path_parts = field_path.split('.')
            field_name = path_parts[-1]
            parent_path = '.'.join(path_parts[:-1])
        else:
            field_name = field_path
            parent_path = None
        
        # Determine validation module
        validation_module = self._determine_validation_type(issue)
        
        # Classify issue type (more accurate classification)
        if ISSUE_CLASSIFICATION_AVAILABLE:
            issue_type = classify_validation_issue(message, field_path, validation_module)
            severity = determine_severity(issue_type)
        else:
            # Improved basic classification
            issue_type_str, severity_str = self._classify_validation_issue_basic(message, field_path, validation_module)
        
        # Extract expected value and type (using ValidationError object)
        expected_values = None
        expected_type = None
        
        if expected_value:
            if isinstance(expected_value, list):
                expected_values = json.dumps(expected_value)
            else:
                expected_type = str(expected_value)
        elif "Valid values:" in message:
            # Extract values from message like "Valid values: A, B, C"
            parts = message.split("Valid values:")
            if len(parts) > 1:
                values_str = parts[1].strip()
                expected_values = json.dumps([v.strip() for v in values_str.split(',')])
        
        if "expected" in message.lower() and "got" in message.lower():
            # Extract expected type from mismatch message
            words = message.lower().split()
            if "expected" in words:
                idx = words.index("expected")
                if idx + 1 < len(words):
                    expected_type = words[idx + 1].replace(',', '').replace('.', '')
        
        # Generate suggestion
        if ISSUE_CLASSIFICATION_AVAILABLE:
            suggestion = self._generate_suggestion(issue_type, message, expected_values)
            issue_type_str = issue_type.value
            severity_str = severity.value
        else:
            suggestion = self._generate_suggestion_basic(issue_type_str, message, expected_values)
        
        return DetailedValidationRecord(
            session_id=session_id,
            pmc_id=pmc_id,
            field_path=field_path,
            field_name=field_name,
            parent_path=parent_path,
            issue_type=issue_type_str,
            severity=severity_str,
            validation_module=validation_module,
            original_value=original_value if original_value is not None else actual_value,
            expected_type=expected_type,
            expected_values=expected_values,
            corrected_value=corrected_value,
            error_message=message,
            suggestion=suggestion,
            validation_timestamp=datetime.now().isoformat()
        )
    
    def _generate_suggestion(self, issue_type, message: str, expected_values: str = None) -> str:
        """Generate suggestions based on issue type."""
        
        if not ISSUE_CLASSIFICATION_AVAILABLE:
            return "Review the field according to schema requirements"
        
        if issue_type == ValidationIssueType.ENUM_VIOLATION and expected_values:
            return f"Use one of the allowed values: {expected_values}"
        elif issue_type == ValidationIssueType.UNDEFINED_FIELD:
            return "Remove this field or check if it belongs to a different section"
        elif issue_type == ValidationIssueType.TYPE_MISMATCH:
            return "Check the data type and format according to the schema"
        elif issue_type == ValidationIssueType.MESH_UNVERIFIED:
            return "Verify the medical term against official MeSH database"
        elif issue_type == ValidationIssueType.ARRAY_TYPE_VIOLATION:
            return "Convert single value to array format"
        elif issue_type == ValidationIssueType.SINGLE_TYPE_VIOLATION:
            return "Use only the first value or combine multiple values"
        else:
            return "Review the field according to schema requirements"
    
    def _determine_validation_type(self, issue) -> str:
        """Determine validation type from issue object."""
        message = getattr(issue, 'message', str(issue)).lower()
        
        if 'mesh' in message or 'medical subject' in message:
            return "mesh"
        elif 'enum' in message or 'allowed values' in message:
            return "fieldlist"
        elif 'structure' in message or 'schema' in message:
            return "structure"
        elif 'type' in message or 'format' in message:
            return "type"
        else:
            return "fieldlist"  # Default
    
    def _classify_validation_issue_basic(self, message: str, field_path: str, validation_module: str) -> tuple:
        """Basic validation issue classification (used when validation_issue_types is unavailable)."""
        message_lower = message.lower()
        
        # 1. Enum violation
        if ("invalid enum value" in message_lower or 
            "valid values:" in message_lower or
            "allowed values:" in message_lower):
            return "enum_violation", "error"
        
        # 2. Field not defined in schema
        if ("field not in schema" in message_lower or
            "not defined in schema" in message_lower or
            "undefined field" in message_lower):
            return "undefined_field", "warning"
        
        # 3. Type mismatch
        if ("expected" in message_lower and "got" in message_lower) or "type mismatch" in message_lower:
            return "type_mismatch", "error"
        
        # 4. Array type violation
        if ("expected array" in message_lower and "got" in message_lower):
            return "array_type_violation", "error"
        elif ("expected string" in message_lower or "expected object" in message_lower) and "array" in message_lower:
            return "single_type_violation", "error"
        
        # 5. MeSH validation related
        if validation_module.lower() == "mesh" or "mesh" in message_lower:
            if "invalid" in message_lower or "not found" in message_lower:
                return "mesh_invalid", "error"
            else:
                return "mesh_unverified", "warning"
        
        # 6. System error
        if (field_path in ["_system", "system"] or 
            "system error" in message_lower or
            "validation system error" in message_lower):
            return "system_error", "critical"
        
        # 7. Field removed
        if "field removed" in message_lower or "removed during validation" in message_lower:
            return "field_removed", "info"
        
        # 8. Other validation errors
        return "validation_error", "error"
    
    def _generate_suggestion_basic(self, issue_type: str, message: str, expected_values: str = None) -> str:
        """Basic suggestion generation (used when validation_issue_types is unavailable)."""
        
        if issue_type == "enum_violation" and expected_values:
            return f"Use one of the allowed values: {expected_values}"
        elif issue_type == "undefined_field":
            return "Remove this field or check if it belongs to a different section of the schema"
        elif issue_type == "type_mismatch":
            return "Check the data type and format according to the schema requirements"
        elif issue_type == "array_type_violation":
            return "Convert single value to array format or provide multiple values as an array"
        elif issue_type == "single_type_violation":
            return "Use only the first value or combine multiple values into a single value"
        elif issue_type == "mesh_invalid":
            return "Verify the medical term against official MeSH database or use a recognized medical term"
        elif issue_type == "mesh_unverified":
            return "Consider verifying this medical term against the MeSH database for accuracy"
        elif issue_type == "system_error":
            return "Contact system administrator - this indicates an internal validation error"
        elif issue_type == "field_removed":
            return "Field was automatically removed due to schema non-compliance"
        else:
            return "Review the field according to schema requirements and documentation"
    
    def _convert_string_error_to_validation_error(self, error_message: str) -> ValidationError:
        """Convert string error to ValidationError object (including field path and type classification)."""
        
        # Extract field path from error message
        field_path = "unknown"
        actual_value = None
        expected_value = None
        
        if ":" in error_message:
            # Extract field_path from "field_path: error description" format
            parts = error_message.split(":", 1)
            potential_field_path = parts[0].strip()
            
            # Check if it's a valid field path (contains dot or CamelCase/camelCase)
            if ("." in potential_field_path or 
                any(c.isupper() for c in potential_field_path) or
                potential_field_path.lower() in ["system", "_system", "validation"]):
                field_path = potential_field_path
                error_message = parts[1].strip()
        
        # Extract actual value (part starting with keywords like got, actual)
        if " got " in error_message.lower():
            parts = error_message.lower().split(" got ")
            if len(parts) > 1:
                actual_part = parts[1].strip()
                # Extract type information (e.g., "got <class 'str'>" -> "str")
                if actual_part.startswith("<class '") and actual_part.endswith("'>"):
                    actual_value = actual_part[8:-2]
                else:
                    actual_value = actual_part.split()[0] if actual_part else None
        
        # Extract expected value (Valid values: format)
        if "Valid values:" in error_message:
            parts = error_message.split("Valid values:")
            if len(parts) > 1:
                values_str = parts[1].strip()
                expected_value = [v.strip() for v in values_str.split(',')]
        elif "Expected " in error_message:
            parts = error_message.split("Expected ")
            if len(parts) > 1:
                expected_part = parts[1].split(",")[0].split(".")[0].strip()
                expected_value = expected_part
        
        # Determine validation level (for critical errors)
        level = ValidationLevel.CRITICAL
        if any(keyword in error_message.lower() for keyword in ["warning", "unverified", "field not in schema"]):
            level = ValidationLevel.WARNING
        
        return ValidationError(
            field_path=field_path,
            message=error_message,
            level=level,
            expected_value=expected_value,
            actual_value=actual_value
        )

# Synchronous wrapper function for legacy support (temporarily maintained)
def validate_clinical_trial_data_unified(
    data: Dict[str, Any],
    config: Optional[ValidationConfig] = None
) -> ValidationResult:
    """Synchronous version of the unified validation function (temporarily maintained for testing)."""
    pipeline = ValidationPipeline(config)
    return asyncio.run(pipeline.validate_extracted_data(data))
