import matplotlib
matplotlib.use('Agg')  # Must be the very first line

import os
import json
import base64
import asyncio
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI

# Import your existing modules
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
            model="gpt-5.1", 
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
        "pandas_agent": {}, 
        "rag_agent": {}, 
        "synthesis": {}
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
        instructions = [
            {
                "section": "Regional Performance",
                "type": "high_level",
                "query": "Calculate total Sales_Volume by Region. Sort descending."
            },
            {
                "section": "Regional Context",
                "type": "detailed",
                "query": "What regulations impact sales in the top region?"
            }
        ]

    # Initialize Agents
    pandas_agent = PandasAgent(df)
    rag_agent = RAGAgent(df)
    synthesizer = InsightSynthesizer()

    # --- 3. Async Execution Loop ---
    
    async def process_instruction(step):
        # We can now await the agents directly
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

    # <--- Print statement added as requested --->
    print(f"[Server Log] Parallel execution finished. Collected {len(results)} results.")
    
    # --- 4. Process Results & Synthesis ---
    section_title = "Analysis Report"
    pandas_result = None
    rag_result = None

    for res in results:
        if not res: continue

        step = res['step']
        output = res['result']
        
        if step.get('section'):
            section_title = step.get('section')

        if res['type'] == 'pandas':
            pandas_result = output 
            plot_base64 = None
            if output.get('image'):
                plot_base64 = encode_image_to_base64(output['image'])
            
            response_data["pandas_agent"] = {
                "query": step['query'],
                "code": output.get('code_executed', 'No code'),
                "insight": output.get('insight', ''),
                "image": plot_base64
            }
            
        elif res['type'] == 'rag':
            rag_result = output
            response_data["rag_agent"] = {
                "query": step['query'],
                "insight": output.get('insight', ''),
                "context": output.get('context_used', '')
            }

    # Generate Final Narrative Async
    final_narrative = await synthesizer.generate_section_narrative(
        section_title=section_title,
        pandas_output=pandas_result,
        rag_output=rag_result
    )
    
    response_data["synthesis"] = {
        "markdown_content": final_narrative
    }

    return response_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)