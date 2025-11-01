import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Union
from datetime import datetime
from dataclasses import dataclass, asdict
import uuid


@dataclass
class ExtractionRecord:
    # single extraction record
    session_id: str
    pmc_id: str
    prompt_file: str
    group: str
    start_time: str
    end_time: str
    duration_seconds: float
    status: str  # "success", "error", "partial"
    extracted_fields: List[str]
    error_message: Optional[str] = None
    retry_count: int = 0


@dataclass
class ValidationRecord:
    # single validation record
    session_id: str
    pmc_id: str
    field_path: str
    validation_type: str  # "fieldlist", "mesh", "structure", "type"
    status: str  # "valid", "error", "warning", "corrected"
    original_value: Any
    corrected_value: Any
    error_message: Optional[str] = None
    warning_message: Optional[str] = None


@dataclass 
class DetailedValidationRecord:
    session_id: str
    pmc_id: str
    field_path: str
    field_name: str                    # last field name only
    issue_type: str                    # ValidationIssueType.value
    severity: str                      # ValidationSeverity.value  
    validation_module: str             # "fieldlist", "mesh", "structure", "type", "constraint"
    error_message: str
    
    parent_path: Optional[str] = None  # parent path
    original_value: Any = None
    expected_type: Optional[str] = None
    expected_values: Optional[str] = None  # stored as JSON string
    corrected_value: Any = None
    suggestion: Optional[str] = None
    validation_timestamp: Optional[str] = None
    processing_time_ms: Optional[float] = None


@dataclass
class SessionSummary:
    """Complete session summary"""
    session_id: str
    pmc_id: str
    start_time: str
    end_time: str
    total_duration_seconds: float
    extraction_phase_duration: float
    validation_phase_duration: float
    
    # Extraction statistics
    total_prompts: int
    successful_prompts: int
    failed_prompts: int
    total_extraction_retries: int
    
    # Validation statistics
    total_fields_input: int
    valid_fields: int
    invalid_fields: int
    corrected_fields: int
    removed_fields: int
    
    # Error/warning statistics
    enum_violations: int
    structure_violations: int
    type_violations: int
    constraint_violations: int
    mesh_validation_errors: int
    fieldlist_validation_errors: int
    
    # Cache information
    used_cache: bool
    cache_validation_applied: bool


