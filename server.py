import matplotlib
matplotlib.use('Agg')  # Must be the very first line
import uvicorn
import os
import json
import base64
import asyncio
import shutil
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI
from ImportConfig import DataIngestion, AppConfig
from DualAgentProcess import PandasAgent, RAGAgent
from InsightSynthesisEngine import InsightSynthesizer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Startup Cleanup ---
@app.on_event("startup")
async def startup_event():
    """Cleans the artifacts directory on server startup to remove old plots."""
    folder = AppConfig.OUTPUT_DIR
    if os.path.exists(folder):
        print(f"[Server] Cleaning up old artifacts in '{folder}'...")
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        os.makedirs(folder, exist_ok=True)
    print("[Server] Artifacts folder is ready.")

class ReportRequest(BaseModel):
    user_instructions: str = None

# --- Planning Agent (Async) ---
class PlanningAgent:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate_plan(self, user_input, columns_info, sample_data):
        prompt = f"""
        You are a Technical Project Manager.
        
        USER REQUEST: "{user_input}"
        
        DATASET SCHEMA:
        Columns: {columns_info}
        
        SAMPLE DATA:
        {sample_data}
        
        TASK: 
        Break the user request into specific execution steps.
        
        RULES:
        1. If the step requires calculating numbers/stats from data, set "type" to "high_level".
           - The "query" must be a NATURAL LANGUAGE description using EXACT column names.
           - *** DO NOT WRITE PYTHON CODE. ***
        2. If the step requires qualitative context, specs, or reasons (not in the excel), set "type" to "detailed".
           - The "query" must be a research question.
        3. MANDATORY: Regardless of the specific user request, you MUST ensure the plan includes steps to analyze:
           - Sales trends over time (e.g., Year-over-Year growth).
           - Top-performing and underperforming models or regions.
           - Key drivers of sales (e.g., Impact of Price on Volume, or breakdown by Model Type).
        
        OUTPUT FORMAT (JSON List):
        [
            {{
                "section": "Section Title",
                "type": "high_level", 
                "query": "Filter by Year 2023 and sum Sales_Volume..."
            }},
            {{
                "section": "Section Title",
                "type": "detailed",
                "query": "What key features driven sales in..."
            }}
        ]
        """
        
        response = await self.client.chat.completions.create(
            model="gpt-4o", # Updated to a valid model name
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        if isinstance(parsed, dict):
            for key in ["steps", "instructions", "plan"]:
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
            return [parsed]
            
        return parsed

def encode_image_to_base64(image_path):
    if not image_path or not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# --- Main Endpoint ---
@app.post("/generate-report")
async def generate_report(request: ReportRequest):
    
    response_data = {
        "pandas_agent": [], 
        "rag_agent": [],
        "synthesis": {},
        "ingestion": {}
    }

    # 1. Ingestion
    try:
        ingestion = DataIngestion(AppConfig.DATA_PATH)
        df = ingestion.load_data()
        
        columns_list = ", ".join(df.columns.tolist()) 
        sample_rows = df.head(5).to_markdown(index=False)
        
        response_data["ingestion"] = {
            "status": "Success",
            "row_count": len(df),
            "columns": list(df.columns),
            "preview": df.head(5).to_dict(orient="records")
        }
    except Exception as e:
        return {"error": str(e)}

    # 2. Planning
    if request.user_instructions:
        print(f"Generating plan for: {request.user_instructions}")
        planner = PlanningAgent()
        instructions = await planner.generate_plan(request.user_instructions, columns_list, sample_rows)
    else:
        # Default plan updated to meet requirements if no user input is provided
        instructions = [
            {
                "section": "Global Sales Trends",
                "type": "high_level",
                "query": "Group data by Year and calculate total Sales_Volume to show the trend over time."
            },
            {
                "section": "Performance by Region",
                "type": "high_level",
                "query": "Calculate total Sales_Volume by Region. Sort descending to identify top and bottom performers."
            },
            {
                "section": "Price & Segment Drivers",
                "type": "high_level",
                "query": "Analyze average Price_USD by Model to see which segments drive the most value."
            },
            {
                "section": "Regulatory Context",
                "type": "detailed",
                "query": "What key market drivers or regulations might impact sales trends for these models?"
            }
        ]

    # Initialize Agents
    pandas_agent = PandasAgent(df)
    rag_agent = RAGAgent(df)
    synthesizer = InsightSynthesizer()

    # --- 3. Async Execution Loop ---
    
    async def process_instruction(step):
        if step['type'] == 'high_level':
            result = await pandas_agent.execute_task(step['query'])
            return {"type": "pandas", "step": step, "result": result}
            
        elif step['type'] == 'detailed':
            result = await rag_agent.execute_task(step['query'])
            return {"type": "rag", "step": step, "result": result}
        return None

    print(f"Starting parallel execution of {len(instructions)} steps...")
    
    tasks = [process_instruction(step) for step in instructions]
    results = await asyncio.gather(*tasks)

    print(f"[Server Log] Parallel execution finished. Collected {len(results)} results.")
    
    # --- 4. Collect Results ---
    
    grouped_sections = {} 

    for res in results:
        if not res: continue

        step = res['step']
        output = res['result']
        section_title = step.get('section', 'General Analysis')

        # Initialize group
        if section_title not in grouped_sections:
            grouped_sections[section_title] = {'pandas': None, 'rag': None}

        if res['type'] == 'pandas':
            grouped_sections[section_title]['pandas'] = output
            
            plot_base64 = None
            if output.get('image'):
                plot_base64 = encode_image_to_base64(output['image'])
            
            response_data["pandas_agent"].append({
                "section": section_title,
                "query": step['query'],
                "code": output.get('code_executed', 'No code'),
                "insight": output.get('insight', ''),
                "image": plot_base64
            })
            
        elif res['type'] == 'rag':
            grouped_sections[section_title]['rag'] = output
            
            response_data["rag_agent"].append({
                "section": section_title,
                "query": step['query'],
                "insight": output.get('insight', ''),
                "context": output.get('context_used', '')
            })

    print("Synthesizing full report...")
    final_markdown = await synthesizer.generate_full_report(grouped_sections)
    
    saved_path = synthesizer.compile_final_report(final_markdown)
    print(f"Report saved locally at: {saved_path}")

    response_data["synthesis"] = {
        "markdown_content": final_markdown,
        "saved_path": saved_path
    }

    return response_data

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)