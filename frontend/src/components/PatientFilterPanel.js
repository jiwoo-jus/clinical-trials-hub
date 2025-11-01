// import { Filter } from 'lucide-react';
import PropTypes from 'prop-types';
import React from 'react';
import { useState, useEffect } from "react";
import { Info, X, Plus, Minus } from 'lucide-react'

// Add a mapping for field names to display labels
const fieldLabels = {
  cond: 'Condition',
  intr: 'Intervention',
  other_term: 'Other Terms'
};

const phases = [
  'Early Phase 1',
  'Phase 1',
  'Phase 2',
  'Phase 3',
  'Phase 4'
]; 
const types = [
  "Interventional",
  "Observational",
  "Expanded Access"
]
const sponsors = [
  'NIH',
  'Industry',
  'U.S. federal agency',
  'All others  (individuals, universities, organizations)'
]; 



export const PatientFilterPanel = ({ filters, setFilters }) => {
  // showMore feature removed (code retained for possible future reactivation)
  // const [showMore, setShowMore] = React.useState(false);
  const [query, setQuery] = useState(filters["location"] || "");
  const [selected, setSelected] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [glossary, setGlossary] = useState(false);
  const [term, setTerm] = useState("")
  const [showFilters, setShowFilters] = useState(false)

  // ✅ useEffect + debounce pattern
  useEffect(() => {
    if (!query || query.length < 2 || selected) {
      setSuggestions([]); // hide dropdown if too short
      return;
    }

    const delayDebounce = setTimeout(async () => {
      setLoading(true);
      try {
        const url = `https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&limit=5&dedupe=1&q=${encodeURIComponent(query)}`;
        const res = await fetch(url, {
          headers: { "User-Agent": "ClinicalTrialsHub/1.0" }
        });

        const data = await res.json();

        // ✅ Only keep meaningful places (no roads or POIs)
        const filtered = data.filter(item =>
          ["city", "town", "village", "state", "country"].includes(item.addresstype)
        );

        setSuggestions(filtered);
      } catch (err) {
        console.error("Error fetching suggestions:", err);
      } finally {
        setLoading(false);
      }
    }, 400); // ✅ wait 400ms after user stops typing

    // ✅ cleanup function to clear timer on next keystroke
    return () => clearTimeout(delayDebounce);
  }, [query, selected]);
  

  // ✅ When user clicks a suggestion
  const handleSelect = (place) => {
    const addr = place.address;

    const city = addr.city || addr.town || addr.village || "";
    const state = addr.state || "";
    const country = addr.country || "";

    // ✅ update filters with full structured info
    setFilters((prev) => ({
      ...prev,
      location: place.display_name,
      city,
      state,
      country
    }));

    setQuery(formatLocation(place.address));
    setSuggestions([]); // hide dropdown
    setSelected(true);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFilters({
      ...filters,
      [name]: value === '' ? null : value,
    });
  };

const handleCheckboxChange = (e, key) => {
  const { value, checked } = e.target;

  setFilters((prev) => {
    const currentList = prev[key] || [];
    const updatedList = checked
      ? [...currentList, value]
      : currentList.filter((item) => item !== value);

    return {
      ...prev,
      [key]: updatedList,
    };
  });
};

  const formatLocation = (address) => {
  // Fallback city logic
  const city = address.city || address.town || address.village || "";

  // Handle US abbreviation logic
  let state = address.state || "";
  if (address.country_code === "us" && address["ISO3166-2-lvl4"]) {
    // Extract abbreviation from 'US-XX'
    const isoParts = address["ISO3166-2-lvl4"].split("-");
    if (isoParts.length === 2) {
      state = isoParts[1];
    }
  }

  const country = address.country || "";

  // Filter out empty values and join
  const parts = [city, state, country].filter(Boolean);
  return parts.join(", ");
  };

  return (
    <div className="w-full max-w-7xl mx-auto px-4 flex">
      <div className="w-full bg-white light:border-primary-12 light:bg-secondary-100 rounded-2xl light:shadow-splash-chatpgpt-input p-6 mb-3 border">
        {/* Basic Filters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {['cond', 'intr', 'other_term'].map((field, idx) => (
            <div key={idx}>
              <label className="block text-sm font-medium text-primary-100 capitalize">
                {fieldLabels[field] || field.replace('_', ' ')}
              </label>
              <input
                type="text"
                name={field}
                value={filters[field] || ''}
                onChange={handleChange}
                placeholder={`e.g., ${field === 'cond' ? 'Diabetes' : field === 'intr' ? 'Insulin' : 'RCT'}`}
                className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input"
              />
            </div>
          ))}
          
        </div>
        <div className="flex items-center justify-center mt-3">
          <div className="border-b basis-[50%] border-gray-200 "></div>
          <button className="p-1 bg-gray-100 rounded-full mx-2" onClick={() => setShowFilters(!showFilters)}>
            {showFilters ? <Minus size={14}/> : <Plus size={14}/>}
          </button>
          <div className="border-b basis-[50%] border-gray-200"></div>
        </div>

        {/* Structured Filters */}
        {showFilters && ( 
        <div className="pt-2 grid grid-cols-1 md:grid-cols-3 gap-4">

          <div>
            <label className="block text-sm font-medium text-primary-100 capitalize">sex</label>
            <select value={filters["sex"] || ""} onChange={handleChange} name="sex" className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input">
              <option value=''></option>
              <option value="MALE">Male</option>
              <option value="FEMALE">Female</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-100 capitalize">location</label>
            <input
              type="text"
              name="location"
              value={query}
              onChange={function handleInputChange(e) {
                setQuery(e.target.value);
                setSelected(false) } }
              placeholder="e.g., Columbus, Ohio"
              className="mt-1 block w-full border rounded-2xl px-4 py-2 text-sm"
            />
          {loading && query.length >= 2 && (
            <div className="absolute bg-white text-gray-500 px-2 py-1 text-xs">
              Loading...
            </div>
          )}

          {!selected && suggestions.length > 0 && (
            <ul className="absolute bg-white border rounded-md shadow-md mt-1 w-[20.75%] z-10 max-h-48 overflow-auto">
              {suggestions.map((place) => (
                <li
                  key={place.place_id}
                  className="p-2 hover:bg-gray-100 cursor-pointer text-sm block w-full border px-4 py-2 text-sm"
                  onClick={() => handleSelect(place)}
                >
                  {formatLocation(place.address)}
                </li>
              ))}
            </ul>
          )}
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-100 capitalize">age range</label>
            <div className="space-y-2">
             <div className="flex gap-x-2  items-center">
              <select value={filters["age1"] || ""} onChange={handleChange} name="age1"
                className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input flex-1"
              >
                <option value=""></option>
                {Array.from({ length: 99 }, (_, i) => i + 1).map((age) => (
                  <option key={age} value={age}>
                    {age}
                  </option>
                ))}
              </select>
              <span className="text-sm text-custom-text">to</span>
              <select value={filters["age2"] || ""} onChange={handleChange} name="age2"
                className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input flex-1"
              >
                <option value=""></option>
                {Array.from({ length: 99 }, (_, i) => i + 1).map((age) => (
                  <option key={age} value={age}>
                    {age}
                  </option>
                ))}
              </select>
             </div>
            </div>
          </div>

          {/* <div>
            <label className="block text-sm font-medium text-primary-100 capitalize">sponsor</label>
            <input type="text" name="sponsor" placeholder="e.g., NIH"
                value={filters["sponsor"] || ""}
                onChange={handleChange} className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input"/>
          </div> */ }

          {/*<div>
            <label className="block text-sm font-medium text-primary-100 capitalize">status</label>
            <select value={filters["status"] || ""} onChange={handleChange} name="status" className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input">
              <option value=""></option>
                {statuses.map((each, i) => (
                  <option key={i} value={each}>{each}</option>
                ))}
            </select>
          </div> */}

           <div>
            <div className="flex gap-1">
              <label className="block text-sm font-medium text-primary-100 capitalize">phase</label>
              <span
                className="flex items-center justify-center rounded-full w-6 h-6"
              >
                <Info size={16} strokeWidth = {3} className="rounded-full text-blue-700 hover:text-neutral-500"
                onClick={function handleClick() {
                  setGlossary(true) 
                  setTerm("phase")
                  }}/>
              </span>
            </div>
            <div className="flex flex-wrap gap-1 mt-2">
            {phases.map((type, i) => (
              <div
                key={i}
                className="flex items-center space-x-2 border light:border-primary-12 rounded-3xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input"
              >
                <input
                  type="checkbox"
                  name="phase"
                  value={type}
                  checked={filters.phase?.includes(type) || false}
                  onChange={(e) => handleCheckboxChange(e, "phase")}
                  className="form-checkbox text-primary-100"
                />
                <span className="text-sm text-primary-100">{type}</span>
              </div>
            ))}
            </div>
          </div> 
          <div>
            <div className="flex gap-1">
              <label className="block text-sm font-medium text-primary-100 capitalize">study type</label>
              <span
                className="flex items-center justify-center rounded-full w-6 h-6"
              >
                <Info size={16} strokeWidth = {3} className="rounded-full text-blue-700 hover:text-neutral-500"
                onClick={function handleClick() {
                  setGlossary(true) 
                  setTerm("type")
                  }} />
              </span>
            </div>
            <div className="flex flex-wrap gap-1 mt-2">
            {types.map((type, i) => (
              <div
                key={i}
                className="flex items-center space-x-2 border light:border-primary-12 rounded-3xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input"
              >
                <input
                  type="checkbox"
                  name="studyType"
                  value={type}
                  checked={filters.studyType?.includes(type) || false}
                  onChange={(e) => handleCheckboxChange(e, "studyType")}
                  className="form-checkbox text-primary-100"
                />
                <span className="text-sm text-primary-100">{type}</span>
              </div>
            ))}
            </div>
          </div>
          <div>
            <div className="flex gap-1">
              <label className="block text-sm font-medium text-primary-100 capitalize">sponsor</label>
              <span
                className="flex items-center justify-center rounded-full w-6 h-6"
              >
                <Info size={16} strokeWidth = {3} className="rounded-full text-blue-700 hover:text-neutral-500" 
                onClick={function handleClick() {
                  setGlossary(true) 
                  setTerm("sponsor")
                  }}/>
              </span>
            </div>
            
            <div className="flex flex-wrap gap-1 mt-2">
            {sponsors.map((type, i) => (
              <div
                key={i}
                className="flex items-center space-x-2 border light:border-primary-12 rounded-3xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input"
              >
                <input
                  type="checkbox"
                  name="sponsor"
                  value={type}
                  checked={filters.sponsor?.includes(type) || false}
                  onChange={(e) => handleCheckboxChange(e, "sponsor")}
                  className="form-checkbox text-primary-100"
                />
                <span className="text-sm text-primary-100">{type}</span>
              </div>
            ))}
            </div>
          </div>

        { /*   <div>
            <label className="block text-sm font-medium text-primary-100 capitalize">allocation</label>
            <select value={filters["allocation"] || ""} onChange={handleChange} name="allocation" className="mt-1 block w-full border light:border-primary-12 rounded-2xl px-4 py-2 text-sm light:shadow-splash-chatpgpt-input">
              <option value=""></option>
                {allocs.map((each, i) => (
                  <option key={i} value={each}>{each}</option>
                ))}
            </select>
          </div> */ }

        </div>
        )}

      </div>
      { glossary && (
        <div className="ml-2 w-1/2 bg-gray-100 light:border-primary-12 light:bg-secondary-100 rounded-2xl light:shadow-splash-chatpgpt-input p-6 mb-6 border relative">
          <button className="absolute top-2 m-4 right-2 rounded-full text-red-500 p-1 hover:bg-gray-300 bg-gray-200"onClick = {() => setGlossary(false)}>
            <X size={15} strokeWidth={3}/>
          </button>
        { term === "phase" && (
          <div>
              <p className="font-bold text-custom-blue-deep text-md">Study Phase</p>
              <div className="mt-2 pr-4 text-sm">Each <span className="text-blue-500 font-semibold">phase</span> of a drug-related clinical trial is identified by a number.</div>
              <ul className=" text-sm mt-3 space-y-2">
                <li>Early Phase 1: Exploratory trials with no therapeutic or diagnostic intent (e.g., screening studies).</li>
                <li>Phase 1: Includes initial studies to determine safety, side effects, and processing of a drug.</li>
                <li>Phase 2: Controlled clinical studies conducted on patients to determine any short-term risks associated with the drug</li>
                <li>Phase 3: Trials conducted after preliminary evidence is gathered to confirm effectiveness and assess the risk-benefit relationship of a drug.</li>
                <li>Phase 4: Studies of FDA-approved drugs to track information such as the risks, benefits, and optimal use of the drug.</li>
              </ul>
          </div>
        )}

        { term === "type" && (
          <div>
              <p className="font-bold text-custom-blue-deep text-md">Study Type</p>
              <div className="mt-2 pr-4 text-sm">The <span className="text-blue-500 font-semibold">study type</span> describes the nature of the investigation or investigational use for which clinical study information is being submitted.</div>
              <ul className=" text-sm mt-3 space-y-2">
                <li>Interventional: Participants are assigned an intervention to evaluate the effect of the intervention on biomedical or other health related outcomes.</li>
                <li>Observational: Studies in humans where health outcomes are assessed in predefined groups. Participants may receive diagnostic or therapeutic care, but researchers do not assign specific treatments—they observe outcomes from routine care or other interventions.</li>
                <li>Expanded Access: An investigational drug product available through expanded access for patients who do not qualify for enrollment in a clinical trial.</li>
              </ul>
          </div>
        )}

        { term === "sponsor" && (
          <div>
              <p className="font-bold text-custom-blue-deep text-md">Sponsor</p>
              <div className="mt-2 pr-4 text-sm">The organization or person who initiates the study and who has authority and control over the study.</div>
          </div>
        )}
        
        </div>
      )}
      
    </div>
  );
};

PatientFilterPanel.propTypes = {
  filters: PropTypes.object.isRequired,
  setFilters: PropTypes.func.isRequired,
};
