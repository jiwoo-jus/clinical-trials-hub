import React, { useState } from 'react';
import Header from '../components/Header';
import PropTypes from 'prop-types'
import { Microscope, Hospital, Pill} from 'lucide-react'

function ManualPage() {

  const UseCaseCard = ({ title, description, workflow, outcomes }) => {
  const [open, setOpen] = useState(true);

  return (
    <div className="border border-custom-border overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left px-4 py-3 bg-blue-50 hover:bg-blue-100 transition flex justify-between items-center"
      >
        <div>
          <h3 className="text-base font-bold text-custom-blue">{title}</h3>
          <p className="text-sm text-custom-text-subtle mt-1">{description}</p>
        </div>
        <span className="text-custom-blue font-bold text-lg">{open ? '-' : '+'}</span>
      </button>
      {open && (
        <div className="bg-white px-4 py-4 space-y-4 border-t">
          <div>
            <h4 className="text-sm font-semibold text-custom-text">Demonstration Workflow</h4>
            <ul className="list-disc list-inside text-sm text-custom-text-subtle mt-1 pl-4">
              {Object.entries(workflow).map(([key, value]) => (
                <li key={key}><strong className="font-semibold">{key}:</strong> {value}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-custom-text">Outcomes</h4>
            <ul className="list-disc list-inside text-sm text-custom-text-subtle mt-1 pl-4">
              {outcomes.map((outcome, index) => (
                <li key={index}>{outcome}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
  };
  UseCaseCard.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  workflow: PropTypes.objectOf(PropTypes.string).isRequired,
  outcomes: PropTypes.arrayOf(PropTypes.string).isRequired,
};
  // const useCases = [
  //   {
  //     title: 'Systematic Review for Researchers',
  //     description: 'Dr. Sarah Chen reduces months of systematic review work into days.',
  //     workflow: {
  //       'Initial Search': 'Natural language query "CAR-T therapy pediatric ALL phase 2 3 trials outcomes"',
  //       'Automated Expansion': 'Structured searches across multiple databases',
  //       'Comprehensive Retrieval': '127 studies found across PubMed and ClinicalTrials.gov',
  //       'Intelligent Filtering': 'Phase, age, outcome filters applied',
  //       'Structured Extraction': 'GPT-4o extracts standardized data from full-texts',
  //       'Export and Analysis': 'Exported in PRISMA-compliant formats'
  //     },
  //     outcomes: [
  //       '98.3% time saved (480 hours to 8 hours)',
  //       '23 more trials identified than manual search',
  //       'Automated PRISMA flow diagram generated'
  //     ]
  //   },
  //   {
  //     title: 'Clinical Decision Support for Oncologists',
  //     description: 'Dr. Rodriguez uses the system to compare trial options for a difficult case.',
  //     workflow: {
  //       'Targeted Search': '"myelofibrosis post-ruxolitinib failure clinical trials"',
  //       'Real-time Filtering': 'Filters by trial status, age, JAK2 status',
  //       'Geographic Proximity': '100-mile radius site filter',
  //       'Efficacy Comparison': 'Generated comparative efficacy table',
  //       'Safety Profile': 'Aggregated adverse event data'
  //     },
  //     outcomes: [
  //       '7 suitable trials identified (vs. 3 manually)',
  //       'Head-to-head efficacy comparisons enabled',
  //       'Improved shared decision-making'
  //     ]
  //   },
  //   {
  //     title: 'Medical Education and Training',
  //     description: 'Dr. Lisa Park creates an educational module on multiple myeloma treatment.',
  //     workflow: {
  //       'Historical Search': '"multiple myeloma clinical trials 2000-2025"',
  //       'Paradigm Tracking': 'Identifies major treatment milestones and FDA approvals',
  //       'Visual Timeline': 'Generated treatment evolution timeline',
  //       'Case-Based Learning': 'Representative trial cases extracted',
  //       'Knowledge Assessment': 'Auto-generated quiz questions'
  //     },
  //     outcomes: [
  //       '25 years of trial data condensed in one module',
  //       'Structured progression from basic to advanced',
  //       'Real trial data supports interactive learning'
  //     ]
  //   },
  //   {
  //     title: 'Patient Empowerment and Advocacy',
  //     description: 'Maria Gonzalez explores trial options after immunotherapy progression.',
  //     workflow: {
  //       'Plain Language Search': '"melanoma trials after immunotherapy stops working"',
  //       'Eligibility Prescreening': 'Highlights criteria in patient-friendly language',
  //       'Location Mapping': 'Interactive trial site map with contact info',
  //       'Question Generation': 'AI suggests questions for oncologist',
  //       'Trial Comparison': 'Side-by-side requirement and benefit comparison'
  //     },
  //     outcomes: [
  //       'Improved communication with care team',
  //       'Reduced info gap between patients and providers',
  //       'Increased likelihood of trial enrollment'
  //     ]
  //   },
  //   {
  //     title: 'Pharmaceutical Competitive Intelligence',
  //     description: 'A pharma team investigates BTK inhibitor pipelines in autoimmune disease.',
  //     workflow: {
  //       'Competitor Analysis': 'Search for "BTK inhibitors autoimmune diseases all phases"',
  //       'Patent Linkage': 'Cross-referenced with IP databases',
  //       'Failure Analysis': 'Extracted discontinuation reasons',
  //       'Market Sizing': 'Enrollment data aggregated',
  //       'Development Timeline': 'Approval projections based on history'
  //     },
  //     outcomes: [
  //       '43 trials across 12 indications identified',
  //       '3 new competitor programs discovered',
  //       'Risk assessment improved through failure mode analysis'
  //     ]
  //   }
  // ];

  return (
    <>
      <Header />
      <div className="px-6 py-8 max-w-screen-2xl mx-auto">
        <h1 className="text-3xl font-bold text-black mb-6">About ClinicalTrialsHub</h1>

        {/* Intro Section */}
        <div className="bg-custom-blue-bg p-6 border border-custom-border mb-8">
          <h2 className="text-xl font-bold text-custom-blue-deep mb-2">What is ClinicalTrialsHub?</h2>
          <p className="text-sm text-custom-text-subtle mb-2">
            Clinical Trials Hub is a central platform designed to simplify and supercharge how users access and analyze clinical trial data. Whether you are a physician, researcher, student, or patient, our intuitive interface and powerful GPT-4o backend make analyzing and utilizing trial data easier and faster than ever.
          </p>

          <h3 className="text-sm font-semibold text-custom-text-subtle mb-1">Core Problems:</h3>
          <ul className="list-disc list-inside text-sm text-custom-text-subtle pl-4">
            <li>Clinical trials are lengthy and costly (median 7.3 years, average $117.4 million).</li>
            <li>Meta-analyses are crucial but highly manual and labor-intensive (3-4 researchers take approx. 16 months for one clinical question).</li>
          </ul>

          <h3 className="text-sm font-semibold text-custom-text-subtle mt-2 mb-1">Our Objective:</h3>
          <ul className="list-disc list-inside text-sm text-custom-text-subtle pl-4">
            <li>Provide a centralized hub for query generation, information extraction, and question answering in clinical trials using GPT-4o</li>
            <li>Reduce R&D time and cost with fast, intelligent search.</li>
            <li>Access structured insights from both PubMed and ClinicalTrials.gov.</li>
            <li>Empower evidence-based medicine with immediate answers and clean summaries.</li>
          </ul>
        </div>

        {/* Section: System Overview */}
        <section className="mb-8">
          <h2 className="text-xl font-bold text-custom-blue-deep mb-2">System Overview & Interface Design</h2>
          <p className="text-sm text-custom-text leading-relaxed">
            Our system is purpose-built through iterative collaboration with clinical practitioners, ensuring that every design choice aligns with real-world workflows. From peer-reviewed publication prioritization to guided user onboarding, every detail is tuned for practical clinical needs. 
          </p>
          <p className="text-sm text-custom-text leading-relaxed mt-2">
            On arrival, users can initiate a search via our robust search interface, which supports both natural language queries ( &quot;latest immunotherapy trials for triple-negative breast cancer&quot;) and structured field inputs (condition: &quot;TNBC&quot;, intervention: &quot;pembrolizumab&quot;, phase: &quot;3&quot;). Results display in a unified view with visual indicators distinguishing data sources, merger status, and extraction confidence levels. 
            For each result, a dynamic summary panel automatically generates high-level insights, including trial counts by phase, FDA approval status, enrollment patterns, and time-based distributions. These features work together to streamline user navigation and decision-making, all grounded in a design philosophy centered on accessibility, clarity, and clinical impact.
          </p>
        </section>

        {/* Section: Data Sources */}
        <section className="mb-8">
          <h2 className="text-xl font-bold text-custom-blue-deep mb-2">Data Sources</h2>
          <table className="min-w-full text-sm table-auto mt-4 text-custom-text border ">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-2 border-b border-r bg-blue-50 text-custom-text w-[50%]">ClinicalTrials.gov</th>
              <th className="px-4 py-2 border-b bg-blue-50 text-custom-text w-[50%]">PubMed / PubMed Central</th>
            </tr>
          </thead>
          <tbody>
            <tr>
                <td className="px-4 bg-white py-2 align-top border-r">
                    This is a public registry of clinical trials which aims provide detailed information about clinical research studies to the public, researchers, and health care professionals. It 
                    contains structured fields like trial phase, status, and enrollment 
                    numbers. 
                </td>
                <td className="px-4 bg-white py-2">
                    This is a repository that provides full-text 
                    access to open-access biomedical research articles. It serves as 
                    a primary source of full-text documents, aim to extract structured 
                    information, especially for detailed outcome measures or 
                    statistical results.
                </td>
            </tr>
          </tbody>
          </table>
        </section>

        {/* Section: Workflow Details*/}
        <section className="mb-10">
          <h2 className="text-xl font-bold text-custom-blue-deep ">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
            <div className="bg-white border p-4 shadow-sm">
              <h3 className="text-md font-bold text-custom-blue">Identification</h3>
              <h3 className="text-sm font-bold text-custom-text-subtle">Query Generation</h3>
              <p className="text-sm text-custom-text mt-1">When a user submits a query in natural language (e.g. &quot;Find studies on the effect of donepezil in men over 70 with dementia&quot;), our model generates optimized queries tailored to each database (PubMed, PMC, ClinicalTrials.gov), automatically retrieving relevant records.   </p>
            </div>
            <div className="bg-white border p-4 shadow-sm">
              <h3 className="text-md font-bold text-custom-blue">Screening</h3>
              <h3 className="text-sm font-bold text-custom-text-subtle">Information Extraction</h3>
              <p className="text-sm text-custom-text mt-1">
               Using our structured information extraction model, users can apply trial-specific filters—such as intervention dosage, subgroup population, or outcome measure—that are not searchable through conventional title/abstract filtering    </p>
            </div>
            <div className="bg-white border p-4 shadow-sm">
              <h3 className="text-md font-bold text-custom-blue">Eligibility</h3>
              <h3 className="text-sm font-bold text-custom-text-subtle">Question Answering</h3>
              <p className="text-sm text-custom-text mt-1">
           For detailed clinical questions not explicitly recorded in metadata fields, users can ask our chatbot and receive immediate answers, along with supporting evidence highlighted from the full text.     </p>
            </div>
          </div>
        </section>

        {/* Section: Users */}
        <section className="mb-10">
          <h2 className="text-xl font-bold text-custom-blue-deep ">Primary Users</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-5">
            <div className="flex flex-col items-center  ">
                <Microscope size={35} strokeWidth={1.75} />
                <h3 className="text-md font-bold mt-3 text-custom-blue">Clinical Researchers</h3>
                <p className="text-sm text-center text-custom-text mt-1">Performing meta-analyses and systematic reviews</p>
            </div>
            <div className="flex flex-col items-center  ">
                <Hospital size={35} strokeWidth={1.75} />
                <h3 className="text-md font-bold mt-3 text-custom-blue">Physicians</h3>
                <p className="text-sm text-center text-custom-text mt-1">Searching and summarizing clinical trial information for specific conditions</p>
            </div>
            <div className="flex flex-col items-center  ">
                <Pill size={35} strokeWidth={1.75} />
                <h3 className="text-md font-bold mt-3 text-custom-blue">Pharmaceutical Professionals</h3>
                <p className="text-sm text-center text-custom-text mt-1">Formulating drug development strategies and analyzing competitive landscapes</p>
            </div>
          </div>
        </section>

        {/* Section: Use Case Scenarios */}
        {/* <section className="space-y-8">

          <h2 className="text-xl font-bold text-custom-blue-deep ">Use Case Scenarios</h2>
          {useCases.map((useCase, idx) => (
            <UseCaseCard key={idx} {...useCase} />
          ))}

        </section> */}
      </div>
    </>
  );
}

export default ManualPage;
