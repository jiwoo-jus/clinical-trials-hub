import json
import logging
from typing import Dict, List, Any, Optional
from services.openai_service import OpenAIService
from services.cache_service import CacheService
from services.ctg_service import CTGService
from services.pm_service import PMService

logger = logging.getLogger(__name__)
insights_log = logging.getLogger("insights_conversations")  # Reference to dedicated logger

class InsightsService:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.cache_service = CacheService()
        self.ctg_service = CTGService()
        self.pm_service = PMService()
    
    def generate_insights(self, search_key: str, page: int = 1, applied_filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate AI insights for search results - cached per search_key (not per page)
        Insights are always generated from page 1 results for consistency
        """
        try:
            # Always use page 1 for insights generation (ignore the page parameter)
            # This ensures insights are consistent across all pages
            insights_page = 1
            
            # Build cache key for insights (based on search_key and filters only, not page)
            insights_key = f"insights_{search_key}"
            if applied_filters:
                filter_hash = hash(json.dumps(applied_filters, sort_keys=True))
                insights_key += f"_{filter_hash}"
            
            # Check if insights are already cached
            cached_insights = self.cache_service.get_insights(insights_key)
            if cached_insights:
                logger.info(f"✅ Using cached insights for search_key: {search_key}")
                return {
                    'insights': cached_insights,
                    'page': page,
                    'insights_key': insights_key,
                    'from_cache': True
                }
            
            logger.info(f"Generating NEW insights for search_key: {search_key}, page: {insights_page}")
            
            # Get search results from cache (always use page 1)
            search_results = self.cache_service.get_search_results(search_key, insights_page)
            if not search_results:
                return {'error': 'Search results not found'}
            
            # Use metadata from search results directly (no need for detailed API calls)
            results_list = search_results.get('results', [])
            if not results_list:
                return {'error': 'No results found for insights generation'}
            
            # Extract user's original query from search params
            search_params = search_results.get('search_params', {})
            user_query = search_params.get('query', '')
            
            logger.info(f"Using metadata from {len(results_list)} results for insights generation")
            logger.info(f"User query: {user_query}")

            # ── Log: insights generation start ───────────────────────────────
            insights_log.info("=" * 80)
            insights_log.info("[INSIGHTS GENERATE] Starting new insights generation")
            insights_log.info(f"  search_key     : {search_key}")
            insights_log.info(f"  user_query     : {user_query}")
            insights_log.info(f"  results_count  : {len(results_list)}")
            insights_log.info(f"  applied_filters: {json.dumps(applied_filters, ensure_ascii=False) if applied_filters else 'None'}")
            insights_log.info("=" * 80)
            # ─────────────────────────────────────────────────────────

            # Generate insights using OpenAI (with metadata, abstracts, and user query)
            insights = self._generate_ai_insights(results_list, applied_filters, user_query)
            
            # Cache the insights
            self.cache_service.cache_insights(insights_key, insights)
            logger.info(f"✅ Cached new insights with key: {insights_key}")
            
            return {
                'insights': insights,
                'page': page,
                'total_results': len(results_list),
                'insights_key': insights_key,
                'from_cache': False
            }
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return {'error': f'Failed to generate insights: {str(e)}'}
    
    def _get_detailed_results(self, results: List[Dict]) -> List[Dict]:
        """
        Get detailed data for each result (PM: efetch XML, CTG: full JSON)
        """
        detailed_results = []
        
        for result in results:
            try:
                detailed_data = {'metadata': result}
                
                if result.get('type') == 'PM':
                    # Get PM detailed data using efetch
                    pmid = result.get('pmid') or result.get('id')
                    if pmid:
                        pm_detail = self.pm_service.get_paper_details(pmid)
                        if pm_detail:
                            detailed_data['pm_full_data'] = pm_detail
                
                elif result.get('type') == 'CTG':
                    # Get CTG detailed data
                    nct_id = result.get('id')
                    if nct_id:
                        ctg_detail = self.ctg_service.get_study_details(nct_id)
                        if ctg_detail:
                            detailed_data['ctg_full_data'] = ctg_detail
                
                elif result.get('type') == 'MERGED':
                    # Get both PM and CTG detailed data
                    pmid = result.get('pmid')
                    nct_id = result.get('nctid')
                    
                    if pmid:
                        pm_detail = self.pm_service.get_paper_details(pmid)
                        if pm_detail:
                            detailed_data['pm_full_data'] = pm_detail
                    
                    if nct_id:
                        ctg_detail = self.ctg_service.get_study_details(nct_id)
                        if ctg_detail:
                            detailed_data['ctg_full_data'] = ctg_detail
                
                detailed_results.append(detailed_data)
                
            except Exception as e:
                logger.warning(f"Failed to get detailed data for result {result.get('id', 'unknown')}: {str(e)}")
                # Still include the result with just metadata
                detailed_results.append({'metadata': result})
        
        return detailed_results
    
    def _generate_ai_insights(self, results_list: List[Dict], applied_filters: Optional[Dict] = None, user_query: str = "") -> Dict[str, Any]:
        """
        Generate AI insights from search results metadata with abstracts
        """
        try:
            logger.info(f"Starting AI insights generation for {len(results_list)} results")
            
            # Prepare data summary for AI
            summary_data = self._prepare_data_summary(results_list)
            logger.info(f"Prepared summary data: {len(summary_data)} fields")

            # ── Log: data summary ──────────────────────────────────────
            insights_log.info("[DATA SUMMARY] Data summary result")
            insights_log.info(f"  total_items  : {summary_data['total_items']}")
            insights_log.info(f"  pm_count     : {summary_data['pm_count']}")
            insights_log.info(f"  ctg_count    : {summary_data['ctg_count']}")
            insights_log.info(f"  merged_count : {summary_data['merged_count']}")
            insights_log.info(f"  conditions   : {summary_data['conditions']}")
            insights_log.info(f"  interventions: {summary_data['interventions']}")
            insights_log.info(f"  phases       : {summary_data['study_phases']}")
            insights_log.info(f"  study_types  : {summary_data['study_types']}")
            insights_log.info(f"  journals     : {summary_data['journals']}")
            # ─────────────────────────────────────────────────────────
            
            # Create prompt for insights generation
            prompt = self._create_insights_prompt(summary_data, results_list, applied_filters, user_query)
            logger.info(f"Created prompt with length: {len(prompt)} characters")

            insights_log.info(f"[PROMPT BUILT] Prompt length: {len(prompt)} chars (full content logged in OPENAI REQUEST section)")
            
            # Generate insights using OpenAI
            system_msg = "You are an expert clinical research analyst. Provide comprehensive, actionable insights about clinical trials and research papers. Respond only with valid JSON."
            response = self.openai_service.generate_completion(
                prompt=prompt,
                system_message=system_msg,
                max_tokens=4096,
                temperature=0.3,
                response_format="json"
            )
            
            logger.info(f"Received OpenAI response with length: {len(response) if response else 0}")
            
            # Parse and structure the insights
            insights = self._parse_insights_response(response)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'summary': 'Unable to generate insights at this time.',
                'key_findings': [],
                'trends': [],
                'recommendations': []
            }
    
    def _prepare_data_summary(self, results_list: List[Dict]) -> Dict[str, Any]:
        """
        Prepare a structured summary of the data for AI analysis using metadata only
        """
        summary = {
            'total_items': len(results_list),
            'pm_count': 0,
            'ctg_count': 0,
            'merged_count': 0,
            'conditions': set(),
            'interventions': set(),
            'study_phases': set(),
            'study_types': set(),
            'journals': set(),
            'recent_studies': [],
            'key_outcomes': []
        }
        
        for item in results_list:
            item_type = item.get('type', '')

            # MERGED items have pm_data / ctg_data nested inside
            pm_data  = item.get('pm_data',  {})
            ctg_data = item.get('ctg_data', {})
            
            # Count by type
            if item_type == 'PM':
                summary['pm_count'] += 1
            elif item_type == 'CTG':
                summary['ctg_count'] += 1
            elif item_type == 'MERGED':
                summary['merged_count'] += 1
            
            # Extract conditions (MERGED → ctg_data takes priority)
            conditions = item.get('conditions') or ctg_data.get('conditions') or pm_data.get('conditions') or []
            if isinstance(conditions, list):
                summary['conditions'].update(conditions)
            elif isinstance(conditions, str) and conditions:
                summary['conditions'].add(conditions)

            # Extract interventions (MERGED → ctg_data takes priority)
            interventions = item.get('intervention_names') or ctg_data.get('intervention_names') or []
            if isinstance(interventions, list):
                summary['interventions'].update(interventions)
            elif isinstance(interventions, str) and interventions:
                summary['interventions'].add(interventions)
            
            # Extract study information
            phase = item.get('phase') or ctg_data.get('phase') or pm_data.get('phase') or ''
            if phase:
                summary['study_phases'].add(phase)

            study_type = (item.get('studyType') or item.get('study_type')
                          or ctg_data.get('study_type') or pm_data.get('study_type') or '')
            if study_type:
                summary['study_types'].add(study_type)

            journal = item.get('journal') or pm_data.get('journal') or ''
            if journal:
                summary['journals'].add(journal)
            
            # Add recent studies (with publication date)
            pub_date = (item.get('pubDate') or item.get('date')
                        or pm_data.get('pubDate') or ctg_data.get('start_date') or '')
            title = (item.get('title', '') or pm_data.get('title', '') or ctg_data.get('title', ''))
            if pub_date:
                summary['recent_studies'].append({
                    'title': title,
                    'date': pub_date,
                    'type': item_type
                })
        
        # Convert sets to lists for JSON serialization
        summary['conditions'] = list(summary['conditions'])[:10]  # Limit to top 10
        summary['interventions'] = list(summary['interventions'])[:10]
        summary['study_phases'] = list(summary['study_phases'])
        summary['study_types'] = list(summary['study_types'])
        summary['journals'] = list(summary['journals'])[:10]
        
        # Sort recent studies by date
        summary['recent_studies'].sort(key=lambda x: x.get('date', ''), reverse=True)
        summary['recent_studies'] = summary['recent_studies'][:5]  # Top 5 recent
        
        return summary
    
    def _create_insights_prompt(self, summary_data: Dict[str, Any], results_list: List[Dict], applied_filters: Optional[Dict] = None, user_query: str = "") -> str:
        """
        Create a prompt for AI insights generation with user query and abstracts
        """
        query_context = f"\n\nUser's Search Query: \"{user_query}\"" if user_query else ""
        
        filter_context = ""
        if applied_filters:
            filter_context = f"\n\nApplied Filters: {json.dumps(applied_filters, indent=2)}"
        
        # Format sample results for the prompt (including abstracts)
        # ── Log: chunking ────────────────────────────────────────────
        total = len(results_list)
        chunk_size = 10
        taken = results_list[:chunk_size]
        insights_log.info("[CHUNKING] Chunking results for prompt")
        insights_log.info(f"  total results : {total}")
        insights_log.info(f"  included in prompt : {len(taken)} (top {chunk_size})")
        insights_log.info(f"  excluded results : {total - len(taken)}")
        for idx, item in enumerate(taken, 1):
            iid = item.get('id') or item.get('pmid') or item.get('nctid') or 'unknown'
            # MERGED items have pm_data / ctg_data nested inside
            pm_data  = item.get('pm_data',  {})
            ctg_data = item.get('ctg_data', {})
            abstract_raw = (
                item.get('abstract', '')
                or pm_data.get('abstract', '')
                or item.get('brief_summary', '')
                or ctg_data.get('brief_summary', '')
                or item.get('description', '')
                or item.get('briefSummary', '')
            )
            if isinstance(abstract_raw, dict):
                abstract_raw = ' '.join(str(v) for v in abstract_raw.values() if v)
            abst_len = len(abstract_raw) if abstract_raw else 0
            truncated = abst_len > 3000
            insights_log.info(
                f"  [{idx:02d}] id={iid} | type={item.get('type','?')} | "
                f"abstract={abst_len}chars {'→ truncated(3000)' if truncated else '→ full'}"
            )
        # ─────────────────────────────────────────────────────────

        sample_results_text = self._format_results_for_prompt(results_list[:chunk_size])
        
        prompt = f"""
Based on the following clinical research data, provide comprehensive insights and analysis:
{query_context}
{filter_context}

Data Summary:
- Total items analyzed: {summary_data['total_items']}
- PubMed papers: {summary_data['pm_count']}
- Clinical trials: {summary_data['ctg_count']}
- Merged items: {summary_data['merged_count']}

Key Conditions: {', '.join(summary_data['conditions'][:5]) if summary_data['conditions'] else 'None specified'}
Key Interventions: {', '.join(summary_data['interventions'][:5]) if summary_data['interventions'] else 'None specified'}
Study Phases: {', '.join(summary_data['study_phases']) if summary_data['study_phases'] else 'Not specified'}
Study Types: {', '.join(summary_data['study_types']) if summary_data['study_types'] else 'Not specified'}
Top Journals: {', '.join(summary_data['journals'][:3]) if summary_data['journals'] else 'Not specified'}

Recent Studies: {json.dumps(summary_data['recent_studies'], indent=2)}

Top 10 Results with Abstracts:
{sample_results_text}

Please provide insights in the following JSON format:
{{
    "summary": "A comprehensive 2-3 sentence overview of the research landscape",
    "key_findings": [
        "Finding 1: Specific insight about the data",
        "Finding 2: Another important pattern or trend",
        "Finding 3: Additional significant observation"
    ],
    "trends": [
        "Trend 1: Description of temporal or methodological trends",
        "Trend 2: Another important trend in the research"
    ],
    "recommendations": [
        "Recommendation 1: Actionable suggestion for researchers",
        "Recommendation 2: Another practical recommendation"
    ],
    "research_gaps": [
        "Gap 1: Identified area needing more research",
        "Gap 2: Another research opportunity"
    ]
}}
"""
        
        return prompt
    
    def _format_results_for_prompt(self, results_list: List[Dict]) -> str:
        """
        Format results metadata with abstracts for inclusion in the AI prompt
        """
        try:
            formatted_items = []
            
            logger.info("=" * 80)
            logger.info("ABSTRACTS INCLUDED IN LLM PROMPT:")
            logger.info("=" * 80)
            
            for i, item in enumerate(results_list, 1):
                try:
                    item_type = item.get('type', 'Unknown')
                    item_id = item.get('id') or item.get('pmid') or item.get('nctid') or 'unknown'

                    # MERGED items have pm_data / ctg_data nested → extract flat
                    pm_data  = item.get('pm_data',  {})
                    ctg_data = item.get('ctg_data', {})

                    title = (item.get('title', '') or pm_data.get('title', '') or ctg_data.get('title', '') or 'No title')

                    # Basic info
                    item_text = f"\n{i}. [{item_type}] {title}"

                    # Add key metadata (MERGED: ctg_data takes priority, PM fallback)
                    conditions = (item.get('conditions') or ctg_data.get('conditions') or pm_data.get('conditions') or [])
                    if conditions:
                        cond_list = conditions[:3] if isinstance(conditions, list) else [conditions]
                        item_text += f"\n   Conditions: {', '.join(cond_list)}"

                    interventions = (item.get('intervention_names') or ctg_data.get('intervention_names') or [])
                    if interventions:
                        intr_list = interventions[:3] if isinstance(interventions, list) else [interventions]
                        item_text += f"\n   Interventions: {', '.join(intr_list)}"

                    phase = (item.get('phase') or ctg_data.get('phase') or pm_data.get('phase') or '')
                    if phase:
                        item_text += f"\n   Phase: {phase}"

                    study_type = (item.get('study_type') or item.get('studyType')
                                  or ctg_data.get('study_type') or pm_data.get('study_type') or '')
                    if study_type:
                        item_text += f"\n   Study Type: {study_type}"

                    enrollment = (item.get('enrollment') or ctg_data.get('enrollment'))
                    if enrollment:
                        item_text += f"\n   Enrollment: {enrollment}"

                    date = (item.get('pubDate') or item.get('date')
                            or pm_data.get('pubDate') or ctg_data.get('start_date') or '')
                    if date:
                        item_text += f"\n   Date: {date}"

                    # Abstract: PM first, fallback to CTG brief_summary
                    abstract = (
                        item.get('abstract', '')
                        or pm_data.get('abstract', '')
                        or item.get('brief_summary', '')
                        or ctg_data.get('brief_summary', '')
                        or item.get('description', '')
                        or item.get('briefSummary', '')
                    )
                    if abstract:
                        # Handle different abstract formats
                        if isinstance(abstract, dict):
                            abstract_text = ' '.join(str(v) for v in abstract.values() if v)
                        elif isinstance(abstract, str):
                            abstract_text = abstract
                        else:
                            abstract_text = ''
                        
                        # Truncate if too long
                        if abstract_text:
                            if len(abstract_text) > 3000:
                                abstract_text = abstract_text[:3000] + '...'
                            item_text += f"\n   Abstract: {abstract_text}"
                            
                            # Log abstract info
                            preview = abstract_text[:50].replace('\n', ' ')
                            logger.info(f"[{i}] ID: {item_id} | Type: {item_type}")
                            logger.info(f"    Abstract preview: {preview}...")
                            logger.info(f"    Full length: {len(abstract_text)} chars")
                        else:
                            logger.info(f"[{i}] ID: {item_id} | Type: {item_type} | ⚠️  No abstract")
                    else:
                        logger.info(f"[{i}] ID: {item_id} | Type: {item_type} | ❌ No abstract field")
                    
                    formatted_items.append(item_text)
                    
                except Exception as e:
                    logger.warning(f"Failed to format result {i}: {str(e)}")
                    continue
            
            logger.info("=" * 80)
            logger.info(f"Total results with abstracts: {len([item for item in formatted_items if 'Abstract:' in item])}/{len(formatted_items)}")
            logger.info("=" * 80)
            
            return '\n'.join(formatted_items) if formatted_items else "No detailed results available"
            
        except Exception as e:
            logger.error(f"Error formatting results: {str(e)}")
            return "Error formatting results"

    def _parse_insights_response(self, response: str) -> Dict[str, Any]:
        """
        Parse and validate the AI insights response
        """
        _empty_fallback = {
            'summary': "Unable to generate insights: empty response from AI model.",
            'key_findings': [],
            'trends': [],
            'recommendations': [],
            'research_gaps': []
        }

        try:
            # Explicit handling of empty response
            if not response or not response.strip():
                insights_log.error("[PARSE ERROR] Response is empty (empty string or None)")
                insights_log.error("  Possible cause: response truncated by max_tokens or model refused to respond")
                return _empty_fallback

            # Clean up response - remove markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            # Try to parse as JSON
            insights = json.loads(cleaned_response.strip())
            
            # Validate required fields and ensure they are lists
            required_fields = ['summary', 'key_findings', 'trends', 'recommendations']
            for field in required_fields:
                if field not in insights:
                    if field == 'summary':
                        insights[field] = "Unable to generate summary at this time."
                    else:
                        insights[field] = []
                elif field != 'summary' and not isinstance(insights[field], list):
                    # Convert to list if it's not already
                    insights[field] = [str(insights[field])] if insights[field] else []
            
            # Ensure research_gaps exists
            if 'research_gaps' not in insights:
                insights['research_gaps'] = []
            elif not isinstance(insights['research_gaps'], list):
                insights['research_gaps'] = [str(insights['research_gaps'])] if insights['research_gaps'] else []

            # ── Log: parsing result ────────────────────────────────────────
            insights_log.info("[PARSED INSIGHTS] JSON parsing successful")
            insights_log.info(f"  summary        : {insights.get('summary', '')[:200]}")
            insights_log.info(f"  key_findings   : {len(insights.get('key_findings', []))} items")
            for i, kf in enumerate(insights.get('key_findings', []), 1):
                insights_log.info(f"    [{i}] {kf}")
            insights_log.info(f"  trends         : {len(insights.get('trends', []))} items")
            for i, t in enumerate(insights.get('trends', []), 1):
                insights_log.info(f"    [{i}] {t}")
            insights_log.info(f"  recommendations: {len(insights.get('recommendations', []))} items")
            for i, r in enumerate(insights.get('recommendations', []), 1):
                insights_log.info(f"    [{i}] {r}")
            insights_log.info(f"  research_gaps  : {len(insights.get('research_gaps', []))} items")
            for i, g in enumerate(insights.get('research_gaps', []), 1):
                insights_log.info(f"    [{i}] {g}")
            insights_log.info("-" * 80)
            # ─────────────────────────────────────────────────────────
            
            return insights
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Response content: {response[:500]}...")
            insights_log.error(f"[PARSE ERROR] JSON parsing failed: {e}")
            insights_log.error(f"  Raw response (500 chars): {response[:500]}")
            # Fallback if JSON parsing fails
            return {
                'summary': response[:200] + "..." if len(response) > 200 else response,
                'key_findings': [],
                'trends': [],
                'recommendations': [],
                'research_gaps': []
            }
        except Exception as e:
            logger.error(f"Unexpected error parsing insights: {e}")
            insights_log.error(f"[PARSE ERROR] Exception occurred: {e}")
            return {
                'summary': "Error processing insights response.",
                'key_findings': [],
                'trends': [],
                'recommendations': [],
                'research_gaps': []
            }
    
    def chat_about_results(self, search_key: str, message: str, page: int = 1, 
                          chat_history: List[Dict] = None, applied_filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Handle chat about the search results and insights
        Always uses page 1 results and insights for consistency
        """
        try:
            if not chat_history:
                chat_history = []

            # ── Log: chat request received ─────────────────────────────────
            insights_log.info("=" * 80)
            insights_log.info("[CHAT REQUEST] Chat message received")
            insights_log.info(f"  search_key   : {search_key}")
            insights_log.info(f"  history_len  : {len(chat_history)} turns")
            insights_log.info(f"  user_message : {message}")
            if chat_history:
                insights_log.info("  ── Previous conversation history ──")
                for i, h in enumerate(chat_history, 1):
                    role_label = "User" if h.get('role') == 'user' else "Assistant"
                    insights_log.info(f"    [{i}] {role_label}: {h.get('message', '')}")
            insights_log.info("=" * 80)
            # ────────────────────────────────────────────────────────
            
            # Always use page 1 for context (same as insights generation)
            context_page = 1
            
            # Get search results from page 1
            search_results = self.cache_service.get_search_results(search_key, context_page)
            if not search_results:
                return {'error': 'Search results not found'}
            
            # Build cache key for insights (same as generate_insights)
            insights_key = f"insights_{search_key}"
            if applied_filters:
                filter_hash = hash(json.dumps(applied_filters, sort_keys=True))
                insights_key += f"_{filter_hash}"
            
            # Get insights from cache
            insights = self.cache_service.get_insights(insights_key)
            if not insights:
                # Generate insights if not cached
                insights_result = self.generate_insights(search_key, context_page, applied_filters)
                insights = insights_result.get('insights', {})
            
            # Create context for chat
            context = self._create_chat_context(search_results, insights, applied_filters)
            
            # Generate chat response
            chat_response = self._generate_chat_response(message, context, chat_history)
            
            # Update chat history
            updated_history = chat_history + [
                {'role': 'user', 'message': message},
                {'role': 'assistant', 'message': chat_response}
            ]
            
            # ── Log: chat response ───────────────────────────────────
            insights_log.info("[CHAT RESPONSE] Assistant response")
            insights_log.info(f"  Assistant: {chat_response}")
            insights_log.info("-" * 80)
            # ────────────────────────────────────────────────────────

            return {
                'response': chat_response,
                'chat_history': updated_history,
                'context_available': True
            }
            
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            insights_log.error(f"[CHAT ERROR] {str(e)}")
            return {'error': f'Failed to process chat: {str(e)}'}
    
    def _create_chat_context(self, search_results: Dict, insights: Dict, applied_filters: Optional[Dict] = None) -> str:
        """
        Create context string for chat
        """
        context_parts = []
        
        # Add search results summary
        results = search_results.get('results', [])
        context_parts.append(f"Current page contains {len(results)} research items.")
        
        # Add insights summary
        if insights.get('summary'):
            context_parts.append(f"Research overview: {insights['summary']}")
        
        # Add key findings
        if insights.get('key_findings'):
            context_parts.append("Key findings: " + "; ".join(insights['key_findings'][:3]))
        
        # Add filter context
        if applied_filters:
            context_parts.append(f"Results are filtered by: {json.dumps(applied_filters)}")
        
        return " ".join(context_parts)
    
    def _generate_chat_response(self, message: str, context: str, chat_history: List[Dict]) -> str:
        """
        Generate chat response using OpenAI
        """
        try:
            # Prepare chat history for context
            history_text = ""
            for chat in chat_history[-3:]:  # Last 3 exchanges for context
                role = "User" if chat['role'] == 'user' else "Assistant"
                history_text += f"{role}: {chat['message']}\n"
            
            system_message = f"""You are an expert clinical research assistant helping users understand research data and insights. 

Context about the current search results:
{context}

Recent conversation:
{history_text}

Provide helpful, accurate responses about the clinical research data. Be concise but informative."""

            # ── Log: chat context + system message ───────────────
            insights_log.info("[CHAT CONTEXT] Building chat context")
            insights_log.info(f"  context (300 chars): {context[:300]}")
            insights_log.info(f"  history used (last 3 turns): {len(chat_history[-3:])} turns")
            insights_log.info("  ── FULL SYSTEM MESSAGE ──")
            insights_log.info(system_message)
            insights_log.info(f"  ── USER MESSAGE ──")
            insights_log.info(message)
            # ────────────────────────────────────────────────────────

            response = self.openai_service.generate_completion(
                prompt=message,
                system_message=system_message,
                max_tokens=800,
                temperature=0.5
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating chat response: {str(e)}")
            insights_log.error(f"[CHAT CONTEXT ERROR] {str(e)}")
            return "I'm sorry, I'm having trouble processing your question right now. Please try again."
