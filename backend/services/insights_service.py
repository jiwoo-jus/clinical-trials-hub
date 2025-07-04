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
            # Prepare data summary for AI
            summary_data = self._prepare_data_summary(detailed_results)
            
            # Create prompt for insights generation
            prompt = self._create_insights_prompt(summary_data, applied_filters)
            
            # Generate insights using OpenAI
            response = self.openai_service.generate_completion(
                prompt=prompt,
                system_message="You are an expert clinical research analyst. Provide comprehensive, actionable insights about clinical trials and research papers. Respond only with valid JSON.",
                max_tokens=1500,
                temperature=0.3,
                response_format="json"
            )
            
            # Parse and structure the insights
            insights = self._parse_insights_response(response)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {str(e)}")
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
            if 'interventions' in metadata:
                summary['interventions'].update(metadata['interventions'])
            
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
    
    def _create_insights_prompt(self, summary_data: Dict[str, Any], applied_filters: Optional[Dict] = None) -> str:
        """
        Create a prompt for AI insights generation
        """
        filter_context = ""
        if applied_filters:
            filter_context = f"\n\nNote: The results have been filtered with the following criteria: {json.dumps(applied_filters, indent=2)}"
        
        prompt = f"""
Based on the following clinical research data summary, provide comprehensive insights and analysis:

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
