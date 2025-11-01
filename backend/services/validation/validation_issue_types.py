"""
Definition of Validation Issue Types

Defines all possible error types that can occur in the validation system in a detailed manner.
"""

from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass


class ValidationIssueType(Enum):
    """Detailed validation issue types"""
    
    # 1. Field existence-related
    UNDEFINED_FIELD = "undefined_field"           # Field not defined in the schema
    MISSING_REQUIRED_FIELD = "missing_required"   # Missing required field
    
    # 2. Data type-related
    TYPE_MISMATCH = "type_mismatch"               # Mismatch with expected type (e.g., string vs number)
    STRUCTURE_MISMATCH = "structure_mismatch"     # Structural mismatch (e.g., object vs array)
    
    # 3. Value constraints
    ENUM_VIOLATION = "enum_violation"             # Invalid enum value
    FORMAT_VIOLATION = "format_violation"         # Format error (e.g., date, URL)
    LENGTH_VIOLATION = "length_violation"         # Length constraint violation
    RANGE_VIOLATION = "range_violation"           # Numeric range violation
    PATTERN_VIOLATION = "pattern_violation"       # Regex pattern violation
    
    # 4. Array/List-related
    ARRAY_TYPE_VIOLATION = "array_type_violation" # Expected array but got a single value
    SINGLE_TYPE_VIOLATION = "single_type_violation" # Expected single value but got an array
    ARRAY_LENGTH_VIOLATION = "array_length_violation" # Array length constraint violation
    
    # 5. Medical term-related
    MESH_INVALID = "mesh_invalid"                 # Invalid MeSH term
    MESH_UNVERIFIED = "mesh_unverified"           # Unverified MeSH term
    
    # 6. System errors
    VALIDATION_SYSTEM_ERROR = "system_error"      # Internal validation system error
    TIMEOUT_ERROR = "timeout_error"               # Validation timeout
    
    # 7. Data quality
    DUPLICATE_VALUE = "duplicate_value"           # Duplicate value
    INCONSISTENT_DATA = "inconsistent_data"        # Inconsistent data
    
    # 8. Processing results
    FIELD_REMOVED = "field_removed"               # Field removed
    FIELD_CORRECTED = "field_corrected"           # Field corrected
    FIELD_NORMALIZED = "field_normalized"         # Field normalized


class ValidationSeverity(Enum):
    """Severity levels of validation issues"""
    CRITICAL = "critical"    # Errors that make the data unusable
    ERROR = "error"          # Severe errors requiring correction
    WARNING = "warning"      # Warnings; data is usable but requires attention
    INFO = "info"            # Informational; no issues
    

def classify_validation_issue(
    error_message: str, 
    field_path: str = "", 
    validation_type: str = ""
) -> ValidationIssueType:
    """Classify issue type based on error message"""
    
    message_lower = error_message.lower()
    
    # 1. Field existence
    if "field not in schema" in message_lower or "not defined" in message_lower:
        return ValidationIssueType.UNDEFINED_FIELD
    if "required field" in message_lower or "missing" in message_lower:
        return ValidationIssueType.MISSING_REQUIRED_FIELD
    
    # 2. Data type
    if "type mismatch" in message_lower or "expected" in message_lower and "got" in message_lower:
        return ValidationIssueType.TYPE_MISMATCH
    if "should be array" in message_lower or "should be object" in message_lower:
        return ValidationIssueType.STRUCTURE_MISMATCH
    
    # 3. Value constraints
    if "invalid enum value" in message_lower or "valid values:" in message_lower:
        return ValidationIssueType.ENUM_VIOLATION
    if "invalid format" in message_lower or "format error" in message_lower:
        return ValidationIssueType.FORMAT_VIOLATION
    if "too long" in message_lower or "exceeds maximum length" in message_lower:
        return ValidationIssueType.LENGTH_VIOLATION
    if "out of range" in message_lower or "must be between" in message_lower:
        return ValidationIssueType.RANGE_VIOLATION
    if "pattern" in message_lower or "regex" in message_lower:
        return ValidationIssueType.PATTERN_VIOLATION
    
    # 4. Array-related
    if "should be array" in message_lower and "single" in message_lower:
        return ValidationIssueType.ARRAY_TYPE_VIOLATION
    if "should be single" in message_lower and "array" in message_lower:
        return ValidationIssueType.SINGLE_TYPE_VIOLATION
    if "array length" in message_lower:
        return ValidationIssueType.ARRAY_LENGTH_VIOLATION
    
    # 5. MeSH-related
    if validation_type == "mesh":
        if "invalid mesh" in message_lower or "not found" in message_lower:
            return ValidationIssueType.MESH_INVALID
        if "unverified" in message_lower:
            return ValidationIssueType.MESH_UNVERIFIED
    
    # 6. System errors
    if "system error" in message_lower or "internal error" in message_lower:
        return ValidationIssueType.VALIDATION_SYSTEM_ERROR
    if "timeout" in message_lower:
        return ValidationIssueType.TIMEOUT_ERROR
    
    # 7. Processing results
    if "field removed" in message_lower:
        return ValidationIssueType.FIELD_REMOVED
    if "field corrected" in message_lower or "auto-corrected" in message_lower:
        return ValidationIssueType.FIELD_CORRECTED
    if "normalized" in message_lower:
        return ValidationIssueType.FIELD_NORMALIZED
    
    # Default: Decide based on validation type
    if validation_type == "fieldlist":
        return ValidationIssueType.ENUM_VIOLATION  # Most common fieldlist error
    elif validation_type == "structure":
        return ValidationIssueType.UNDEFINED_FIELD
    elif validation_type == "type":
        return ValidationIssueType.TYPE_MISMATCH
    else:
        return ValidationIssueType.VALIDATION_SYSTEM_ERROR


def determine_severity(issue_type: ValidationIssueType) -> ValidationSeverity:
    """Determine severity based on issue type"""
    
    critical_issues = {
        ValidationIssueType.MISSING_REQUIRED_FIELD,
        ValidationIssueType.VALIDATION_SYSTEM_ERROR,
        ValidationIssueType.TIMEOUT_ERROR
    }
    
    error_issues = {
        ValidationIssueType.TYPE_MISMATCH,
        ValidationIssueType.STRUCTURE_MISMATCH,
        ValidationIssueType.ENUM_VIOLATION,
        ValidationIssueType.FORMAT_VIOLATION,
        ValidationIssueType.RANGE_VIOLATION,
        ValidationIssueType.ARRAY_TYPE_VIOLATION,
        ValidationIssueType.SINGLE_TYPE_VIOLATION,
        ValidationIssueType.MESH_INVALID
    }
    
    warning_issues = {
        ValidationIssueType.UNDEFINED_FIELD,
        ValidationIssueType.LENGTH_VIOLATION,
        ValidationIssueType.PATTERN_VIOLATION,
        ValidationIssueType.ARRAY_LENGTH_VIOLATION,
        ValidationIssueType.MESH_UNVERIFIED,
        ValidationIssueType.DUPLICATE_VALUE,
        ValidationIssueType.INCONSISTENT_DATA
    }
    
    info_issues = {
        ValidationIssueType.FIELD_REMOVED,
        ValidationIssueType.FIELD_CORRECTED,
        ValidationIssueType.FIELD_NORMALIZED
    }
    
    if issue_type in critical_issues:
        return ValidationSeverity.CRITICAL
    elif issue_type in error_issues:
        return ValidationSeverity.ERROR
    elif issue_type in warning_issues:
        return ValidationSeverity.WARNING
    else:
        return ValidationSeverity.INFO
