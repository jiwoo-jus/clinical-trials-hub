import React, { useState } from "react";
import { Search } from "lucide-react";

const DataGlossary = () => {
  const [searchInput, setSearchInput] = useState("");
  const [searchResults, setSearchResults] = useState("");
  //const [isLoading, setIsLoading] = useState(false);

  const handleSearch = async () => {
    const trimmedInput = searchInput.trim();
    if (!trimmedInput) return;

  //  setIsLoading(true);
    let result = ""
    setSearchResults(result)
  };

  return (
    <div className="mt-6 border-t pt-4">
      <div className="flex justify-between items-center border-b border-custom-border pb-2 mb-2">
          <h2 className="text-xl font-semibold text-custom-blue-deep">Structured Information Glossary</h2>
      </div>

      {/* Search Bar */}
      <div className="flex items-center gap-3 mt-auto border-custom-border pt-1 mb-2">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Enter search term"
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
      <div className=" text-sm p-4 border rounded-lg bg-gray-50 shadow-sm min-h-[120px]">
      
      <p>{searchResults}</p>
        
      </div>
    </div>
  );
};

export default DataGlossary;