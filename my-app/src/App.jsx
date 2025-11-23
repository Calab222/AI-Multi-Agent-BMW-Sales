import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown'; // You might need: npm install react-markdown
import { BarChart, FileText, Database, PenTool, Play, Loader2 } from 'lucide-react';

const App = () => {
  const [activeTab, setActiveTab] = useState('ingestion');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/generate-report', {
        method: 'POST',
      });
      const result = await response.json();
      if (result.error) throw new Error(result.error);
      setData(result);
      setActiveTab('ingestion'); // Reset to first tab on new run
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // --- Tab Content Components ---

  const IngestionView = ({ data }) => (
    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
      <h3 className="font-bold text-lg mb-4 text-gray-800">Data Ingestion Status</h3>
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white p-4 rounded shadow-sm">
            <div className="text-sm text-gray-500">Total Rows</div>
            <div className="text-2xl font-bold">{data?.row_count || 0}</div>
        </div>
        <div className="bg-white p-4 rounded shadow-sm">
            <div className="text-sm text-gray-500">Status</div>
            <div className="text-2xl font-bold text-green-600">{data?.status || "Waiting"}</div>
        </div>
      </div>
      
      <h4 className="font-semibold mb-2">Data Preview (Head):</h4>
      <div className="overflow-x-auto bg-white rounded shadow-sm border">
        <table className="min-w-full text-sm text-left">
          <thead className="bg-gray-100">
            <tr>
              {data?.columns?.map(col => <th key={col} className="p-2 border-b">{col}</th>)}
            </tr>
          </thead>
          <tbody>
            {data?.preview?.map((row, i) => (
              <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                {data.columns.map(col => <td key={col} className="p-2">{row[col]}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const PandasAgentView = ({ data }) => (
    <div className="space-y-6">
      <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
        <h4 className="font-bold text-blue-800 mb-1">Agent Objective:</h4>
        <p className="text-blue-700">{data?.query}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Code Execution */}
        <div className="border rounded-lg overflow-hidden shadow-sm">
          <div className="bg-gray-800 text-white px-4 py-2 text-sm font-mono">Generated Python Code</div>
          <pre className="bg-gray-900 text-green-400 p-4 text-xs overflow-auto h-64">
            {data?.code}
          </pre>
        </div>

        {/* Right: Visual Output */}
        <div className="border rounded-lg p-4 shadow-sm flex flex-col items-center justify-center bg-white">
            <h5 className="text-sm font-semibold text-gray-500 mb-2">Generated Visualization</h5>
            {data?.image ? (
                <img 
                  src={`data:image/png;base64,${data.image}`} 
                  alt="Generated Plot" 
                  className="max-h-60 object-contain"
                />
            ) : (
                <div className="text-gray-400 italic">No visualization generated</div>
            )}
        </div>
      </div>

      <div className="bg-white p-4 border rounded-lg">
        <h4 className="font-bold mb-2">Quantitative Insight:</h4>
        <p className="text-gray-700">{data?.insight}</p>
      </div>
    </div>
  );

  const RAGAgentView = ({ data }) => (
    <div className="space-y-6">
      <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
        <h4 className="font-bold text-purple-800 mb-1">Research Question:</h4>
        <p className="text-purple-700">{data?.query}</p>
      </div>

      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <h4 className="font-bold mb-2 flex items-center gap-2">
            <Database size={16} /> Retrieved Context (Vector DB):
        </h4>
        <div className="bg-gray-50 p-3 rounded text-sm text-gray-600 border h-40 overflow-y-auto whitespace-pre-wrap">
            {data?.context}
        </div>
      </div>

      <div className="bg-green-50 border border-green-100 p-4 rounded-lg">
        <h4 className="font-bold text-green-800 mb-2">Qualitative Insight:</h4>
        <p className="text-green-700">{data?.insight}</p>
      </div>
    </div>
  );

  const SynthesisView = ({ data }) => (
    <div className="bg-white shadow-lg rounded-lg border p-8 max-w-4xl mx-auto min-h-[500px]">
        <div className="prose prose-slate lg:prose-xl mx-auto">
             {/* We strip the image markdown here to avoid broken links, 
                 as we handled images in the Pandas tab */}
             <ReactMarkdown>
                {data?.markdown_content?.replace(/!\[.*?\]\(.*?\)/g, "")}
             </ReactMarkdown>
        </div>
    </div>
  );

  // --- Main Layout ---

  return (
    <div className="min-h-screen bg-gray-100 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Multi-Agent Insight Engine</h1>
            <p className="text-gray-500">Orchestrating Pandas, ChromaDB, and GPT-4 for Automated Reporting</p>
          </div>
          
          <button 
            onClick={handleGenerate} 
            disabled={loading}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg text-white font-semibold shadow-md transition-all
                ${loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'}`}
          >
            {loading ? <Loader2 className="animate-spin" /> : <Play size={20} />}
            {loading ? "Running Agents..." : "Generate Live Report"}
          </button>
        </div>

        {error && (
             <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
                Error: {error}
             </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-200 pb-1">
            {[
                { id: 'ingestion', label: '1. Ingestion & Config', icon: FileText },
                { id: 'pandas', label: '2. Pandas Agent (Quant)', icon: BarChart },
                { id: 'rag', label: '3. RAG Agent (Qual)', icon: Database },
                { id: 'synthesis', label: '4. Final Report', icon: PenTool },
            ].map((tab) => (
                <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-t-lg font-medium transition-colors
                        ${activeTab === tab.id 
                            ? 'bg-white text-indigo-600 border border-b-0 border-gray-200 shadow-sm' 
                            : 'text-gray-500 hover:text-gray-700 hover:bg-gray-200'}`}
                >
                    <tab.icon size={16} />
                    {tab.label}
                </button>
            ))}
        </div>

        {/* Content Area */}
        <div className="bg-white rounded-b-lg rounded-tr-lg min-h-[400px] p-6 shadow-sm border border-t-0 border-gray-200">
            {!data && !loading && (
                <div className="text-center py-20 text-gray-400">
                    <div className="text-6xl mb-4">🤖</div>
                    <p>Click "Generate Live Report" to start the multi-agent workflow.</p>
                </div>
            )}

            {loading && (
                 <div className="flex flex-col items-center justify-center py-20 space-y-4">
                    <Loader2 className="animate-spin text-indigo-600" size={48} />
                    <p className="text-gray-500 animate-pulse">Agents are analyzing data...</p>
                 </div>
            )}

            {data && !loading && (
                <>
                    {activeTab === 'ingestion' && <IngestionView data={data.ingestion} />}
                    {activeTab === 'pandas' && <PandasAgentView data={data.pandas_agent} />}
                    {activeTab === 'rag' && <RAGAgentView data={data.rag_agent} />}
                    {activeTab === 'synthesis' && <SynthesisView data={data.synthesis} />}
                </>
            )}
        </div>

      </div>
    </div>
  );
};

export default App;