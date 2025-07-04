"""
Asynchronous FieldList Validator

Asynchronous validator based on ClinicalTrials.gov FieldList.json and Enums.json
Supports performance optimization and parallel processing
"""

import json
import re
import asyncio
import time
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor

from .validation_types import (
    ValidationResult, ValidationError, ValidationWarning, ValidationStatistics,
    ValidationLevel, ValidationStatus, ValidationConfig, FieldPath, ValidationData
)

logger = logging.getLogger(__name__)


class AsyncFieldListValidator:
    """Asynchronous FieldList Validator"""
    
    def __init__(self, fieldlist_file: str, enums_file: str, config: ValidationConfig = None):
        """
        Args:
            fieldlist_file: Path to FieldList.json file
            enums_file: Path to Enums.json file
            config: Validation configuration
        """
        self.fieldlist_file = fieldlist_file
        self.enums_file = enums_file
        self.config = config or ValidationConfig()
        
        # Initialize
        self.fieldlist_data = []
        self.enums_data = []
        self.field_schema = {}
        self.enum_mapping = {}
        self._initialized = False
        self._init_lock = asyncio.Lock()
        
        # For performance optimization
        self._validation_cache = {}
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_validations)

    async def initialize(self):
        """Asynchronous initialization"""
        if self._initialized:
            return
        
        async with self._init_lock:
            if self._initialized:
                return
            
            try:
                # Execute file loading in a separate thread
                loop = asyncio.get_event_loop()
                
                fieldlist_task = loop.run_in_executor(
                    self._executor, self._load_fieldlist
                )
                enums_task = loop.run_in_executor(
                    self._executor, self._load_enums
                )
                
                self.fieldlist_data, self.enums_data = await asyncio.gather(
                    fieldlist_task, enums_task
                )
                
                # Build schema
                schema_task = loop.run_in_executor(
                    self._executor, self._build_field_schema
                )
                enum_task = loop.run_in_executor(
                    self._executor, self._build_enum_mapping
                )
                
                self.field_schema, self.enum_mapping = await asyncio.gather(
                    schema_task, enum_task
                )
                
                self._initialized = True
                logger.info(f"AsyncFieldListValidator initialized: {len(self.field_schema)} fields, "
                           f"{len(self.enum_mapping)} enum types")
                
            except Exception as e:
                logger.error(f"Failed to initialize AsyncFieldListValidator: {e}")
                raise

    def _load_fieldlist(self) -> List[Dict]:
        """Load FieldList.json (synchronous)"""
        try:
            with open(self.fieldlist_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load FieldList.json: {e}")
            return []

    def _load_enums(self) -> List[Dict]:
        """Load Enums.json (synchronous)"""
        try:
            with open(self.enums_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load Enums.json: {e}")
            return []

    def _build_field_schema(self) -> Dict[str, Dict]:
        """Build field schema structure from FieldList.json (synchronous)"""
        schema = {}
        
        def extract_fields(node, path="", parent_type=""):
            """Recursively extract field information"""
            if isinstance(node, dict):
                if 'name' in node:
                    field_name = node['name']
                    full_path = f"{path}.{field_name}" if path else field_name
                    
                    schema[full_path] = {
                        'name': field_name,
                        'title': node.get('title', ''),
                        'sourceType': node.get('sourceType', ''),
                        'type': node.get('type', ''),
                        'maxChars': node.get('maxChars'),
                        'rules': node.get('rules', ''),
                        'isEnum': node.get('isEnum', False),
                        'description': node.get('description', ''),
                        'synonyms': node.get('synonyms', False),
                        'path': full_path,
                        'parent_type': parent_type
                    }
                    
                    # If there are children, process recursively
                    if 'children' in node:
                        current_type = node.get('type', parent_type)
                        for child in node['children']:
                            extract_fields(child, full_path, current_type)
                            
            elif isinstance(node, list):
                for item in node:
                    extract_fields(item, path, parent_type)
        
        extract_fields(self.fieldlist_data)
        return schema

    def _build_enum_mapping(self) -> Dict[str, List[str]]:
        """Map possible values for each enum type from Enums.json (synchronous)"""
        mapping = {}
        for enum_data in self.enums_data:
            enum_type = enum_data.get('type', '')
            values = [item['value'] for item in enum_data.get('values', [])]
            mapping[enum_type] = values
        return mapping

    async def validate_async(self, data: ValidationData) -> ValidationResult:
        """
        Asynchronous data validation

        Args:
            data: Data to validate

        Returns:
            ValidationResult: Validation result
        """
        start_time = time.time()
        
        # Check initialization
        await self.initialize()
        
        result = ValidationResult(
            status=ValidationStatus.PASSED,
            cleaned_data={},
            errors=[],
            warnings=[],
            removed_fields=[],
            statistics=ValidationStatistics(),
            validator_name="AsyncFieldListValidator"
        )
        
        try:
            # Parallel section validation
            if self.config.parallel_validation and len(data) > 1:
                cleaned_data = await self._validate_sections_parallel(data, result)
            else:
                cleaned_data = await self._validate_sections_sequential(data, result)
            
            result.cleaned_data = cleaned_data
            
            # Determine final status
            if result.has_critical_errors:
                result.status = ValidationStatus.FAILED
            elif result.errors or result.warnings:
                result.status = ValidationStatus.PARTIAL
            else:
                result.status = ValidationStatus.PASSED
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            result.add_error("_system", f"Validation system error: {e}", ValidationLevel.CRITICAL)
            result.status = ValidationStatus.FAILED
        
        result.validation_time = time.time() - start_time
        
        logger.info(f"Async validation completed in {result.validation_time:.3f}s: "
                   f"{result.statistics.valid_fields}/{result.statistics.total_fields_input} fields valid")
        
        return result
    
    async def _validate_sections_parallel(self, data: ValidationData, result: ValidationResult) -> Dict[str, Any]:
        """Parallel section validation"""
        tasks = []
        sections = list(data.items())
        
        # Create tasks for each section
        for section_name, section_data in sections:
            if isinstance(section_data, dict):
                task = asyncio.create_task(
                    self._validate_section_async(section_name, section_data)
                )
                tasks.append((section_name, task))
        
        # Execute in parallel
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        cleaned_data = {}
        for i, (section_name, _) in enumerate(tasks):
            section_result = results[i]
            
            if isinstance(section_result, Exception):
                logger.error(f"Section {section_name} validation failed: {section_result}")
                result.add_error(section_name, f"Section validation error: {section_result}")
                continue
            
            # Merge results - convert string errors to ValidationError objects
            cleaned_data[section_name] = section_result['cleaned_data']
            
            # Convert and add errors
            for error_msg in section_result['errors']:
                if isinstance(error_msg, str):
                    # Convert string error to ValidationError (including field path extraction)
                    converted_error = self._convert_string_to_validation_error(error_msg)
                    result.errors.append(converted_error)
                else:
                    result.errors.append(error_msg)
            
            # Convert and add warnings  
            for warning_msg in section_result['warnings']:
                if isinstance(warning_msg, str):
                    warning = ValidationWarning(field_path="unknown", message=warning_msg)
                    result.warnings.append(warning)
                else:
                    result.warnings.append(warning_msg)
                    
            result.removed_fields.extend(section_result['removed_fields'])
            
            # Merge statistics
            for key in result.statistics.__dict__:
                current_value = getattr(result.statistics, key)
                section_value = section_result['statistics'].get(key, 0)
                setattr(result.statistics, key, current_value + section_value)
        
        return cleaned_data
    
    async def _validate_sections_sequential(self, data: ValidationData, result: ValidationResult) -> Dict[str, Any]:
        """Sequential section validation"""
        cleaned_data = {}
        
        for section_name, section_data in data.items():
            if isinstance(section_data, dict):
                section_result = await self._validate_section_async(section_name, section_data)
                
                cleaned_data[section_name] = section_result['cleaned_data']
                
                # Convert and add errors
                for error_msg in section_result['errors']:
                    if isinstance(error_msg, str):
                        # Convert string error to ValidationError (including field path extraction)
                        converted_error = self._convert_string_to_validation_error(error_msg)
                        result.errors.append(converted_error)
                    else:
                        result.errors.append(error_msg)
                
                # Convert and add warnings  
                for warning_msg in section_result['warnings']:
                    if isinstance(warning_msg, str):
                        warning = ValidationWarning(field_path="unknown", message=warning_msg)
                        result.warnings.append(warning)
                    else:
                        result.warnings.append(warning_msg)
                        
                result.removed_fields.extend(section_result['removed_fields'])
                
                # Merge statistics
                for key in result.statistics.__dict__:
                    current_value = getattr(result.statistics, key)
                    section_value = section_result['statistics'].get(key, 0)
                    setattr(result.statistics, key, current_value + section_value)
        
        return cleaned_data
    
    async def _validate_section_async(self, section_name: str, section_data: Dict[str, Any]) -> Dict[str, Any]:
        """Asynchronous section validation"""
        loop = asyncio.get_event_loop()
        
        # Execute CPU-intensive tasks in a separate thread
        return await loop.run_in_executor(
            self._executor, self._validate_section_sync, section_name, section_data
        )
    
    def _validate_section_sync(self, section_name: str, section_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous section validation (reuse existing logic)"""
        result = {
            'cleaned_data': {},
            'errors': [],
            'warnings': [],
            'removed_fields': [],
            'statistics': {
                'total_fields_input': 0,
                'valid_fields': 0,
                'invalid_fields': 0,
                'enum_violations': 0,
                'structure_violations': 0
            }
        }
        
        # Find schema fields matching the section
        section_schema = {path: schema for path, schema in self.field_schema.items() 
                         if path.startswith(section_name) or any(section_name.lower() in path.lower() 
                         for part in path.split('.'))}
        
        if not section_schema:
            result['warnings'].append(f"No schema found for section: {section_name}")
            result['cleaned_data'] = section_data
            return result
        
        # Validate recursively
        result['cleaned_data'] = self._validate_object_sync(
            section_data, section_name, section_schema, result
        )
        
        return result
    
    def _validate_object_sync(self, obj: Any, path: str, schema_subset: Dict[str, Dict], 
                             result: Dict[str, Any]) -> Any:
        """Recursively validate object (synchronous)"""
        if isinstance(obj, dict):
            cleaned_obj = {}
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                result['statistics']['total_fields_input'] += 1
                
                # Find schema for the field
                field_schema = self._find_field_schema_sync(current_path, schema_subset)
                
                if field_schema:
                    # Validate field type and value
                    validation_result = self._validate_field_sync(
                        key, value, field_schema, current_path
                    )
                    
                    if validation_result['valid']:
                        validated_value = validation_result['value']
                        
                        # If array type, validate each item
                        field_type = field_schema.get('type', '')
                        if field_type.endswith('[]') and isinstance(validated_value, list):
                            cleaned_array = []
                            for i, item in enumerate(validated_value):
                                if isinstance(item, dict):
                                    cleaned_item = self._validate_object_sync(
                                        item, current_path, schema_subset, result
                                    )
                                    cleaned_array.append(cleaned_item)
                                else:
                                    cleaned_array.append(item)
                            cleaned_obj[key] = cleaned_array
                        elif isinstance(validated_value, (dict, list)):
                            # Recursively validate nested structures
                            cleaned_obj[key] = self._validate_object_sync(
                                validated_value, current_path, schema_subset, result
                            )
                        else:
                            cleaned_obj[key] = validated_value
                        result['statistics']['valid_fields'] += 1
                    else:
                        result['errors'].extend(validation_result['errors'])
                        result['warnings'].extend(validation_result['warnings'])
                        result['removed_fields'].append(current_path)
                        result['statistics']['invalid_fields'] += 1
                        
                        if validation_result.get('enum_violation'):
                            result['statistics']['enum_violations'] += 1
                        if validation_result.get('structure_violation'):
                            result['statistics']['structure_violations'] += 1
                else:
                    # Handle fields not in schema
                    if self.config.allow_unknown_fields:
                        cleaned_obj[key] = value
                        result['warnings'].append(f"Unknown field preserved: {current_path}")
                    else:
                        result['warnings'].append(f"Field not in schema: {current_path}")
                        result['removed_fields'].append(current_path)
                        result['statistics']['invalid_fields'] += 1
                        result['statistics']['structure_violations'] += 1
            
            return cleaned_obj
            
        elif isinstance(obj, list):
            cleaned_list = []
            for i, item in enumerate(obj):
                cleaned_item = self._validate_object_sync(item, path, schema_subset, result)
                if cleaned_item is not None:
                    cleaned_list.append(cleaned_item)
            return cleaned_list
        
        else:
            return obj
    
    def _find_field_schema_sync(self, path: str, schema_subset: Dict[str, Dict]) -> Optional[Dict]:
        """Find field schema for the given path (synchronous)"""
        # Try exact match first
        if path in schema_subset:
            return schema_subset[path]
        
        # Try partial match (remove array index)
        normalized_path = re.sub(r'\[\d+\]', '', path)
        if normalized_path in schema_subset:
            return schema_subset[normalized_path]
        
        # Try match by field name (improved context matching)
        field_name = path.split('.')[-1]
        candidates = []
        
        for schema_path, schema_data in schema_subset.items():
            if schema_data['name'] == field_name:
                context_score = self._calculate_context_score(path, schema_path)
                candidates.append((context_score, schema_data))
        
        if candidates:
            # Return schema with highest context score
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
        
        return None
    
    def _calculate_context_score(self, data_path: str, schema_path: str) -> float:
        """Calculate context matching score (improved algorithm)"""
        data_parts = data_path.lower().split('.')
        schema_parts = schema_path.lower().split('.')
        
        # Count exact matches
        exact_matches = len(set(data_parts) & set(schema_parts))
        
        # Sequence match bonus
        sequence_bonus = 0
        for i in range(min(len(data_parts), len(schema_parts))):
            if data_parts[i] == schema_parts[i]:
                sequence_bonus += 1
            else:
                break
        
        # Length similarity
        length_similarity = 1 - abs(len(data_parts) - len(schema_parts)) / max(len(data_parts), len(schema_parts))
        
        # Final score (0-1 range)
        score = (exact_matches * 0.4 + sequence_bonus * 0.4 + length_similarity * 0.2) / max(len(data_parts), len(schema_parts))
        return min(score, 1.0)
    
    def _validate_field_sync(self, field_name: str, value: Any, field_schema: Dict, 
                            path: str) -> Dict[str, Any]:
        """Validate individual field (synchronous)"""
        result = {
            'valid': True,
            'value': value,
            'errors': [],
            'warnings': [],
            'enum_violation': False,
            'structure_violation': False
        }
        
        source_type = field_schema.get('sourceType', '')
        field_type = field_schema.get('type', '')
        max_chars = field_schema.get('maxChars')
        is_enum = field_schema.get('isEnum', False)
        rules = field_schema.get('rules', '')
        
        # Array type handling
        if field_type.endswith('[]'):
            if not isinstance(value, list):
                if value is not None:
                    if self.config.auto_fix_enums:
                        result['warnings'].append(f"{path}: Converting {type(value).__name__} to array")
                        result['value'] = [value] if value is not None else []
                    else:
                        result['errors'].append(f"{path}: Expected array, got {type(value).__name__}")
                        result['valid'] = False
                        result['structure_violation'] = True
            return result
        
        # Type validation
        if source_type == 'TEXT' and not isinstance(value, str):
            if value is not None:
                result['errors'].append(f"{path}: Expected string, got {type(value).__name__}")
                result['valid'] = False
                result['structure_violation'] = True
        
        elif source_type == 'BOOLEAN' and not isinstance(value, bool):
            if value is not None:
                result['errors'].append(f"{path}: Expected boolean, got {type(value).__name__}")
                result['valid'] = False
                result['structure_violation'] = True
        
        elif source_type == 'DATE':
            if isinstance(value, str) and not self._is_valid_date(value):
                if self.config.date_format_strict:
                    result['errors'].append(f"{path}: Invalid date format: {value}")
                    result['valid'] = False
                else:
                    result['warnings'].append(f"{path}: Invalid date format: {value}")
        
        elif source_type == 'STRUCT' and not isinstance(value, (dict, list)):
            if value is not None:
                if not (field_type.endswith('[]') and isinstance(value, list)):
                    result['errors'].append(f"{path}: Expected object or array, got {type(value).__name__}")
                    result['valid'] = False
                    result['structure_violation'] = True
        
        # ENUM value validation
        if is_enum and field_type in self.enum_mapping:
            valid_values = self.enum_mapping[field_type]
            if isinstance(value, str) and value not in valid_values:
                if self.config.auto_fix_enums:
                    # Attempt auto-correction
                    corrected = self._try_fix_enum_value(value, valid_values)
                    if corrected:
                        result['warnings'].append(f"{path}: Auto-corrected '{value}' to '{corrected}'")
                        result['value'] = corrected
                    else:
                        result['errors'].append(f"{path}: Invalid enum value '{value}'. Valid values: {', '.join(valid_values)}")
                        result['valid'] = False
                        result['enum_violation'] = True
                else:
                    result['errors'].append(f"{path}: Invalid enum value '{value}'. Valid values: {', '.join(valid_values)}")
                    result['valid'] = False
                    result['enum_violation'] = True
        
        # Character length limit validation
        if max_chars and isinstance(value, str) and len(value) > max_chars:
            if self.config.auto_truncate_long_fields:
                result['warnings'].append(f"{path}: Text truncated from {len(value)} to {max_chars} characters")
                result['value'] = value[:max_chars]
            else:
                result['errors'].append(f"{path}: Text length ({len(value)}) exceeds maximum ({max_chars})")
                result['valid'] = False
        
        # Required field validation
        if self.config.required_fields_strict and 'required' in rules.lower() and (value is None or value == ''):
            result['warnings'].append(f"{path}: Required field is empty")
        
        return result
    
    def _try_fix_enum_value(self, value: str, valid_values: List[str]) -> Optional[str]:
        """Attempt to auto-correct ENUM value"""
        value_lower = value.lower()
        
        # Case-insensitive matching
        for valid_value in valid_values:
            if value_lower == valid_value.lower():
                return valid_value
        
        # Attempt partial matching
        for valid_value in valid_values:
            if value_lower in valid_value.lower() or valid_value.lower() in value_lower:
                return valid_value
        
        return None
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Validate date format"""
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{4}-\d{2}$',        # YYYY-MM
            r'^\d{4}$',              # YYYY
            r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
        ]
        
        return any(re.match(pattern, date_str) for pattern in date_patterns)
    
    async def get_schema_summary(self) -> Dict[str, Any]:
        """Return schema summary information"""
        await self.initialize()
        
        return {
            'total_fields': len(self.field_schema),
            'enum_types': len(self.enum_mapping),
            'sections': list(set(path.split('.')[0] for path in self.field_schema.keys())),
            'field_types': {
                source_type: len([f for f in self.field_schema.values() 
                                if f['sourceType'] == source_type])
                for source_type in set(f['sourceType'] for f in self.field_schema.values())
            }
        }
    
    async def close(self):
        """Clean up resources"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)
    
    def _convert_string_to_validation_error(self, error_message: str) -> ValidationError:
        """Convert string error to ValidationError object (including field path extraction)"""
        
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
        
        # Extract expected value (part after Valid values: )
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
        
        # Determine validation level
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


async def validate_clinical_trial_data_async(data: ValidationData, 
                                           fieldlist_file: str = None, 
                                           enums_file: str = None,
                                           config: ValidationConfig = None) -> ValidationResult:
    """
    Asynchronous FieldList-based clinical trial data validation

    Args:
        data: Data to validate
        fieldlist_file: Path to FieldList.json file
        enums_file: Path to Enums.json file
        config: Validation configuration

    Returns:
        ValidationResult: Validation result
    """
    if not fieldlist_file:
        fieldlist_file = Path(__file__).parent.parent.parent / "CTGOV/FieldList.json"
    if not enums_file:
        enums_file = Path(__file__).parent.parent.parent / "CTGOV/Enums.json"
    
    validator = AsyncFieldListValidator(str(fieldlist_file), str(enums_file), config)
    
    try:
        result = await validator.validate_async(data)
        return result
    finally:
        await validator.close()


def validate_clinical_trial_data_with_fieldlist(data: ValidationData, 
                                               fieldlist_file: str = None, 
                                               enums_file: str = None) -> Dict[str, Any]:
    """
    Synchronous wrapper (backward compatibility)
    """
    async def _validate():
        result = await validate_clinical_trial_data_async(data, fieldlist_file, enums_file)
        # Convert to old format
        return {
            'valid': result.is_valid,
            'cleaned_data': result.cleaned_data,
            'errors': [error.message for error in result.errors],
            'warnings': [warning.message for warning in result.warnings],
            'removed_fields': result.removed_fields,
            'statistics': {
                'total_fields_input': result.statistics.total_fields_input,
                'valid_fields': result.statistics.valid_fields,
                'invalid_fields': result.statistics.invalid_fields,
                'enum_violations': result.statistics.enum_violations,
                'structure_violations': result.statistics.structure_violations
            }
        }
    
    # Execute in new event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, execute in new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _validate())
                return future.result()
        else:
            return loop.run_until_complete(_validate())
    except RuntimeError:
        return asyncio.run(_validate())
