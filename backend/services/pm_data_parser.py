"""
PubMed XML Data Parser

This module provides functions to parse PubMed XML data from NCBI EFETCH API
and extract all necessary fields including metadata, abstracts, and NCT IDs.
"""

from typing import Dict, List, Optional, Any
import re
from bs4 import BeautifulSoup
from datetime import datetime


def parse_pubmed_xml(xml_content: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse PubMed XML content and extract all relevant fields.
    
    Args:
        xml_content: Raw XML content from NCBI EFETCH API
        
    Returns:
        Dictionary mapping PMID to extracted data:
        {
            "PMID": {
                "pmid": str,
                "pmcid": str or None,
                "title": str,
                "abstract": dict or None,
                "journal": str,
                "journal_abbrev": str,
                "journal_issn": str or None,
                "authors": List[dict],
                "pub_date": str,
                "pub_year": int or None,
                "article_date": str or None,
                "doi": str or None,
                "pii": str or None,
                "language": List[str],
                "publication_types": List[str],
                "mesh_headings": List[dict],
                "keywords": List[str],
                "chemicals": List[dict],
                "grants": List[dict],
                "ref_nctids": List[str],
                "country": str or None,
                "nlm_unique_id": str or None,
                "citation_subset": List[str],
                "coi_statement": str or None,
                "pagination": dict or None,
                "volume": str or None,
                "issue": str or None
            }
        }
    """
    results = {}
    
    try:
        # Use lxml parser for better XML handling
        soup = BeautifulSoup(xml_content, "lxml-xml")
        
        for article in soup.find_all("PubmedArticle"):
            pmid_data = _parse_single_article(article)
            if pmid_data and pmid_data["pmid"]:
                results[pmid_data["pmid"]] = pmid_data
                
    except Exception as e:
        print(f"Error parsing PubMed XML: {str(e)}")
        
    return results


def _parse_single_article(article) -> Optional[Dict[str, Any]]:
    """Parse a single PubmedArticle element."""
    try:
        # Initialize result structure
        result = {
            "pmid": None,
            "pmcid": None,
            "title": "",
            "abstract": None,
            "journal": "",
            "journal_abbrev": "",
            "journal_issn": None,
            "authors": [],
            "pub_date": "",
            "pub_year": None,
            "article_date": None,
            "doi": None,
            "pii": None,
            "language": [],
            "publication_types": [],
            "mesh_headings": [],
            "keywords": [],
            "chemicals": [],
            "grants": [],
            "ref_nctids": [],
            "country": None,
            "nlm_unique_id": None,
            "citation_subset": [],
            "coi_statement": None,
            "pagination": None,
            "volume": None,
            "issue": None
        }
        
        # Extract PMID
        pmid_tag = article.find("PMID")
        if not pmid_tag:
            return None
        result["pmid"] = pmid_tag.get_text(strip=True)
        
        # Extract article IDs (PMC, DOI, PII)
        article_id_list = article.find("ArticleIdList")
        if article_id_list:
            for article_id in article_id_list.find_all("ArticleId"):
                id_type = article_id.get("IdType", "")
                id_value = article_id.get_text(strip=True)
                
                if id_type in ["pmc", "pmcid"] and id_value.startswith("PMC"):
                    result["pmcid"] = id_value
                elif id_type == "doi":
                    result["doi"] = id_value
                elif id_type == "pii":
                    result["pii"] = id_value
        
        # Extract basic article information
        medline_citation = article.find("MedlineCitation")
        if medline_citation:
            article_elem = medline_citation.find("Article")
            if article_elem:
                # Title
                title_elem = article_elem.find("ArticleTitle")
                if title_elem:
                    result["title"] = title_elem.get_text(" ", strip=True)
                
                # Abstract
                result["abstract"] = _parse_abstract(article_elem)
                
                # Journal information
                journal_info = _parse_journal_info(article_elem)
                result.update(journal_info)
                
                # Authors
                result["authors"] = _parse_authors(article_elem)
                
                # Languages
                for lang in article_elem.find_all("Language"):
                    result["language"].append(lang.get_text(strip=True))
                
                # Publication types
                pub_type_list = article_elem.find("PublicationTypeList")
                if pub_type_list:
                    for pub_type in pub_type_list.find_all("PublicationType"):
                        result["publication_types"].append(pub_type.get_text(strip=True))
                
                # Grants
                result["grants"] = _parse_grants(article_elem)
            
            # MeSH headings
            result["mesh_headings"] = _parse_mesh_headings(medline_citation)
            
            # Keywords
            result["keywords"] = _parse_keywords(medline_citation)
            
            # Chemicals
            result["chemicals"] = _parse_chemicals(medline_citation)
            
            # Journal info from MedlineJournalInfo
            medline_journal = medline_citation.find("MedlineJournalInfo")
            if medline_journal:
                country_elem = medline_journal.find("Country")
                if country_elem:
                    result["country"] = country_elem.get_text(strip=True)
                
                nlm_id_elem = medline_journal.find("NlmUniqueID")
                if nlm_id_elem:
                    result["nlm_unique_id"] = nlm_id_elem.get_text(strip=True)
            
            # Citation subset
            for subset in medline_citation.find_all("CitationSubset"):
                result["citation_subset"].append(subset.get_text(strip=True))
            
            # COI Statement
            coi_elem = medline_citation.find("CoiStatement")
            if coi_elem:
                result["coi_statement"] = coi_elem.get_text(" ", strip=True)
        
        # Extract NCT IDs from DataBankList
        result["ref_nctids"] = _parse_nct_ids(article)
        
        return result
        
    except Exception as e:
        print(f"Error parsing single article: {str(e)}")
        return None


def _parse_abstract(article_elem) -> Optional[Dict[str, str]]:
    """Parse abstract with labels."""
    abstract_elem = article_elem.find("Abstract")
    if not abstract_elem:
        return None
    
    abstract_parts = {}
    for text_elem in abstract_elem.find_all("AbstractText"):
        label = text_elem.get("Label", "")
        if not label:
            # If no label, use "BACKGROUND" or similar default
            label = text_elem.get("NlmCategory", "UNLABELED")
        
        content = text_elem.get_text(" ", strip=True)
        if content:
            abstract_parts[label] = content
    
    return abstract_parts if abstract_parts else None


def _parse_journal_info(article_elem) -> Dict[str, Any]:
    """Parse journal information."""
    info = {
        "journal": "",
        "journal_abbrev": "",
        "journal_issn": None,
        "pub_date": "",
        "pub_year": None,
        "article_date": None,
        "volume": None,
        "issue": None,
        "pagination": None
    }
    
    journal_elem = article_elem.find("Journal")
    if journal_elem:
        # Journal title
        title_elem = journal_elem.find("Title")
        if title_elem:
            info["journal"] = title_elem.get_text(strip=True)
        
        # Journal abbreviation
        abbrev_elem = journal_elem.find("ISOAbbreviation")
        if abbrev_elem:
            info["journal_abbrev"] = abbrev_elem.get_text(strip=True)
        
        # ISSN
        issn_elem = journal_elem.find("ISSN")
        if issn_elem:
            info["journal_issn"] = issn_elem.get_text(strip=True)
        
        # Journal issue info
        issue_elem = journal_elem.find("JournalIssue")
        if issue_elem:
            # Volume
            vol_elem = issue_elem.find("Volume")
            if vol_elem:
                info["volume"] = vol_elem.get_text(strip=True)
            
            # Issue
            issue_num_elem = issue_elem.find("Issue")
            if issue_num_elem:
                info["issue"] = issue_num_elem.get_text(strip=True)
            
            # Publication date
            pub_date_elem = issue_elem.find("PubDate")
            if pub_date_elem:
                info["pub_date"], info["pub_year"] = _parse_pub_date(pub_date_elem)
    
    # Article date (electronic publication)
    article_date_elem = article_elem.find("ArticleDate")
    if article_date_elem:
        info["article_date"] = _parse_article_date(article_date_elem)
    
    # Pagination
    pagination_elem = article_elem.find("Pagination")
    if pagination_elem:
        info["pagination"] = _parse_pagination(pagination_elem)
    
    return info


def _parse_authors(article_elem) -> List[Dict[str, Any]]:
    """Parse author list."""
    authors = []
    author_list = article_elem.find("AuthorList")
    
    if author_list:
        for author in author_list.find_all("Author"):
            author_info = {}
            
            # Individual name parts
            last_name = author.find("LastName")
            if last_name:
                author_info["last_name"] = last_name.get_text(strip=True)
            
            fore_name = author.find("ForeName")
            if fore_name:
                author_info["fore_name"] = fore_name.get_text(strip=True)
            
            initials = author.find("Initials")
            if initials:
                author_info["initials"] = initials.get_text(strip=True)
            
            suffix = author.find("Suffix")
            if suffix:
                author_info["suffix"] = suffix.get_text(strip=True)
            
            # Collective name
            collective = author.find("CollectiveName")
            if collective:
                author_info["collective_name"] = collective.get_text(strip=True)
            
            # Combine name for display
            if "last_name" in author_info:
                name_parts = []
                if "fore_name" in author_info:
                    name_parts.append(author_info["fore_name"])
                if "last_name" in author_info:
                    name_parts.append(author_info["last_name"])
                if "suffix" in author_info:
                    name_parts.append(author_info["suffix"])
                author_info["name"] = " ".join(name_parts)
            elif "collective_name" in author_info:
                author_info["name"] = author_info["collective_name"]
            
            # Affiliations
            affiliations = []
            for affil in author.find_all("AffiliationInfo"):
                affil_elem = affil.find("Affiliation")
                if affil_elem:
                    affiliations.append(affil_elem.get_text(" ", strip=True))
            author_info["affiliations"] = affiliations
            
            # Author attributes
            author_info["valid"] = author.get("ValidYN", "Y") == "Y"
            author_info["equal_contrib"] = author.get("EqualContrib", "N") == "Y"
            
            if author_info:
                authors.append(author_info)
    
    return authors


def _parse_mesh_headings(medline_citation) -> List[Dict[str, Any]]:
    """Parse MeSH headings."""
    mesh_headings = []
    mesh_list = medline_citation.find("MeshHeadingList")
    
    if mesh_list:
        for mesh in mesh_list.find_all("MeshHeading"):
            mesh_info = {}
            
            # Descriptor
            descriptor = mesh.find("DescriptorName")
            if descriptor:
                mesh_info["descriptor"] = descriptor.get_text(strip=True)
                mesh_info["descriptor_major"] = descriptor.get("MajorTopicYN", "N") == "Y"
                mesh_info["descriptor_ui"] = descriptor.get("UI", "")
            
            # Qualifiers
            qualifiers = []
            for qualifier in mesh.find_all("QualifierName"):
                qual_info = {
                    "name": qualifier.get_text(strip=True),
                    "major": qualifier.get("MajorTopicYN", "N") == "Y",
                    "ui": qualifier.get("UI", "")
                }
                qualifiers.append(qual_info)
            mesh_info["qualifiers"] = qualifiers
            
            if mesh_info:
                mesh_headings.append(mesh_info)
    
    return mesh_headings


def _parse_keywords(medline_citation) -> List[str]:
    """Parse keywords."""
    keywords = []
    
    for keyword_list in medline_citation.find_all("KeywordList"):
        for keyword in keyword_list.find_all("Keyword"):
            keywords.append(keyword.get_text(" ", strip=True))
    
    return keywords


def _parse_chemicals(medline_citation) -> List[Dict[str, str]]:
    """Parse chemical list."""
    chemicals = []
    chem_list = medline_citation.find("ChemicalList")
    
    if chem_list:
        for chemical in chem_list.find_all("Chemical"):
            chem_info = {}
            
            reg_num = chemical.find("RegistryNumber")
            if reg_num:
                chem_info["registry_number"] = reg_num.get_text(strip=True)
            
            name_elem = chemical.find("NameOfSubstance")
            if name_elem:
                chem_info["name"] = name_elem.get_text(strip=True)
                chem_info["ui"] = name_elem.get("UI", "")
            
            if chem_info:
                chemicals.append(chem_info)
    
    return chemicals


def _parse_grants(article_elem) -> List[Dict[str, str]]:
    """Parse grant list."""
    grants = []
    grant_list = article_elem.find("GrantList")
    
    if grant_list:
        for grant in grant_list.find_all("Grant"):
            grant_info = {}
            
            grant_id = grant.find("GrantID")
            if grant_id:
                grant_info["grant_id"] = grant_id.get_text(strip=True)
            
            acronym = grant.find("Acronym")
            if acronym:
                grant_info["acronym"] = acronym.get_text(strip=True)
            
            agency = grant.find("Agency")
            if agency:
                grant_info["agency"] = agency.get_text(strip=True)
            
            country = grant.find("Country")
            if country:
                grant_info["country"] = country.get_text(strip=True)
            
            if grant_info:
                grants.append(grant_info)
    
    return grants


def _parse_nct_ids(article) -> List[str]:
    """Parse NCT IDs from DataBankList."""
    nct_ids = []
    
    # Look in DataBankList
    medline_citation = article.find("MedlineCitation")
    if medline_citation:
        article_elem = medline_citation.find("Article")
        if article_elem:
            databank_list = article_elem.find("DataBankList")
            if databank_list:
                for databank in databank_list.find_all("DataBank"):
                    databank_name = databank.find("DataBankName")
                    if databank_name and "ClinicalTrials.gov" in databank_name.get_text():
                        accession_list = databank.find("AccessionNumberList")
                        if accession_list:
                            for accession in accession_list.find_all("AccessionNumber"):
                                nct_id = accession.get_text(strip=True)
                                if nct_id.startswith("NCT"):
                                    nct_ids.append(nct_id)
    
    return nct_ids


def _parse_pub_date(pub_date_elem) -> tuple[str, Optional[int]]:
    """Parse publication date."""
    year_elem = pub_date_elem.find("Year")
    month_elem = pub_date_elem.find("Month")
    day_elem = pub_date_elem.find("Day")
    medline_date = pub_date_elem.find("MedlineDate")
    
    if medline_date:
        date_str = medline_date.get_text(strip=True)
        # Try to extract year from MedlineDate
        year_match = re.search(r'(\d{4})', date_str)
        year = int(year_match.group(1)) if year_match else None
        return date_str, year
    
    date_parts = []
    year = None
    
    if year_elem:
        year_str = year_elem.get_text(strip=True)
        year = int(year_str) if year_str.isdigit() else None
        date_parts.append(year_str)
    
    if month_elem:
        date_parts.append(month_elem.get_text(strip=True))
    
    if day_elem:
        date_parts.append(day_elem.get_text(strip=True))
    
    return " ".join(date_parts), year


def _parse_article_date(article_date_elem) -> str:
    """Parse electronic article date."""
    year = article_date_elem.find("Year")
    month = article_date_elem.find("Month")
    day = article_date_elem.find("Day")
    
    date_parts = []
    if year:
        date_parts.append(year.get_text(strip=True))
    if month:
        date_parts.append(month.get_text(strip=True))
    if day:
        date_parts.append(day.get_text(strip=True))
    
    return "-".join(date_parts)


def _parse_pagination(pagination_elem) -> Dict[str, str]:
    """Parse pagination information."""
    pagination = {}
    
    start_page = pagination_elem.find("StartPage")
    if start_page:
        pagination["start_page"] = start_page.get_text(strip=True)
    
    end_page = pagination_elem.find("EndPage")
    if end_page:
        pagination["end_page"] = end_page.get_text(strip=True)
    
    medline_pgn = pagination_elem.find("MedlinePgn")
    if medline_pgn:
        pagination["medline_pgn"] = medline_pgn.get_text(strip=True)
    
    return pagination
