# server.py
import os
import base64
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import your existing modules
from ImportConfig import DataIngestion, AppConfig
from DualAgentProcess import PandasAgent, RAGAgent
from InsightSynthesisEngine import InsightSynthesizer

app = FastAPI()

# Allow React to communicate with this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def encode_image_to_base64(image_path):
    """Helper to send plot images to the frontend"""
    if not image_path or not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

@app.post("/generate-report")
async def generate_report():
    """
    Executes the logic from main.py but captures output 
    to return to the React frontend.
    """
    response_data = {
        "ingestion": {},
        "pandas_agent": {},
        "rag_agent": {},
        "synthesis": {}
    }

    # --- STEP 1: Ingestion ---
    try:
        ingestion = DataIngestion(AppConfig.DATA_PATH)
        df = ingestion.load_data()
        
        response_data["ingestion"] = {
            "status": "Success",
            "columns": list(df.columns),
            "row_count": len(df),
            "preview": df.head(5).to_dict(orient="records") # Send top 5 rows for preview
        }
    except Exception as e:
        return {"error": f"Ingestion Failed: {str(e)}"}

    # Initialize Agents
    pandas_agent = PandasAgent(df)
    rag_agent = RAGAgent(df)
    synthesizer = InsightSynthesizer()

    # --- STEP 2: Pandas Agent (Quantitative) ---
    # Using the logic from your main.py
    section_title = "Regional Performance Drivers"
    pandas_query = "Calculate total sales volume by Region. Sort descending. Identify the top performing region."
    
    p_result = pandas_agent.execute_task(pandas_query)
    
    # Process image if it exists
    plot_base64 = None
    if p_result.get('image'):
        plot_base64 = encode_image_to_base64(p_result['image'])

    response_data["pandas_agent"] = {
        "query": pandas_query,
        "code": p_result.get('code_executed', 'No code'),
        "insight": p_result.get('insight', ''),
        "image": plot_base64
    }

    # --- STEP 3: RAG Agent (Qualitative) ---
    rag_query = "What specific features or regulations make BMW models popular or unique in Europe?"
    r_result = rag_agent.execute_task(rag_query)
    
    response_data["rag_agent"] = {
        "query": rag_query,
        "insight": r_result.get('insight', ''),
        "context": r_result.get('context_used', '')
    }

    # --- STEP 4: Synthesis ---
    # We modify the synthesis call slightly to return the string directly 
    # rather than just writing to file, or we read the file back.
    final_narrative = synthesizer.generate_section_narrative(
        section_title=section_title,
        pandas_output=p_result,
        rag_output=r_result
    )
    
    response_data["synthesis"] = {
        "markdown_content": final_narrative
    }

    return response_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)