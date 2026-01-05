import json
import logging
from typing import Dict, List, Any, Optional
from services.openai_service import OpenAIService
from services.cache_service import CacheService
from services.ctg_service import CTGService
from services.pm_service import PMService

logger = logging.getLogger(__name__)

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
            
            # Create prompt for insights generation
            prompt = self._create_insights_prompt(summary_data, results_list, applied_filters, user_query)
            logger.info(f"Created prompt with length: {len(prompt)} characters")
            
            # Generate insights using OpenAI
            response = self.openai_service.generate_completion(
                prompt=prompt,
                system_message="You are an expert clinical research analyst. Provide comprehensive, actionable insights about clinical trials and research papers. Respond only with valid JSON.",
                max_tokens=2000,
                temperature=0.3,
                response_format="json"
            )
            
            logger.info(f"Received OpenAI response with length: {len(response) if response else 0}")
            
            # DEBUG: Print the actual OpenAI response
            logger.info("=== DEBUG: OPENAI RESPONSE ===")
            logger.info(response)
            logger.info("=== END OPENAI RESPONSE ===")
            
            print("=== DEBUG: OPENAI RESPONSE ===")
            print(response)
            print("=== END OPENAI RESPONSE ===")
            
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
            
            # Count by type
            if item_type == 'PM':
                summary['pm_count'] += 1
            elif item_type == 'CTG':
                summary['ctg_count'] += 1
            elif item_type == 'MERGED':
                summary['merged_count'] += 1
            
            # Extract conditions and interventions
            if 'conditions' in item:
                if isinstance(item['conditions'], list):
                    summary['conditions'].update(item['conditions'])
                elif isinstance(item['conditions'], str):
                    summary['conditions'].add(item['conditions'])
                    
            if 'intervention_names' in item:
                if isinstance(item['intervention_names'], list):
                    summary['interventions'].update(item['intervention_names'])
                elif isinstance(item['intervention_names'], str):
                    summary['interventions'].add(item['intervention_names'])
            
            # Extract study information
            if 'phase' in item:
                summary['study_phases'].add(item['phase'])
            if 'studyType' in item:
                summary['study_types'].add(item['studyType'])
            if 'journal' in item:
                summary['journals'].add(item['journal'])
            
            # Add recent studies (with publication date)
            if item.get('pubDate') or item.get('date'):
                summary['recent_studies'].append({
                    'title': item.get('title', ''),
                    'date': item.get('pubDate') or item.get('date'),
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
        sample_results_text = self._format_results_for_prompt(results_list[:10])
        
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
                    title = item.get('title', 'No title')
                    item_id = item.get('id') or item.get('pmid') or item.get('nctid') or 'unknown'
                    
                    # Basic info
                    item_text = f"\n{i}. [{item_type}] {title}"
                    
                    # Add key metadata
                    if item.get('conditions'):
                        conditions = item['conditions'][:3] if isinstance(item['conditions'], list) else [item['conditions']]
                        item_text += f"\n   Conditions: {', '.join(conditions)}"
                    
                    if item.get('intervention_names'):
                        interventions = item['intervention_names'][:3] if isinstance(item['intervention_names'], list) else [item['intervention_names']]
                        item_text += f"\n   Interventions: {', '.join(interventions)}"
                    
                    if item.get('phase'):
                        item_text += f"\n   Phase: {item['phase']}"
                    
                    if item.get('studyType'):
                        item_text += f"\n   Study Type: {item['studyType']}"
                    
                    if item.get('enrollment'):
                        item_text += f"\n   Enrollment: {item['enrollment']}"
                    
                    if item.get('pubDate') or item.get('date'):
                        date = item.get('pubDate') or item.get('date')
                        item_text += f"\n   Date: {date}"
                    
                    # Add abstract (most important for insights!)
                    abstract = item.get('abstract', '') or item.get('description', '') or item.get('briefSummary', '')
                    if abstract:
                        # Handle different abstract formats
                        if isinstance(abstract, dict):
                            abstract_text = ' '.join(str(v) for v in abstract.values() if v)
                        elif isinstance(abstract, str):
                            abstract_text = abstract
                        else:
                            abstract_text = ''
                        
                        # Truncate if too long (keep more than before for better insights)
                        if abstract_text:
                            if len(abstract_text) > 800:
                                abstract_text = abstract_text[:800] + '...'
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
        try:
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
            
            return insights
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Response content: {response[:500]}...")
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
            
            return {
                'response': chat_response,
                'chat_history': updated_history,
                'context_available': True
            }
            
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
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

            response = self.openai_service.generate_completion(
                prompt=message,
                system_message=system_message,
                max_tokens=800,
                temperature=0.5
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating chat response: {str(e)}")
            return "I'm sorry, I'm having trouble processing your question right now. Please try again."
