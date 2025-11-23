import os
import pandas as pd
from ImportConfig import DataIngestion, AppConfig
from DualAgentProcess import PandasAgent, RAGAgent
from InsightSynthesisEngine import InsightSynthesizer

def main():
    print("=== STEP 1: Ingestion & Setup ===")
    ingestion = DataIngestion(AppConfig.DATA_PATH)
    df = ingestion.load_data()
    
    # Initialize Agents
    pandas_agent = PandasAgent(df)
    rag_agent = RAGAgent(df)
    synthesizer = InsightSynthesizer()
    
    final_report_sections = []

    print("\n=== STEP 2: Multi-Agent Processing ===")
    
    # Define the workflow for a specific analysis section
    # Example: "Regional Performance Analysis"
    section_title = "Regional Performance Drivers"
    print(f"Processing Section: {section_title}...")
    
    # A. Run Pandas Agent (Get the Numbers)
    print(" -> Pandas Agent: Calculating Regional Volumes...")
    pandas_query = "Calculate total sales volume by Region. Sort descending. Identify the top performing region."
    pandas_result = pandas_agent.execute_task(pandas_query)
    
    # B. Run RAG Agent (Get the 'Why')
    # We dynamically formulate a RAG query based on the Pandas result (optional advanced step)
    # For now, we use a specific query about the top region (Europe)
    print(" -> RAG Agent: Researching Top Region Features...")
    rag_query = "What specific features or regulations make BMW models popular or unique in Europe?"
    rag_result = rag_agent.execute_task(rag_query)
    
    # C. Run Synthesis Engine (Merge them)
    print(" -> Synthesis Engine: Writing Narrative...")
    section_content = synthesizer.generate_section_narrative(
        section_title=section_title,
        pandas_output=pandas_result,
        rag_output=rag_result
    )
    
    final_report_sections.append(section_content)
    
    print("\n=== STEP 3: Report Generation ===")
    output_path = synthesizer.compile_final_report(final_report_sections)
    print(f"Report generated successfully at: {output_path}")

if __name__ == "__main__":
    main()