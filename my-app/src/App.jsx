import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
// import remarkGfm from 'remark-gfm'; // UNCOMMENT THIS LINE LOCALLY
import { BarChart, FileText, Database, PenTool, Play, Loader2, Settings, Layers, CheckCircle, Code, Image as ImageIcon, Sparkles } from 'lucide-react';

const App = () => {
  const [activeTab, setActiveTab] = useState('ingestion');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  
  // User Input State
  const [instructions, setInstructions] = useState("");

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setData(null); // Clear previous data
    try {
      const response = await fetch('http://localhost:8000/generate-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            // FIX: Send empty string "" instead of null to avoid 422 Validation Error
            user_instructions: instructions.trim() 
        }),
      });
      
      const result = await response.json();
      if (result.error) throw new Error(result.error);
      
      setData(result);
      setActiveTab('synthesis'); // Jump to the final report directly for better UX
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // --- 1. Ingestion View ---
  const IngestionView = ({ data }) => (
    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-lg text-gray-800">Data Source Configuration</h3>
          <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full flex items-center gap-1">
            <CheckCircle size={12} /> {data?.status || "Ready"}
          </span>
      </div>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-4 rounded shadow-sm border text-center">
            <div className="text-sm text-gray-500">Total Records</div>
            <div className="text-2xl font-bold text-indigo-600">{data?.row_count?.toLocaleString() || 0}</div>
        </div>
        <div className="bg-white p-4 rounded shadow-sm border text-center col-span-2">
            <div className="text-sm text-gray-500 mb-1">Detected Columns</div>
            <div className="flex flex-wrap gap-1 justify-center">
                {data?.columns?.slice(0, 6).map(c => (
                    <span key={c} className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-600 font-mono">{c}</span>
                ))}
                {(data?.columns?.length > 6) && <span className="text-xs text-gray-400">+{data.columns.length - 6} more</span>}
            </div>
        </div>
      </div>
    </div>
  );

  // --- 2. Pandas View (Quantitative - Iterates through LIST) ---
  const PandasAgentView = ({ data }) => {
    // Check if data is an array and has items
    if (!data || !Array.isArray(data) || data.length === 0) {
        return <div className="text-gray-400 italic p-4">No quantitative analysis performed in this step.</div>;
    }

    return (
        <div className="space-y-12">
            {data.map((item, index) => (
                <div key={index} className="border-b border-gray-200 pb-8 last:border-0 last:pb-0">
                    {/* Section Header */}
                    <div className="flex items-center gap-3 mb-4">
                        <div className="bg-blue-100 p-2 rounded-full text-blue-600">
                            <span className="font-bold text-sm">{index + 1}</span>
                        </div>
                        <h3 className="text-lg font-bold text-gray-800">{item.section || `Analysis Step ${index + 1}`}</h3>
                    </div>

                    <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 mb-6">
                        <h4 className="font-bold text-blue-800 mb-1 flex items-center gap-2 text-sm uppercase tracking-wide">
                            <BarChart size={14}/> Execution Task
                        </h4>
                        <p className="text-blue-700 font-medium text-sm leading-relaxed">{item.query}</p>
                    </div>

                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                        {/* Code Block */}
                        <div className="border rounded-lg overflow-hidden shadow-sm flex flex-col bg-gray-900">
                            <div className="bg-gray-800 text-gray-300 px-4 py-2 text-xs font-mono flex justify-between items-center border-b border-gray-700">
                                <span className="flex items-center gap-2"><Code size={12}/> Python Code</span>
                                <span className="opacity-50">Pandas Agent</span>
                            </div>
                            <pre className="p-4 text-xs text-green-400 font-mono overflow-auto h-64 custom-scrollbar">
                                {item.code || "# No code generated"}
                            </pre>
                        </div>

                        {/* Plot Area */}
                        <div className="border rounded-lg p-4 shadow-sm flex flex-col items-center justify-center bg-white min-h-[250px]">
                            {item.image ? (
                                <div className="w-full h-full flex flex-col items-center">
                                    <img 
                                        src={`data:image/png;base64,${item.image}`} 
                                        alt={`Plot for ${item.section}`} 
                                        className="max-h-64 object-contain rounded hover:scale-105 transition-transform duration-300"
                                    />
                                    <span className="text-xs text-gray-400 mt-2 flex items-center gap-1">
                                        <ImageIcon size={10}/> Generated Plot
                                    </span>
                                </div>
                            ) : (
                                <div className="text-center text-gray-400">
                                    <BarChart size={48} className="mx-auto mb-2 opacity-20"/>
                                    <p className="text-sm">No visualization generated</p>
                                </div>
                            )}
                        </div>
                    </div>
                    
                    {item.insight && (
                        <div className="mt-4 bg-white p-4 border rounded-lg border-l-4 border-l-blue-500 shadow-sm">
                            <h4 className="font-bold mb-1 text-gray-800 text-sm uppercase">Key Findings:</h4>
                            <p className="text-gray-700 text-sm">{item.insight}</p>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
  };

  // --- 3. RAG View (Qualitative - Iterates through LIST) ---
  const RAGAgentView = ({ data }) => {
    if (!data || !Array.isArray(data) || data.length === 0) {
        return <div className="text-gray-400 italic p-4">No qualitative research performed in this step.</div>;
    }
    
    return (
        <div className="space-y-12">
             {data.map((item, index) => (
                <div key={index} className="border-b border-gray-200 pb-8 last:border-0 last:pb-0">
                    {/* Section Header */}
                     <div className="flex items-center gap-3 mb-4">
                        <div className="bg-purple-100 p-2 rounded-full text-purple-600">
                            <span className="font-bold text-sm">{index + 1}</span>
                        </div>
                        <h3 className="text-lg font-bold text-gray-800">{item.section || `Research Step ${index + 1}`}</h3>
                    </div>

                    <div className="bg-purple-50 p-4 rounded-lg border border-purple-100 mb-6">
                        <h4 className="font-bold text-purple-800 mb-1 flex items-center gap-2 text-sm uppercase tracking-wide">
                            <Database size={14}/> Research Question
                        </h4>
                        <p className="text-purple-700 font-medium text-sm">{item.query}</p>
                    </div>

                    <div className="bg-white border rounded-lg shadow-sm mb-4">
                        <div className="px-4 py-2 bg-gray-50 border-b flex items-center gap-2 text-xs font-bold text-gray-500 uppercase">
                            <Layers size={12}/> Context Retrieved from Vector DB
                        </div>
                        <div className="p-4 bg-white text-xs text-gray-600 h-48 overflow-y-auto whitespace-pre-wrap font-mono leading-relaxed custom-scrollbar">
                            {item.context || "No context found."}
                        </div>
                    </div>

                    {item.insight && (
                        <div className="bg-green-50 border border-green-100 p-4 rounded-lg border-l-4 border-l-green-500 shadow-sm">
                            <h4 className="font-bold text-green-800 mb-1 text-sm uppercase">Research Insight:</h4>
                            <p className="text-green-700 leading-relaxed text-sm">{item.insight}</p>
                        </div>
                    )}
                </div>
             ))}
        </div>
    );
  };

  // --- 4. Final Report View ---
  const SynthesisView = ({ data }) => {
    const reportHeader = `# BMW Global Sales Analysis Report (2020-2024)\n> Generated by AI Multi-Agent System\n\n---\n\n`;
    const fullMarkdown = reportHeader + (data?.markdown_content || "*Report generation pending...*");

    return (
        <div className="bg-white shadow-lg rounded-lg border border-gray-200 overflow-hidden">
            <div className="bg-gray-800 text-white p-4 flex justify-between items-center">
                <h3 className="font-bold flex items-center gap-2"><PenTool size={18}/> Final Executive Report</h3>
                <span className="text-xs bg-gray-700 px-2 py-1 rounded">Markdown Preview</span>
            </div>
            <div className="p-8 max-w-4xl mx-auto min-h-[500px]">
                <article className="prose prose-slate lg:prose-lg mx-auto prose-headings:text-indigo-900 prose-a:text-blue-600 prose-img:rounded-xl prose-img:shadow-lg prose-table:border prose-th:bg-gray-100 prose-th:p-2 prose-td:p-2">
                    <ReactMarkdown 
                        // remarkPlugins={[remarkGfm]} // UNCOMMENT THIS LINE LOCALLY FOR TABLE SUPPORT
                    >
                        {fullMarkdown.replace(/!\[.*?\]\(.*?\)/g, "")}
                    </ReactMarkdown>
                </article>
            </div>
        </div>
    );
  };

  // --- Main Layout ---
  return (
    <div className="min-h-screen bg-slate-100 p-8 font-sans text-gray-800">
      <div className="max-w-6xl mx-auto">
        
        {/* Header & Input Section */}
        <div className="mb-8 space-y-4">
            <div>
                <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Multi-Agent Insight Engine</h1>
                <p className="text-slate-500">Orchestrating Pandas, ChromaDB, and GPT-5 for Automated Reporting</p>
            </div>
            
            {/* Input Box */}
            <div className="bg-white p-1 rounded-xl shadow-sm border border-gray-200 flex gap-0 focus-within:ring-2 ring-indigo-500 ring-offset-2 transition-all">
                 <div className="flex-1 relative">
                    <textarea 
                        className="w-full h-full p-4 pb-8 border-0 bg-transparent focus:ring-0 resize-none text-gray-700 placeholder-gray-400 text-base"
                        rows="2"
                        placeholder="Describe your analysis goal (e.g., 'Compare SUV vs Sedan sales trends in 2023'). Leave blank if you want to use sample template."
                        value={instructions}
                        onChange={(e) => setInstructions(e.target.value)}
                    />
                    <button
                        onClick={() => setInstructions("Trend & Growth Analysis \n- Analyze the sales trend of Hybrid vehicles over the last 3 years and explain the market shift towards electrification. \n- Show me the monthly sales volume for 2023. Identify the peak month and research what marketing events or vehicle launches happened then. \n- Compare Year-over-Year growth for SUVs versus Sedans. Why are SUVs trending higher?")} 
                        className="absolute bottom-3 left-4 text-xs font-medium text-gray-400 hover:text-indigo-600 bg-gray-50 hover:bg-indigo-50 px-2 py-1 rounded-md transition-all flex items-center gap-1"
                    >
                        <Sparkles size={12}/> Use Sample Prompt
                    </button>
                 </div>
                <button 
                    onClick={handleGenerate} 
                    disabled={loading}
                    className={`px-8 rounded-r-lg font-bold text-white transition-all flex flex-col items-center justify-center min-w-[140px]
                        ${loading ? 'bg-slate-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'}`}
                >
                    {loading ? <Loader2 className="animate-spin mb-1" /> : <Play size={24} className="mb-1 fill-current" />}
                    <span className="text-xs uppercase tracking-wider">{loading ? "Thinking" : "Generate"}</span>
                </button>
            </div>
        </div>

        {error && (
             <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded mb-6 shadow-sm">
                <strong>System Error:</strong> {error}
             </div>
        )}

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-0 pl-2">
            {[
                { id: 'ingestion', label: '1. Ingestion', icon: FileText },
                { id: 'pandas', label: '2. Pandas Agent', icon: BarChart },
                { id: 'rag', label: '3. RAG Agent', icon: Database },
                { id: 'synthesis', label: '4. Final Report', icon: PenTool },
            ].map((tab) => (
                <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-6 py-3 rounded-t-lg font-medium transition-all text-sm
                        ${activeTab === tab.id 
                            ? 'bg-white text-indigo-600 border-t border-x border-gray-200 shadow-[0_-2px_10px_rgba(0,0,0,0.05)] relative z-10' 
                            : 'bg-gray-100 text-gray-500 hover:bg-gray-200 hover:text-gray-700'}`}
                >
                    <tab.icon size={16} />
                    {tab.label}
                    {/* Counters for results */}
                    {tab.id === 'pandas' && data?.pandas_agent?.length > 0 && (
                        <span className="bg-indigo-100 text-indigo-600 text-xs px-2 py-0.5 rounded-full ml-1">{data.pandas_agent.length}</span>
                    )}
                    {tab.id === 'rag' && data?.rag_agent?.length > 0 && (
                        <span className="bg-indigo-100 text-indigo-600 text-xs px-2 py-0.5 rounded-full ml-1">{data.rag_agent.length}</span>
                    )}
                </button>
            ))}
        </div>

        {/* Main Content Area */}
        <div className="bg-white rounded-b-xl rounded-tr-xl min-h-[500px] p-6 shadow-sm border border-gray-200 relative z-0">
            {!data && !loading && (
                <div className="text-center py-32 opacity-50 select-none">
                    <Settings size={64} className="mx-auto mb-4 text-gray-300"/>
                    <p className="text-lg text-gray-400">System Ready. Awaiting Instructions.</p>
                </div>
            )}

            {loading && (
                 <div className="flex flex-col items-center justify-center py-32 space-y-6">
                    <div className="relative">
                        <div className="w-16 h-16 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
                        <div className="absolute top-0 left-0 w-16 h-16 flex items-center justify-center">
                            <div className="w-2 h-2 bg-indigo-600 rounded-full"></div>
                        </div>
                    </div>
                    <div className="text-center space-y-2">
                        <h3 className="text-xl font-semibold text-gray-800">Generating Insights</h3>
                        <p className="text-gray-500">Planning &rarr; Coding &rarr; Researching &rarr; Writing</p>
                    </div>
                 </div>
            )}

            {data && !loading && (
                <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
                    {activeTab === 'ingestion' && <IngestionView data={data.ingestion} />}
                    {activeTab === 'pandas' && <PandasAgentView data={data.pandas_agent} />}
                    {activeTab === 'rag' && <RAGAgentView data={data.rag_agent} />}
                    {activeTab === 'synthesis' && <SynthesisView data={data.synthesis} />}
                </div>
            )}
        </div>

      </div>
    </div>
  );
};

export default App;