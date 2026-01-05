"""
Extraction Pipeline Service

Dedicated pipeline for extracting structured data from clinical trial papers.
Handles only Information Extraction (IE) tasks.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any
import openai
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from .extraction_logger import get_extraction_logger, ExtractionRecord


class ExtractionPipeline:
    """Dedicated pipeline for structured data extraction using LiteLLM"""
    
    def __init__(self):
        # Check environment variables
        self.api_key = os.getenv("LITELLM_API_KEY")
        self.base_url = os.getenv("LITELLM_BASE_URL")
        
        self.async_client = None
        
        # Validate environment variables
        missing_vars = []
        if not self.api_key:
            missing_vars.append("LITELLM_API_KEY")
        if not self.base_url:
            missing_vars.append("LITELLM_BASE_URL")
            
        if missing_vars:
            print(f"⚠️  Warning: LiteLLM environment variables are not set: {', '.join(missing_vars)}")
            print("   Extraction functionality will be disabled.")
            return
        
        # Initialize only the asynchronous client (IE tasks are performed asynchronously)
        try:
            self.async_client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=180.0  # 3 minutes timeout for long-running extractions
            )
            print("✅ LiteLLM extraction pipeline initialization complete")
        except Exception as e:
            print(f"⚠️  Warning: LiteLLM extraction pipeline initialization failed: {e}")
            self.async_client = None
    
    def load_prompt(self, file_name: str, variables: dict) -> str:
        """Load prompt template and replace variables (for IE tasks only)"""
        # Path to prompts directory from services/extraction
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / file_name
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()
        except Exception as e:
            raise Exception(f"Error reading prompt file ({prompt_path}): {e}")
        
        # Variable replacement
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        
        return template
    
    async def process_prompt_file(self, prompt_file: str, paper_content: str, session_id: str = None, group: str = None) -> dict:
        """Process asynchronous streaming response for a single prompt file"""
        if not self.async_client:
            return {f"error_{prompt_file}": "LiteLLM async client not initialized"}
            
        try:
            prompt = self.load_prompt(prompt_file, {"pmc_text": paper_content})
        except Exception as e:
            return {f"error_{prompt_file}": f"Failed to load prompt: {e}"}
            
        retries = 0
        success = False
        logger = get_extraction_logger()
        
        while retries < 3 and not success:
            collected_messages = []
            try:
                call_start = time.time()
                start_time_iso = datetime.now().isoformat()
                print(f'[ExtractionPipeline] Processing {prompt_file} at {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(call_start))}')
                
                response_stream = await self.async_client.chat.completions.create(
                    model="GPT-5",
                    messages=[
                        {"role": "system", "content": "You are an expert assistant trained to extract structured data in JSON format from clinical trial articles."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    stream=True,
                    temperature=1,
                    seed=42
                )
                
                async for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        chunk_message = chunk.choices[0].delta.content
                        collected_messages.append(chunk_message)
                
                call_end = time.time()
                end_time_iso = datetime.now().isoformat()
                duration = call_end - call_start
                print(f"[ExtractionPipeline] {prompt_file} completed in {time.strftime('%M:%S', time.gmtime(duration))}")
                
                if not collected_messages:
                    print(f"[ExtractionPipeline] Warning: No content received for {prompt_file}")
                    retries += 1
                    await asyncio.sleep(1)
                    continue
                
                content = ''.join(collected_messages)
                partial_data = json.loads(content)
                
                # Extracted fields logging
                extracted_fields = self._extract_field_paths(partial_data)
                
                # Success logging
                if session_id:
                    record = ExtractionRecord(
                        session_id=session_id,
                        pmc_id=session_id.split('_')[0] if '_' in session_id else "unknown",
                        prompt_file=prompt_file,
                        group=group or "unknown",
                        start_time=start_time_iso,
                        end_time=end_time_iso,
                        duration_seconds=duration,
                        status="success",
                        extracted_fields=extracted_fields,
                        retry_count=retries
                    )
                    logger.log_extraction_record(session_id, record)
                
                success = True
                print(f"[ExtractionPipeline] Success: {prompt_file}")
                return partial_data
                
            except json.JSONDecodeError as e:
                retries += 1
                print(f"[ExtractionPipeline] JSON Decode Error on attempt {retries} for {prompt_file}: {e}")
                if retries >= 3:
                    # Failure logging
                    if session_id:
                        record = ExtractionRecord(
                            session_id=session_id,
                            pmc_id=session_id.split('_')[0] if '_' in session_id else "unknown",
                            prompt_file=prompt_file,
                            group=group or "unknown",
                            start_time=start_time_iso,
                            end_time=datetime.now().isoformat(),
                            duration_seconds=time.time() - call_start,
                            status="error",
                            extracted_fields=[],
                            error_message=f"JSON Decode Error: {str(e)}",
                            retry_count=retries
                        )
                        logger.log_extraction_record(session_id, record)
                    return {f"error_{prompt_file}": f"Failed after retries (JSON Decode): {str(e)}"}
                await asyncio.sleep(1)
                
            except Exception as e:
                retries += 1
                print(f"[ExtractionPipeline] Error on attempt {retries} for {prompt_file}: {type(e).__name__} - {e}")
                if retries >= 3:
                    # Failure logging
                    if session_id:
                        record = ExtractionRecord(
                            session_id=session_id,
                            pmc_id=session_id.split('_')[0] if '_' in session_id else "unknown",
                            prompt_file=prompt_file,
                            group=group or "unknown",
                            start_time=start_time_iso,
                            end_time=datetime.now().isoformat(),
                            duration_seconds=time.time() - call_start,
                            status="error",
                            extracted_fields=[],
                            error_message=f"{type(e).__name__}: {str(e)}",
                            retry_count=retries
                        )
                        logger.log_extraction_record(session_id, record)
                    return {f"error_{prompt_file}": f"Failed after retries: {type(e).__name__} - {str(e)}"}
                await asyncio.sleep(1)
    
    def _extract_field_paths(self, data: dict, prefix: str = "") -> List[str]:
        """Extract list of field paths from data"""
        fields = []
        
        def recurse(obj, path):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    fields.append(new_path)
                    if isinstance(value, (dict, list)):
                        recurse(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}[{i}]"
                    if isinstance(item, (dict, list)):
                        recurse(item, new_path)
        
        recurse(data, prefix)
        return fields
    
    async def extract_structured_info(self, paper_content: str, session_id: str = None) -> dict:
        """Extract structured data by asynchronously calling multiple divided prompts"""
        if not self.async_client:
            return {"error": "OpenAI async client not initialized"}
            
        start_time = time.time()
        logger = get_extraction_logger()
        
        print(f"[ExtractionPipeline] Starting extraction at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
        
        # Session logging start
        if session_id:
            logger.log_extraction_start(session_id)
        
        # Grouped prompt folders and final key mapping
        group_mapping = {
            "ie/1_protocol_section": "protocolSection",
            "ie/2_results_section": "resultsSection",
            "ie/3_derived_section": "derivedSection"
        }
        
        prompt_files = [
            # Protocol Section
            "ie/1_protocol_section/1_identification.md",
            "ie/1_protocol_section/2_description_and_conditions.md",
            "ie/1_protocol_section/3_design.md",
            "ie/1_protocol_section/4_arms_interventions.md",
            "ie/1_protocol_section/5_outcomes.md",
            "ie/1_protocol_section/6_eligibility.md",
            
            # Results Section
            "ie/2_results_section/1_participantflow.md",
            "ie/2_results_section/2_baselinecharacteristics.md", 
            "ie/2_results_section/3_outcomemeasures.md",
            "ie/2_results_section/4_adverse_events.md",
            
            # Derived Section
            "ie/3_derived_section/1_conditionbrowse_interventionbrowse.md",
        ]
        
        # Initialize aggregated_data for grouped results
        aggregated_data = {}
        for folder in group_mapping:
            group_key = group_mapping[folder]
            aggregated_data[group_key] = {}
        
        tasks = []
        # Create asynchronous tasks for each prompt file
        for prompt_file in prompt_files:
            group = None
            for folder in group_mapping:
                if prompt_file.startswith(folder):
                    group = group_mapping[folder]
                    break
            if group is None:
                print(f"[ExtractionPipeline] Warning: Prompt file '{prompt_file}' does not belong to any defined group. Skipping.")
                continue
            
            task = asyncio.create_task(self.process_prompt_file(prompt_file, paper_content, session_id, group))
            tasks.append((group, prompt_file, task))
        
        # Wait for all tasks to complete and merge results by group
        results = await asyncio.gather(*(task for _, _, task in tasks), return_exceptions=True)
        
        for i, (group, prompt_file, _) in enumerate(tasks):
            result = results[i]
            
            # Handle exceptions
            if isinstance(result, Exception):
                print(f"[ExtractionPipeline] Exception processing {prompt_file}: {result}")
                aggregated_data[group][f"error_{prompt_file}"] = f"Exception: {str(result)}"
                continue
                
            # Check for error keys
            if isinstance(result, dict):
                is_error = any(key.startswith("error_") for key in result.keys())
                if is_error:
                    print(f"[ExtractionPipeline] Error processing {prompt_file}: {result}")
                
                aggregated_data[group].update(result)
        
        end_time = time.time()
        duration = end_time - start_time
        print(f"[ExtractionPipeline] Extraction completed in {time.strftime('%M:%S', time.gmtime(duration))}")
        
        # Extraction stage end logging
        if session_id:
            logger.log_extraction_end(session_id)
        
        return aggregated_data
    
    def get_cache_filepath(self, pmc_id: str) -> Path:
        """Generate cache file path"""
        # Path to cache directory from services/extraction
        cache_dir = Path(__file__).parent.parent.parent / "cache"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir / f"{pmc_id}.json"
    
    async def get_structured_info_with_cache(self, pmc_id: str, paper_content: str) -> dict:
        """Extract structured information considering cache"""
        logger = get_extraction_logger()
        session_id = logger.start_session(pmc_id)
        
        cache_file = self.get_cache_filepath(pmc_id)
        used_cache = False
        
        if cache_file.exists():
            print(f"[ExtractionPipeline] Found cached data {cache_file}. Loading...")
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                used_cache = True
                logger.log_cache_usage(session_id, used_cache)
                
                # Skip extraction logging for cached data
                logger.finalize_session(session_id)
                return cached
            except json.JSONDecodeError as e:
                print(f"[ExtractionPipeline] Error loading cached data from {cache_file}: {e}. Regenerating...")
        
        logger.log_cache_usage(session_id, used_cache)
        print(f"[ExtractionPipeline] No valid cached data found for {pmc_id}. Generating new data...")
        
        result = await self.extract_structured_info(paper_content, session_id)
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"[ExtractionPipeline] Saved structured info to cache: {cache_file}")
        except Exception as e:
            print(f"[ExtractionPipeline] Error saving data to cache file {cache_file}: {e}")
        
        # Return session_id for finalization after validation
        return result
    
    async def get_structured_info_with_session(self, pmc_id: str, paper_content: str) -> tuple[dict, str]:
        """Extract structured information considering cache and return session ID"""
        logger = get_extraction_logger()
        session_id = logger.start_session(pmc_id)
        
        cache_file = self.get_cache_filepath(pmc_id)
        used_cache = False
        cache_validation_applied = False
        
        if cache_file.exists():
            print(f"[ExtractionPipeline] Found cached data {cache_file}. Loading...")
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                used_cache = True
                
                # Check for validation info in cached data
                if "_validation" in cached:
                    cache_validation_applied = True
                
                logger.log_cache_usage(session_id, used_cache, cache_validation_applied)
                return cached, session_id
            except json.JSONDecodeError as e:
                print(f"[ExtractionPipeline] Error loading cached data from {cache_file}: {e}. Regenerating...")
        
        logger.log_cache_usage(session_id, used_cache, cache_validation_applied)
        print(f"[ExtractionPipeline] No valid cached data found for {pmc_id}. Generating new data...")
        
        result = await self.extract_structured_info(paper_content, session_id)
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"[ExtractionPipeline] Saved structured info to cache: {cache_file}")
        except Exception as e:
            print(f"[ExtractionPipeline] Error saving data to cache file {cache_file}: {e}")
        
        return result, session_id
    
    def get_filtering_fields(self, pmcids: List):

        def fetch_pmc_full_text_xml(pmcid: str) -> tuple[str, str | None]:
            """
            Fetches full text content from PMC using XML format.
            Returns a tuple: (article_text, year)
            """
            if pmcid.startswith("PMC"):
                pmcid = pmcid[3:]

            url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            params = {"db": "pmc", "id": pmcid, "retmode": "xml"}
            headers = {"User-Agent": "Mozilla/5.0"}

            response = requests.get(url, params=params, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch XML for {pmcid}: {response.status_code}")

            soup = BeautifulSoup(response.content, "lxml-xml")

            # -------------------------------
            # Extract paragraphs and section titles
            # -------------------------------
            text_parts = []
            for tag in soup.find_all(["title", "p"]):
                text = tag.get_text(strip=True)
                if text:
                    text_parts.append(text)
            article_text = "\n".join(text_parts)

            # -------------------------------
            # Extract Year from <DateCompleted><Year>
            # -------------------------------
            year = None
            # Try first <pub-date pub-type="epub"> (preferred)
            pub_date = soup.find("pub-date", {"pub-type": "epub"})
            if not pub_date:
                # fallback: any <pub-date>
                pub_date = soup.find("pub-date")

            if pub_date:
                year_tag = pub_date.find("year")
                if year_tag and year_tag.text.strip().isdigit():
                    year = year_tag.text.strip()

            return article_text, year

    
        try:
            client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        except Exception as e:
            raise Exception(f"Failed to initialize OpenAI client: {e}")

        results = {}
        x = 0
        for pmcid in pmcids:
            try:

                article_text, year = fetch_pmc_full_text_xml(pmcid)
                
                prompt = '''Extract the following information in JSON format with defined keys from the given clinical trial pubmed article.
                Output format:
                ```json
                {
                    "studyType": // Study classification - ENUM (EXPANDED_ACCESS, INTERVENTIONAL, OBSERVATIONAL)
                    "phases": // Study phases applicable for drug/biologic trials - ARRAY of ENUM (NA, EARLY_PHASE1, PHASE1, PHASE2, PHASE3, PHASE4)
                    "allocation": // Method of assigning participants - ENUM (RANDOMIZED, NON_RANDOMIZED, NA)
                    "interventionModel": // Type of intervention design. Required if studyType is INTERVENTIONAL - ENUM (SINGLE_GROUP, PARALLEL, CROSSOVER, FACTORIAL, SEQUENTIAL)
                    "observationalModel": // Study model for observational studies. Required if studyType is OBSERVATIONAL - ENUM (COHORT, CASE_CONTROL, CASE_ONLY, CASE_CROSSOVER, ECOLOGIC_OR_COMMUNITY, FAMILY_BASED, DEFINED_POPULATION, NATURAL_HISTORY, OTHER)
                }
                ```
                article_text:
                article_text_here
                '''
                prompt = prompt.replace("article_text_here", article_text)

                response = client.chat.completions.create(
                    model="gemini-2.5-flash",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0,
                )

                content = response.choices[0].message.content.strip()
                parsed = json.loads(content)
                results[pmcid] = {
                    "study_type": parsed['studyType'] or "UNKNOWN",
                    "phase": parsed['phases'] or ["NA"],
                    "design_allocation": parsed['allocation'] or "NA",
                    "observational_model": parsed['observationalModel'] or "UNKNOWN",
                    "year": year or None,
                    "_meta": {"phase_source": "error"},
                }

            except Exception as e:
                print(f"⚠️ Error processing {pmcid}: {e}")
                results[pmcid] = {
                    "study_type": "UNKNOWN",
                    "phase": ["NA"],
                    "design_allocation": "NA",
                    "observational_model": "UNKNOWN",
                    "year": None,
                    "_meta": {"phase_source": "error"},
                }
            x += 1
            if x % 100 == 0:
                print(f"📄 Fetched {x} full texts")
                

        print(f"Extraction complete for {len(results)} articles.")
        return results



# Global instance (Singleton pattern)
_extraction_pipeline = None

def get_extraction_pipeline() -> ExtractionPipeline:
    """Return global extraction pipeline instance"""
    global _extraction_pipeline
    if _extraction_pipeline is None:
        _extraction_pipeline = ExtractionPipeline()
    return _extraction_pipeline


# Backward compatibility functions - Provide only IE functionality
def load_prompt(file_name: str, variables: dict) -> str:
    """Backward compatibility function for load_prompt (IE only)"""
    return get_extraction_pipeline().load_prompt(file_name, variables)


async def process_prompt_file(prompt_file: str, paper_content: str, client=None) -> dict:
    """Backward compatibility function for process_prompt_file (client parameter ignored)"""
    return await get_extraction_pipeline().process_prompt_file(prompt_file, paper_content)


async def extract_structured_info(paper_content: str) -> dict:
    """Backward compatibility function for extract_structured_info"""
    return await get_extraction_pipeline().extract_structured_info(paper_content)


async def get_structured_info_with_cache(pmc_id: str, paper_content: str) -> dict:
    """Backward compatibility function for get_structured_info_with_cache"""
    return await get_extraction_pipeline().get_structured_info_with_cache(pmc_id, paper_content)


def get_cache_filepath(pmc_id: str) -> Path:
    """Backward compatibility function for get_cache_filepath"""
    return get_extraction_pipeline().get_cache_filepath(pmc_id)


# Alias (Backward compatibility)
OpenAIExtractionService = ExtractionPipeline
