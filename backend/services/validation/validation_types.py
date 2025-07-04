"""
Definition of Validation System Types

Defines all validation-related types and result classes.
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ValidationLevel(Enum):
    """Validation levels"""
    CRITICAL = "critical"  # Reject data on validation failure
    WARNING = "warning"   # Display warning, preserve data
    INFO = "info"         # Informational message


class ValidationStatus(Enum):
    """Validation statuses"""
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some validations failed, some succeeded


@dataclass
class FieldValidationResult:
    """Validation result for an individual field"""
    field_path: str
    is_valid: bool
    original_value: Any
    cleaned_value: Any
    error_message: Optional[str] = None
    warning_message: Optional[str] = None
    applied_fixes: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.applied_fixes is None:
            self.applied_fixes = []


@dataclass
class ValidationError:
    """Individual validation error"""
    field_path: str
    message: str
    level: ValidationLevel
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    suggestions: Optional[List[str]] = None


@dataclass
class ValidationWarning:
    """Individual validation warning"""
    field_path: str
    message: str
    original_value: Optional[Any] = None
    corrected_value: Optional[Any] = None


@dataclass
class ValidationStatistics:
    """Validation statistics"""
    total_fields_input: int = 0
    valid_fields: int = 0
    invalid_fields: int = 0
    enum_violations: int = 0
    structure_violations: int = 0
    type_violations: int = 0
    constraint_violations: int = 0
    removed_fields: int = 0
    corrected_fields: int = 0


@dataclass
class ValidationResult:
    """Comprehensive validation result"""
    status: ValidationStatus
    cleaned_data: Dict[str, Any]
    errors: List[ValidationError]
    warnings: List[ValidationWarning]
    removed_fields: List[str]
    statistics: ValidationStatistics
    validation_time: float = 0.0
    validator_name: str = ""
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed"""
        return self.status == ValidationStatus.PASSED
    
    @property
    def has_critical_errors(self) -> bool:
        """Check if there are critical errors"""
        return any(error.level == ValidationLevel.CRITICAL for error in self.errors)
    
    def add_error(self, field_path: str, message: str, 
                  level: ValidationLevel = ValidationLevel.CRITICAL,
                  expected_value: Any = None, actual_value: Any = None):
        """Add an error"""
        error = ValidationError(
            field_path=field_path,
            message=message,
            level=level,
            expected_value=expected_value,
            actual_value=actual_value
        )
        self.errors.append(error)
        
        if level == ValidationLevel.CRITICAL:
            self.status = ValidationStatus.FAILED
        elif self.status == ValidationStatus.PASSED:
            self.status = ValidationStatus.PARTIAL
    
    def add_warning(self, field_path: str, message: str,
                    original_value: Any = None, corrected_value: Any = None):
        """Add a warning"""
        warning = ValidationWarning(
            field_path=field_path,
            message=message,
            original_value=original_value,
            corrected_value=corrected_value
        )
        self.warnings.append(warning)


@dataclass
class ValidationConfig:
    """Validation configuration"""
    strict_mode: bool = True
    allow_unknown_fields: bool = False
    auto_fix_enums: bool = True
    auto_truncate_long_fields: bool = True
    mesh_api_timeout: int = 10
    max_field_length_ratio: float = 1.1
    parallel_validation: bool = True
    cache_validation_results: bool = True
    
    # Enable/disable validation modules
    enable_fieldlist_validation: bool = True
    enable_mesh_validation: bool = False
    enable_auto_fix: bool = True
    strict_mesh_validation: bool = False
    max_parallel_validations: int = 10
    
    # Field-specific settings
    required_fields_strict: bool = False
    enum_case_sensitive: bool = True
    date_format_strict: bool = False
    
    # Performance settings
    max_concurrent_validations: int = 5
    validation_timeout: int = 30
    timeout_seconds: int = 30


class ValidatorType(Enum):
    """Validator types"""
    FIELDLIST = "fieldlist"
    MESH = "mesh"
    COMBINED = "combined"


@dataclass
class ValidationContext:
    """Validation context"""
    source_type: str = "UNKNOWN"
    source_file: Optional[str] = None
    extraction_timestamp: Optional[float] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# Common type aliases
FieldPath = str
FieldValue = Any
ValidationData = Dict[str, Any]
EnumMapping = Dict[str, List[str]]
FieldSchema = Dict[str, Any]
