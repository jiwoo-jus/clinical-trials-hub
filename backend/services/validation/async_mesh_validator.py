"""
Async MeSH (Medical Subject Headings) Term Validation Service

Asynchronous medical term validation and normalization using the NCBI MeSH API
"""

import aiohttp
import asyncio
import json
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Any
from urllib.parse import quote


class AsyncMeshValidator:
    """Asynchronous MeSH term validation and normalization class"""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.mesh_api_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.mesh_cache = {}  # Simple cache
        self.session = session
        self._own_session = session is None
        
    async def __aenter__(self):
        if self._own_session:
            self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._own_session and self.session:
            await self.session.close()
    
    async def validate_terms_async(self, terms: List[str]) -> Dict[str, Any]:
        """Asynchronous validation of a list of MeSH terms"""
        if not self.session:
            async with aiohttp.ClientSession() as session:
                self.session = session
                return await self._validate_terms_with_session(terms)
        else:
            return await self._validate_terms_with_session(terms)
    
    async def _validate_terms_with_session(self, terms: List[str]) -> Dict[str, Any]:
        """Validate a list of terms using a session"""
        results = {
            "validated_terms": [],
            "invalid_terms": [],
            "suggestions": {},
            "normalized_terms": {}
        }
        
        # Create parallel validation tasks
        tasks = []
        for term in terms:
            if term and term.strip():
                task = self.validate_term_async(term.strip())
                tasks.append((term, task))
        
        if not tasks:
            return results
        
        # Execute all validation tasks
        validation_results = await asyncio.gather(
            *(task for _, task in tasks),
            return_exceptions=True
        )
        
        # Process results
        for i, (original_term, _) in enumerate(tasks):
            result = validation_results[i]
            
            if isinstance(result, Exception):
                print(f"[AsyncMeshValidator] Error validating '{original_term}': {result}")
                results["invalid_terms"].append(original_term)
                continue
            
            if result.get("is_valid", False):
                results["validated_terms"].append({
                    "original": original_term,
                    "mesh_term": result["mesh_term"],
                    "mesh_id": result.get("mesh_id"),
                    "confidence": result.get("confidence", 1.0)
                })
                
                if result.get("normalized"):
                    results["normalized_terms"][original_term] = result["mesh_term"]
            else:
                results["invalid_terms"].append(original_term)
                if result.get("suggestions"):
                    results["suggestions"][original_term] = result["suggestions"]
        
        return results
    
    async def validate_term_async(self, term: str) -> Dict[str, Any]:
        """Asynchronous validation of a single MeSH term"""
        print(f"[AsyncMeshValidator] [validate_term_async] Validating term: {term}")
        if not term or not term.strip():
            return {"is_valid": False, "reason": "Empty term"}
        
        term_clean = term.strip().lower()
        
        # Check cache
        if term_clean in self.mesh_cache:
            return self.mesh_cache[term_clean]
        
        # No session, create a temporary one
        if not self.session:
            async with aiohttp.ClientSession() as session:
                self.session = session
                result = await self._validate_single_term(term)
                self.session = None
                return result
        else:
            result = await self._validate_single_term(term)
        
        # Save to cache
        self.mesh_cache[term_clean] = result
        return result
    
    async def _validate_single_term(self, term: str) -> Dict[str, Any]:
        """Validate a single term (internal method)"""
        print(f"[AsyncMeshValidator] [_validate_single_term] Searching for term: {term}")
        # 1. Attempt direct match
        direct_result = await self._search_mesh_direct(term)
        if direct_result["is_valid"]:
            print(f"[AsyncMeshValidator] [_validate_single_term] Direct match found for term: {term}")
            return direct_result
        
        # 2. Search for similar terms
        similar_result = await self._search_mesh_similar(term)
        print(f"[AsyncMeshValidator] [_validate_single_term] Similar match result for term '{term}': {similar_result}")
        return similar_result
    
    async def _search_mesh_direct(self, term: str) -> Dict[str, Any]:
        """Direct search using the MeSH API (asynchronous)"""
        try:
            # Use ESearch to search the MeSH database
            print(f"[AsyncMeshValidator] [_search_mesh_direct] Searching MeSH for term: {term}")
            search_url = f"{self.mesh_api_base}/esearch.fcgi"
            params = {
                "db": "mesh",
                "term": f'"{term}"[MeSH Terms]',
                "retmode": "json",
                "retmax": 5
            }
            
            async with self.session.get(search_url, params=params, timeout=10) as response:
                response.raise_for_status()
                search_data = await response.json()
            
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                return {"is_valid": False, "reason": "No direct match found"}
            
            # Use EFetch to retrieve detailed information
            fetch_url = f"{self.mesh_api_base}/efetch.fcgi"
            fetch_params = {
                "db": "mesh",
                "id": ",".join(id_list[:3]),  # Limit to 3
                "retmode": "xml"
            }
            
            async with self.session.get(fetch_url, params=fetch_params, timeout=10) as fetch_response:
                fetch_response.raise_for_status()
                xml_content = await fetch_response.text()
            
            # Parse XML to extract MeSH terms
            mesh_terms = self._parse_mesh_xml(xml_content)
            
            if mesh_terms:
                print(f"[AsyncMeshValidator] [_search_mesh_direct] Found MeSH terms: {mesh_terms}")
                best_match = mesh_terms[0]  # Use the first result
                return {
                    "is_valid": True,
                    "mesh_term": best_match["term"],
                    "mesh_id": best_match["id"],
                    "normalized": best_match["term"].lower() != term.lower(),
                    "confidence": 0.9
                }
            
            return {"is_valid": False, "reason": "Failed to parse MeSH data"}
            
        except Exception as e:
            print(f"[AsyncMeshValidator] API error for term '{term}': {e}")
            return {"is_valid": False, "reason": f"API error: {str(e)}"}
    
    async def _search_mesh_similar(self, term: str) -> Dict[str, Any]:
        """Search for similar MeSH terms (asynchronous)"""
        try:
            # More lenient search
            search_url = f"{self.mesh_api_base}/esearch.fcgi"
            
            # Try multiple search strategies
            search_strategies = [
                f"{term}[All Fields]",
                f"{term}*[All Fields]",  # Wildcard
                f"*{term}*[All Fields]"  # Partial match
            ]
            
            suggestions = []
            
            for strategy in search_strategies:
                params = {
                    "db": "mesh",
                    "term": strategy,
                    "retmode": "json",
                    "retmax": 10
                }
                
                try:
                    async with self.session.get(search_url, params=params, timeout=10) as response:
                        if response.status == 200:
                            search_data = await response.json()
                            id_list = search_data.get("esearchresult", {}).get("idlist", [])
                            
                            if id_list:
                                # Get term names for top results
                                mesh_terms = await self._get_mesh_terms_by_ids(id_list[:5])
                                for mesh_term in mesh_terms:
                                    similarity = self._calculate_similarity(term, mesh_term["term"])
                                    if similarity > 0.6:
                                        suggestions.append({
                                            "term": mesh_term["term"],
                                            "id": mesh_term["id"],
                                            "similarity": similarity
                                        })
                    
                    if suggestions:
                        break  # Stop if found
                        
                except Exception as e:
                    print(f"[AsyncMeshValidator] Search strategy '{strategy}' failed: {e}")
                    continue
            
            if suggestions:
                # Sort by similarity
                suggestions.sort(key=lambda x: x["similarity"], reverse=True)
                best_suggestion = suggestions[0]
                
                if best_suggestion["similarity"] > 0.8:
                    return {
                        "is_valid": True,
                        "mesh_term": best_suggestion["term"],
                        "mesh_id": best_suggestion["id"],
                        "normalized": True,
                        "confidence": best_suggestion["similarity"],
                        "suggestions": suggestions[:3]
                    }
                else:
                    return {
                        "is_valid": False,
                        "reason": "Low similarity to existing MeSH terms",
                        "suggestions": suggestions[:3]
                    }
            
            return {"is_valid": False, "reason": "No similar MeSH terms found"}
            
        except Exception as e:
            print(f"[AsyncMeshValidator] Similarity search error for term '{term}': {e}")
            return {"is_valid": False, "reason": f"Similarity search error: {str(e)}"}
    
    async def _get_mesh_terms_by_ids(self, id_list: List[str]) -> List[Dict[str, str]]:
        """Retrieve term names from a list of MeSH IDs (asynchronous)"""
        try:
            fetch_url = f"{self.mesh_api_base}/efetch.fcgi"
            fetch_params = {
                "db": "mesh",
                "id": ",".join(id_list),
                "retmode": "xml"
            }
            
            async with self.session.get(fetch_url, params=fetch_params, timeout=10) as response:
                response.raise_for_status()
                xml_content = await response.text()
            
            return self._parse_mesh_xml(xml_content)
            
        except Exception as e:
            print(f"[AsyncMeshValidator] Error fetching MeSH terms by IDs: {e}")
            return []
    
    def _parse_mesh_xml(self, xml_content: str) -> List[Dict[str, str]]:
        """Parse MeSH XML response"""
        mesh_terms = []
        
        try:
            # XML parsing
            root = ET.fromstring(xml_content)
            
            # Find DescriptorRecord elements
            for descriptor in root.findall('.//DescriptorRecord'):
                # Extract DescriptorUI (MeSH ID)
                mesh_id_elem = descriptor.find('.//DescriptorUI')
                mesh_id = mesh_id_elem.text if mesh_id_elem is not None else ""
                
                # Extract DescriptorName
                name_elem = descriptor.find('.//DescriptorName/String')
                mesh_term = name_elem.text if name_elem is not None else ""
                
                if mesh_term:
                    mesh_terms.append({
                        "id": mesh_id,
                        "term": mesh_term
                    })
            
        except ET.ParseError as e:
            print(f"[AsyncMeshValidator] XML parsing error: {e}")
        except Exception as e:
            print(f"[AsyncMeshValidator] Unexpected error parsing XML: {e}")
        
        return mesh_terms
    
    def _calculate_similarity(self, term1: str, term2: str) -> float:
        """Calculate similarity between two terms (simple Jaccard similarity)"""
        if not term1 or not term2:
            return 0.0
        
        # Convert to lowercase and split by words
        words1 = set(term1.lower().split())
        words2 = set(term2.lower().split())
        
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 1.0 if term1.lower() == term2.lower() else 0.0
        
        return intersection / union


# Convenience functions
async def validate_mesh_terms_async(terms: List[str]) -> Dict[str, Any]:
    """Asynchronously validate a list of MeSH terms"""
    async with AsyncMeshValidator() as validator:
        return await validator.validate_terms_async(terms)


async def validate_condition_terms_async(conditions: List[str]) -> Dict[str, Any]:
    """Asynchronously validate condition (disease) terms"""
    return await validate_mesh_terms_async(conditions)


async def validate_intervention_terms_async(interventions: List[str]) -> Dict[str, Any]:
    """Asynchronously validate intervention terms"""
    return await validate_mesh_terms_async(interventions)


# Synchronous wrapper functions for backward compatibility
def validate_mesh_terms_sync(terms: List[str]) -> Dict[str, Any]:
    """Synchronous version of MeSH term validation"""
    return asyncio.run(validate_mesh_terms_async(terms))


def validate_condition_terms_sync(conditions: List[str]) -> Dict[str, Any]:
    """Synchronous version of condition term validation"""
    return asyncio.run(validate_condition_terms_async(conditions))


def validate_intervention_terms_sync(interventions: List[str]) -> Dict[str, Any]:
    """Synchronous version of intervention term validation"""
    return asyncio.run(validate_intervention_terms_async(interventions))
