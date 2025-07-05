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
        Generate AI insights for search results on a specific page
        """
        try:
            logger.info(f"Generating insights for search_key: {search_key}, page: {page}")
            
            # Get search results from cache
            search_results = self.cache_service.get_search_results(search_key, page)
            if not search_results:
                return {'error': 'Search results not found'}
            
            # Get detailed data for results on this page
            detailed_results = self._get_detailed_results(search_results.get('results', []))
            
            if not detailed_results:
                return {'error': 'No results found for insights generation'}
            
            # Generate insights using OpenAI
            insights = self._generate_ai_insights(detailed_results, applied_filters)
            
            # Cache the insights
            insights_key = f"insights_{search_key}_{page}"
            if applied_filters:
                filter_hash = hash(json.dumps(applied_filters, sort_keys=True))
                insights_key += f"_{filter_hash}"
            
            self.cache_service.cache_insights(insights_key, insights)
            
            return {
                'insights': insights,
                'page': page,
                'total_results': len(detailed_results),
                'insights_key': insights_key
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
    
    def _generate_ai_insights(self, detailed_results: List[Dict], applied_filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate AI insights from detailed results
        """
        try:
            logger.info(f"Starting AI insights generation for {len(detailed_results)} results")
            
            # Prepare data summary for AI
            summary_data = self._prepare_data_summary(detailed_results)
            logger.info(f"Prepared summary data: {len(summary_data)} fields")
            
            # Create prompt for insights generation (now includes detailed results)
            prompt = self._create_insights_prompt(summary_data, detailed_results, applied_filters)
            logger.info(f"Created prompt with length: {len(prompt)} characters")
            
            # DEBUG: Print the actual prompt content
            logger.info("=== DEBUG: ACTUAL PROMPT CONTENT ===")
            logger.info(prompt)
            logger.info("=== END PROMPT CONTENT ===")
            
            print("=== DEBUG: ACTUAL PROMPT CONTENT ===")
            print(prompt)
            print("=== END PROMPT CONTENT ===")
            
            # Generate insights using OpenAI
            response = self.openai_service.generate_completion(
                prompt=prompt,
                system_message="You are an expert clinical research analyst. Provide comprehensive, actionable insights about clinical trials and research papers. Respond only with valid JSON.",
                max_tokens=2000,  # Increased to handle larger prompt with detailed data
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
    
    def _prepare_data_summary(self, detailed_results: List[Dict]) -> Dict[str, Any]:
        """
        Prepare a structured summary of the data for AI analysis
        """
        summary = {
            'total_items': len(detailed_results),
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
        
        for item in detailed_results:
            metadata = item.get('metadata', {})
            item_type = metadata.get('type', '')
            
            # Count by type
            if item_type == 'PM':
                summary['pm_count'] += 1
            elif item_type == 'CTG':
                summary['ctg_count'] += 1
            elif item_type == 'MERGED':
                summary['merged_count'] += 1
            
            # Extract conditions and interventions
            if 'conditions' in metadata:
                summary['conditions'].update(metadata['conditions'])
            if 'intervention_names' in metadata:
                summary['interventions'].update(metadata['intervention_names'])
            
            # Extract study information
            if 'phase' in metadata:
                summary['study_phases'].add(metadata['phase'])
            if 'studyType' in metadata:
                summary['study_types'].add(metadata['studyType'])
            if 'journal' in metadata:
                summary['journals'].add(metadata['journal'])
            
            # Add recent studies (with publication date)
            if metadata.get('pubDate') or metadata.get('date'):
                summary['recent_studies'].append({
                    'title': metadata.get('title', ''),
                    'date': metadata.get('pubDate') or metadata.get('date'),
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
    
    def _create_insights_prompt(self, summary_data: Dict[str, Any], detailed_results: List[Dict], applied_filters: Optional[Dict] = None) -> str:
        """
        Create a prompt for AI insights generation including detailed results data
        """
        filter_context = ""
        if applied_filters:
            filter_context = f"\n\nNote: The results have been filtered with the following criteria: {json.dumps(applied_filters, indent=2)}"
        
        # Prepare detailed results data for the prompt
        detailed_items_text = self._format_detailed_results_for_prompt(detailed_results)
        
        prompt = f"""
Based on the following clinical research data summary and detailed results, provide comprehensive insights and analysis:

Data Summary:
- Total items analyzed: {summary_data['total_items']}
- PubMed papers: {summary_data['pm_count']}
- Clinical trials: {summary_data['ctg_count']}
- Merged items: {summary_data['merged_count']}

Key Conditions: {', '.join(summary_data['conditions'][:5])}
Key Interventions: {', '.join(summary_data['interventions'][:5])}
Study Phases: {', '.join(summary_data['study_phases'])}
Study Types: {', '.join(summary_data['study_types'])}
Top Journals: {', '.join(summary_data['journals'][:3])}

Recent Studies: {json.dumps(summary_data['recent_studies'], indent=2)}

Detailed Results Data:
{detailed_items_text}
{filter_context}

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
    
    def _format_detailed_results_for_prompt(self, detailed_results: List[Dict]) -> str:
        """
        Format detailed results data for inclusion in the AI prompt
        """
        try:
            formatted_items = []
            
            for i, item in enumerate(detailed_results[:10], 1):  # Limit to max 10 items
                try:
                    metadata = item.get('metadata', {})
                    item_type = metadata.get('type', 'Unknown')
                    
                    # Basic metadata
                    item_text = f"Item {i} ({item_type}):\n"
                    item_text += f"- Title: {metadata.get('title', 'N/A')}\n"
                    
                    if item_type == 'PM':
                        # PubMed specific data
                        item_text += f"- PMID: {metadata.get('pmid', 'N/A')}\n"
                        item_text += f"- Journal: {metadata.get('journal', 'N/A')}\n"
                        item_text += f"- Publication Date: {metadata.get('pubDate', 'N/A')}\n"
                        item_text += f"- Authors: {', '.join(metadata.get('authors', [])[:3])}\n"  # First 3 authors
                        
                        # Abstract
                        abstract = metadata.get('abstract', '')
                        if isinstance(abstract, dict):
                            abstract_text = ' '.join(str(v) for v in abstract.values() if v)
                        elif isinstance(abstract, str):
                            abstract_text = abstract
                        else:
                            abstract_text = 'N/A'
                        
                        if abstract_text and abstract_text != 'N/A':
                            # Truncate abstract if too long
                            abstract_text = abstract_text[:500] + '...' if len(abstract_text) > 500 else abstract_text
                            item_text += f"- Abstract: {abstract_text}\n"
                        
                        # Additional metadata
                        item_text += f"- DOI: {metadata.get('doi', 'N/A')}\n"
                        mesh_terms = [str(m.get('descriptor', m)) for m in metadata.get('mesh_headings', [])[:5]]
                        item_text += f"- MeSH Terms: {', '.join(mesh_terms)}\n"
                        item_text += f"- Keywords: {', '.join(metadata.get('keywords', [])[:5])}\n"
                        item_text += f"- Study Type: {metadata.get('study_type', 'N/A')}\n"
                        item_text += f"- Phase: {metadata.get('phase', 'N/A')}\n"
                        
                    elif item_type == 'CTG':
                        # Clinical Trial specific data
                        item_text += f"- NCT ID: {metadata.get('id', 'N/A')}\n"
                        item_text += f"- Status: {metadata.get('status', 'N/A')}\n"
                        item_text += f"- Phase: {metadata.get('phase', 'N/A')}\n"
                        item_text += f"- Study Type: {metadata.get('studyType', 'N/A')}\n"
                        item_text += f"- Conditions: {', '.join(metadata.get('conditions', [])[:5])}\n"
                        item_text += f"- Interventions: {', '.join(metadata.get('intervention_names', [])[:5])}\n"
                        item_text += f"- Start Date: {metadata.get('date', 'N/A')}\n"
                        item_text += f"- Enrollment: {metadata.get('enrollment', 'N/A')}\n"
                        item_text += f"- Sponsor: {metadata.get('sponsor', 'N/A')}\n"
                        
                        # Brief summary
                        brief_summary = metadata.get('briefSummary', '')
                        if brief_summary:
                            brief_summary = brief_summary[:500] + '...' if len(brief_summary) > 500 else brief_summary
                            item_text += f"- Brief Summary: {brief_summary}\n"
                        
                    elif item_type == 'MERGED':
                        # Merged item data
                        item_text += f"- PMID: {metadata.get('pmid', 'N/A')}\n"
                        item_text += f"- NCT ID: {metadata.get('nctid', 'N/A')}\n"
                        item_text += f"- Journal: {metadata.get('journal', 'N/A')}\n"
                        item_text += f"- Publication Date: {metadata.get('pubDate', 'N/A')}\n"
                        item_text += f"- Trial Status: {metadata.get('status', 'N/A')}\n"
                        item_text += f"- Phase: {metadata.get('phase', 'N/A')}\n"
                        item_text += f"- Conditions: {', '.join(metadata.get('conditions', [])[:5])}\n"
                        item_text += f"- Interventions: {', '.join(metadata.get('intervention_names', [])[:5])}\n"
                        
                        # Include both PM and CTG abstracts/summaries if available
                        pm_abstract = metadata.get('abstract', '')
                        if isinstance(pm_abstract, dict):
                            pm_abstract = ' '.join(str(v) for v in pm_abstract.values() if v)
                        if pm_abstract:
                            pm_abstract = pm_abstract[:400] + '...' if len(pm_abstract) > 400 else pm_abstract
                            item_text += f"- Paper Abstract: {pm_abstract}\n"
                        
                        trial_summary = metadata.get('briefSummary', '')
                        if trial_summary:
                            trial_summary = trial_summary[:400] + '...' if len(trial_summary) > 400 else trial_summary
                            item_text += f"- Trial Summary: {trial_summary}\n"
                    
                    item_text += "\n"
                    formatted_items.append(item_text)
                
                except Exception as e:
                    logger.warning(f"Error formatting item {i}: {str(e)}")
                    # Add basic fallback formatting
                    formatted_items.append(f"Item {i}: {metadata.get('title', 'Unknown title')}\n\n")
            
            return '\n'.join(formatted_items)
        
        except Exception as e:
            logger.error(f"Error formatting detailed results: {str(e)}")
            return "Error: Unable to format detailed results data."

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
        """
        try:
            if not chat_history:
                chat_history = []
            
            # Get search results and insights context
            search_results = self.cache_service.get_search_results(search_key, page)
            if not search_results:
                return {'error': 'Search results not found'}
            
            # Get or generate insights for context
            insights_key = f"insights_{search_key}_{page}"
            if applied_filters:
                filter_hash = hash(json.dumps(applied_filters, sort_keys=True))
                insights_key += f"_{filter_hash}"
            
            insights = self.cache_service.get_insights(insights_key)
            if not insights:
                # Generate insights if not cached
                insights_result = self.generate_insights(search_key, page, applied_filters)
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
