import React, { useState } from "react";
import { Search } from "lucide-react";

const MeSHGlossary = () => {
  const [searchInput, setSearchInput] = useState("");
  const [searchResults, setSearchResults] = useState("");
  //const [isLoading, setIsLoading] = useState(false);

  const getID = async (trimmedInput) => {
    const lookupEndpoint = `https://id.nlm.nih.gov/mesh/lookup/descriptor?label=${encodeURIComponent(trimmedInput)}&match=startswith`;
    const response = await fetch(lookupEndpoint);
    const data = await response.json();
    if (data.length && data[0].resource) {
      // resource is like "https://id.nlm.nih.gov/mesh/D012345"
      const match = data[0].resource.match(/D\d+/);
      if (match) {
        return match[0];
      }
    }
    return null; 
  };

  const handleSearch = async () => {
    const trimmedInput = searchInput.trim();
    if (!trimmedInput) return;

  //  setIsLoading(true);
    setSearchResults("");

    let meshID = null;
    if (!/^D\d+$/i.test(trimmedInput)) {
      meshID = await getID(trimmedInput);
      if (!meshID) {
        setSearchResults({ Error: "Term info not found." });
        return;
      }
    } else {
      meshID = trimmedInput;
    }

    const endpoint = `https://meshb.nlm.nih.gov/record/ui?ui=${meshID}`;
    const response = await fetch(endpoint);
    const htmlString = await response.text();

    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlString, 'text/html');

    const dtElements = Array.from(doc.querySelectorAll('dt'));
    const result = {};

    dtElements.forEach((dt) => {
    const values = [];
    let sibling = dt.nextElementSibling;
    while (sibling && sibling.tagName.toLowerCase() !== 'dt') {
      if (sibling.tagName.toLowerCase() === 'dd') {
        values.push(sibling.textContent.trim());
      }
      sibling = sibling.nextElementSibling;
    }
    if (values.length === 1) {
      result[dt.textContent.trim()] = values[0];
    } else if (values.length > 1) {
      result[dt.textContent.trim()] = values;
    }
    });
    setSearchResults(result)
  };

  return (
    <div className="mt-0">
      <div className="flex justify-between items-center border-b border-custom-border pb-2 mb-2">
          <h2 className="text-xl font-semibold text-custom-blue-deep">MeSH Term Glossary</h2>
      </div>

      {/* Search Bar */}
      <div className="flex items-center gap-3 mt-auto border-custom-border pt-1 mb-3">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Enter MeSH term or ID (e.g., D012345)"
          className="flex-1 border border-custom-border rounded px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-custom-blue" 
        />
        <button
          onClick={handleSearch}
          className="p-2 text-custom-deep-blue bg-transparent"
        >
          <Search className="w-5 h-5 text-custom-blue-deep" />
        </button>
      </div>

      {/* Display Area */}
      <div className=" text-sm p-4 border rounded-lg bg-gray-50 shadow-sm min-h-[100px]">
      
        {Object.entries(searchResults).map(([field, value]) => (
          <div key={field} className="mb-2">
            <span className="font-semibold text-custom-blue-deep">{field}:</span>{" "}
            {Array.isArray(value) ? (
              <ul className="list-disc list-inside ml-4">
                {value.map((item, idx) => (
                  <li key={idx} className="text-gray-700">{item}</li>
                ))}
              </ul>
            ) : field === "RDF Unique Identifier" ? (
                <a
                  href={value}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 underline"
                >
                  {value}
                </a>         
              ) : (
            <span className="text-gray-700">{value}</span>
              )
            }
              
            
          </div>
        ))}
        
      </div>
    </div>
  );
};

export default MeSHGlossary;