class ExtractionValidationLogger:
    """Extraction and validation process logging system"""
    
    def __init__(self, log_base_dir: str = None):
        # Set absolute path based on backend directory
        if log_base_dir is None:
            # Find backend directory from current file location
            current_file = Path(__file__)
            backend_dir = current_file.parent.parent.parent  # services/extraction/extraction_logger.py -> backend/
            log_base_dir = backend_dir / "logs" / "extraction_validation"
        
        self.log_base_dir = Path(log_base_dir)
        self.log_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Log directory structure
        self.sessions_dir = self.log_base_dir / "sessions"
        self.extractions_dir = self.log_base_dir / "extractions" 
        self.validations_dir = self.log_base_dir / "validations"
        self.summaries_dir = self.log_base_dir / "summaries"
        
        # Create directories
        for dir_path in [self.sessions_dir, self.extractions_dir, self.validations_dir, self.summaries_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        print(f"[Logger] Initialized with log directory: {self.log_base_dir}")
            
        # Temporary storage for current session data
        self.current_session_data = {}
        
    def start_session(self, pmc_id: str) -> str:
        """Start new extraction/validation session"""
        session_id = f"{pmc_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        self.current_session_data[session_id] = {
            "session_id": session_id,
            "pmc_id": pmc_id,
            "start_time": datetime.now().isoformat(),
            "extraction_records": [],
            "validation_records": [],
            "extraction_start": None,
            "extraction_end": None,
            "validation_start": None,
            "validation_end": None,
            "used_cache": False,
            "cache_validation_applied": False
        }
        
        print(f"[Logger] Started session {session_id} for PMC {pmc_id}")
        return session_id
    
    def log_extraction_start(self, session_id: str):
        """Log extraction phase start"""
        if session_id in self.current_session_data:
            self.current_session_data[session_id]["extraction_start"] = datetime.now().isoformat()
    
    def log_extraction_end(self, session_id: str):
        """Log extraction phase end"""
        if session_id in self.current_session_data:
            self.current_session_data[session_id]["extraction_end"] = datetime.now().isoformat()
    
    def log_validation_start(self, session_id: str):
        """Log validation phase start"""
        if session_id in self.current_session_data:
            self.current_session_data[session_id]["validation_start"] = datetime.now().isoformat()
    
    def log_validation_end(self, session_id: str):
        """Log validation phase end"""
        if session_id in self.current_session_data:
            self.current_session_data[session_id]["validation_end"] = datetime.now().isoformat()
    
    def log_cache_usage(self, session_id: str, used_cache: bool, cache_validation_applied: bool = False):
        """Log cache usage"""
        if session_id in self.current_session_data:
            self.current_session_data[session_id]["used_cache"] = used_cache
            self.current_session_data[session_id]["cache_validation_applied"] = cache_validation_applied
    
    def log_extraction_record(self, session_id: str, record: ExtractionRecord):
        """Log individual extraction record"""
        if session_id in self.current_session_data:
            self.current_session_data[session_id]["extraction_records"].append(record)
            
        # Save to file immediately (streaming approach)
        extraction_file = self.extractions_dir / f"{datetime.now().strftime('%Y%m%d')}_extractions.csv"
        
        # Check and create CSV header
        file_exists = extraction_file.exists()
        try:
            with open(extraction_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "session_id", "pmc_id", "prompt_file", "group", "start_time", "end_time", 
                    "duration_seconds", "status", "extracted_fields_count", "extracted_fields", 
                    "error_message", "retry_count"
                ])
                
                if not file_exists:
                    writer.writeheader()
                
                row_data = {
                    "session_id": record.session_id,
                    "pmc_id": record.pmc_id,
                    "prompt_file": record.prompt_file,
                    "group": record.group,
                    "start_time": record.start_time,
                    "end_time": record.end_time,
                    "duration_seconds": record.duration_seconds,
                    "status": record.status,
                    "extracted_fields_count": len(record.extracted_fields),
                    "extracted_fields": "|".join(record.extracted_fields),
                    "error_message": record.error_message or "",
                    "retry_count": record.retry_count
                }
                writer.writerow(row_data)
                f.flush()  # Write to disk immediately
        except Exception as e:
            print(f"[Logger] Error writing extraction record: {e}")
            import traceback
            traceback.print_exc()
    
    def log_validation_record(self, session_id: str, record: Union[ValidationRecord, DetailedValidationRecord]):
        """Log individual validation record (supports both basic and detailed formats)"""
        if session_id in self.current_session_data:
            self.current_session_data[session_id]["validation_records"].append(record)
            
        # Save to file immediately (streaming approach)
        validation_file = self.validations_dir / f"{datetime.now().strftime('%Y%m%d')}_validations.csv"
        
        # Check and create CSV header
        file_exists = validation_file.exists()
        
        # Check if it's a detailed record
        is_detailed = isinstance(record, DetailedValidationRecord)
        
        try:
            with open(validation_file, "a", newline="", encoding="utf-8") as f:
                if is_detailed:
                    # Detailed format CSV
                    fieldnames = [
                        "session_id", "pmc_id", "field_path", "field_name", "parent_path",
                        "issue_type", "severity", "validation_module", 
                        "original_value", "expected_type", "expected_values", "corrected_value",
                        "error_message", "suggestion", "validation_timestamp", "processing_time_ms"
                    ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    
                    if not file_exists:
                        writer.writeheader()
                    
                    # Convert values to strings
                    original_str = json.dumps(record.original_value) if record.original_value is not None else ""
                    corrected_str = json.dumps(record.corrected_value) if record.corrected_value is not None else ""
                    
                    writer.writerow({
                        "session_id": record.session_id,
                        "pmc_id": record.pmc_id,
                        "field_path": record.field_path,
                        "field_name": record.field_name,
                        "parent_path": record.parent_path or "",
                        "issue_type": record.issue_type,
                        "severity": record.severity,
                        "validation_module": record.validation_module,
                        "original_value": original_str,
                        "expected_type": record.expected_type or "",
                        "expected_values": record.expected_values or "",
                        "corrected_value": corrected_str,
                        "error_message": record.error_message,
                        "suggestion": record.suggestion or "",
                        "validation_timestamp": record.validation_timestamp or datetime.now().isoformat(),
                        "processing_time_ms": record.processing_time_ms or 0
                    })
                else:
                    # Basic format CSV (backward compatibility)
                    fieldnames = [
                        "session_id", "pmc_id", "field_path", "validation_type", "status",
                        "original_value", "corrected_value", "error_message", "warning_message"
                    ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    
                    if not file_exists:
                        writer.writeheader()
                    
                    # Convert values to strings (JSON serialization)
                    original_str = json.dumps(record.original_value) if record.original_value is not None else ""
                    corrected_str = json.dumps(record.corrected_value) if record.corrected_value is not None else ""
                    
                    writer.writerow({
                        "session_id": record.session_id,
                        "pmc_id": record.pmc_id,
                        "field_path": record.field_path,
                        "validation_type": record.validation_type,
                        "status": record.status,
                        "original_value": original_str,
                        "corrected_value": corrected_str,
                        "error_message": record.error_message or "",
                        "warning_message": record.warning_message or ""
                    })
                
                f.flush()  # Write to disk immediately
        except Exception as e:
            print(f"[Logger] Error writing validation record: {e}")
            import traceback
            traceback.print_exc()
    
    def finalize_session(self, session_id: str, validation_result=None):
        """Finalize session and generate summary"""
        if session_id not in self.current_session_data:
            print(f"[Logger] Warning: Session {session_id} not found")
            return
        
        session_data = self.current_session_data[session_id]
        end_time = datetime.now().isoformat()
        
        # Calculate time
        start_time = datetime.fromisoformat(session_data["start_time"])
        end_time_dt = datetime.now()
        total_duration = (end_time_dt - start_time).total_seconds()
        
        # Calculate extraction/validation phase durations
        extraction_duration = 0
        validation_duration = 0
        
        if session_data.get("extraction_start") and session_data.get("extraction_end"):
            ext_start = datetime.fromisoformat(session_data["extraction_start"])
            ext_end = datetime.fromisoformat(session_data["extraction_end"])
            extraction_duration = (ext_end - ext_start).total_seconds()
        
        if session_data.get("validation_start") and session_data.get("validation_end"):
            val_start = datetime.fromisoformat(session_data["validation_start"])
            val_end = datetime.fromisoformat(session_data["validation_end"])
            validation_duration = (val_end - val_start).total_seconds()
        
        # Calculate extraction statistics
        extraction_records = session_data["extraction_records"]
        successful_extractions = len([r for r in extraction_records if r.status == "success"])
        failed_extractions = len([r for r in extraction_records if r.status == "error"])
        total_retries = sum(r.retry_count for r in extraction_records)
        
        # Calculate validation statistics
        validation_records = session_data["validation_records"]
        validation_stats = self._calculate_validation_stats(validation_records, validation_result)
        
        # Generate session summary
        summary = SessionSummary(
            session_id=session_id,
            pmc_id=session_data["pmc_id"],
            start_time=session_data["start_time"],
            end_time=end_time,
            total_duration_seconds=total_duration,
            extraction_phase_duration=extraction_duration,
            validation_phase_duration=validation_duration,
            
            total_prompts=len(extraction_records),
            successful_prompts=successful_extractions,
            failed_prompts=failed_extractions,
            total_extraction_retries=total_retries,
            
            **validation_stats,
            
            used_cache=session_data.get("used_cache", False),
            cache_validation_applied=session_data.get("cache_validation_applied", False)
        )
        
        # Save detailed session data in JSON format (safely)
        session_file = self.sessions_dir / f"{session_id}.json"
        
        try:
            # Safely serialize extraction records
            extraction_records_data = []
            for r in extraction_records:
                try:
                    extraction_records_data.append(asdict(r))
                except Exception as e:
                    print(f"[Logger] Error serializing extraction record: {e}")
                    extraction_records_data.append({"error": f"Serialization failed: {str(r)}"})
            
            # Safely serialize validation records
            validation_records_data = []
            for r in validation_records:
                try:
                    validation_records_data.append(asdict(r))
                except Exception as e:
                    print(f"[Logger] Error serializing validation record: {e}")
                    validation_records_data.append({"error": f"Serialization failed: {str(r)}"})
            
            detailed_session = {
                **asdict(summary),
                "extraction_records": extraction_records_data,
                "validation_records": validation_records_data
            }
            
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(detailed_session, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[Logger] Error saving detailed session: {e}")
            # Save minimal summary only
            try:
                minimal_session = asdict(summary)
                with open(session_file, "w", encoding="utf-8") as f:
                    json.dump(minimal_session, f, ensure_ascii=False, indent=2)
            except Exception as e2:
                print(f"[Logger] Error saving minimal session: {e2}")
        
        # Save summary in CSV format (safely)
        try:
            summary_file = self.summaries_dir / f"{datetime.now().strftime('%Y%m%d')}_summaries.csv"
            file_exists = summary_file.exists()
            
            with open(summary_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(asdict(summary).keys()))
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(asdict(summary))
        except Exception as e:
            print(f"[Logger] Error saving summary CSV: {e}")
        
        # Clean up temporary data
        del self.current_session_data[session_id]
        
        print(f"[Logger] Finalized session {session_id}")
        print(f"  - Total duration: {total_duration:.2f}s")
        print(f"  - Extraction: {extraction_duration:.2f}s, Validation: {validation_duration:.2f}s")
        print(f"  - Prompts: {successful_extractions}/{len(extraction_records)} successful")
        print(f"  - Fields: {validation_stats['valid_fields']}/{validation_stats['total_fields_input']} valid")
        
        return summary
    
    def _calculate_validation_stats(self, validation_records: List[Union[ValidationRecord, DetailedValidationRecord]], validation_result=None) -> Dict:
        """Calculate validation statistics (supports both legacy and detailed records)"""
        stats = {
            "total_fields_input": 0,
            "valid_fields": 0,
            "invalid_fields": 0,
            "corrected_fields": 0,
            "removed_fields": 0,
            "enum_violations": 0,
            "structure_violations": 0,
            "type_violations": 0,
            "constraint_violations": 0,
            "mesh_validation_errors": 0,
            "fieldlist_validation_errors": 0
        }
        
        # Get statistics from validation_result (priority)
        if validation_result and hasattr(validation_result, 'statistics') and validation_result.statistics:
            try:
                vs = validation_result.statistics
                stats.update({
                    "total_fields_input": getattr(vs, 'total_fields_input', 0),
                    "valid_fields": getattr(vs, 'valid_fields', 0),
                    "invalid_fields": getattr(vs, 'invalid_fields', 0),
                    "corrected_fields": getattr(vs, 'corrected_fields', 0),
                    "removed_fields": getattr(vs, 'removed_fields', 0),
                    "enum_violations": getattr(vs, 'enum_violations', 0),
                    "structure_violations": getattr(vs, 'structure_violations', 0),
                    "type_violations": getattr(vs, 'type_violations', 0),
                    "constraint_violations": getattr(vs, 'constraint_violations', 0)
                })
            except Exception as e:
                print(f"[Logger] Error extracting validation statistics: {e}")
        
        # Calculate additional statistics from validation_records (supports both legacy and detailed)
        for record in validation_records:
            try:
                # Legacy ValidationRecord support
                if hasattr(record, 'validation_type'):
                    validation_type = record.validation_type
                    status = getattr(record, 'status', 'unknown')
                # Detailed ValidationRecord support  
                elif hasattr(record, 'validation_module'):
                    validation_type = record.validation_module
                    status = getattr(record, 'severity', 'unknown')
                else:
                    continue
                    
                if validation_type == "mesh":
                    if status in ["error", "warning", "critical"]:
                        stats["mesh_validation_errors"] += 1
                elif validation_type == "fieldlist":
                    if status in ["error", "warning", "critical"]:
                        stats["fieldlist_validation_errors"] += 1
            except Exception as e:
                print(f"[Logger] Error processing validation record: {e}")
        
        return stats


# Global logger instance
_logger = None

def get_extraction_logger() -> ExtractionValidationLogger:
    """Return global extraction logger instance"""
    global _logger
    if _logger is None:
        _logger = ExtractionValidationLogger()
    return _logger
