# 🤖 Automated LLM Report Generation & Insight Engine

## 📖 Overview

This project is an AI-powered analytics platform designed to automate business reporting from structured data. It utilizes a **Multi-Agent Architecture** to synthesize quantitative analysis (via Pandas) and qualitative insights (via RAG/Vector Search) into cohesive executive reports.

The system was built as a prototype to analyze BMW Global Sales Data (2020-2024), demonstrating how LLMs can orchestrate complex analytical tasks, generate visualizations, and produce narrative storytelling without human intervention.

---

## 🚀 Key Features

* **Dual-Agent Workflow:**
    * **Pandas Agent:** Executes Python code safely to calculate statistics, aggregate data, and generate Matplotlib/Seaborn visualizations.
    * **RAG Agent (Contextual):** Uses ChromaDB to perform semantic search on vehicle specifications and regional contexts to answer qualitative questions.
* **Insight Synthesis Engine:** Aggregates findings from both agents and uses GPT-4o/GPT-5 to write a professional Markdown report.
* **Self-Healing Data Pipeline:** Automatically detects if the vector database is missing and rebuilds it from the source dataset on the first run.
* **Interactive UI:** A React-based frontend to input natural language queries and view the generation process in real-time.

---

## 🛠️ Architecture

The solution follows a modern client-server architecture:

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Frontend** | React + Tailwind CSS | Visualization & User Input |
| **Backend** | FastAPI | Orchestration Layer |
| **LLM Integration** | OpenAI API | GPT Models |
| **Vector Storage** | ChromaDB | Local persistent storage |
| **Data Processing** | Pandas & Matplotlib | Data Analysis |

---

## 📦 Installation & Setup

### Prerequisites

* Python 3.9+
* Node.js & npm
* OpenAI API Key

### 1. Backend Setup

1.  Clone the repository.
2.  Navigate to the root directory.
3.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Set up your environment variables:
    * Create a `.env` file (or export in terminal) with your API key:
        ```bash
        export OPENAI_API_KEY="your-sk-key-here"
        ```

### 2. Frontend Setup

1.  Navigate to the frontend folder (or wherever your React app resides).
2.  Install dependencies:
    ```bash
    npm install
    ```

### 3. Running the Application

1.  Start the Backend API:
    ```bash
    python server.py
    ```
2.  Start the development server:
    ```bash
    npm run dev
    ```
3.  Open your browser to the URL provided by the frontend (usually `http://localhost:5173`).

> **Note on Initial Run:** On the very first run, the system will take a few moments to ingest the Excel data into ChromaDB. Subsequent runs will be instant.

---

## 📂 Project Structure
* artifacts/ – Generated plots and reports
* chroma_db/ – Vector database (auto-generated, gitignored)
* data/ – Source datasets (Excel/CSV)
* DualAgentProcess.py – Core logic for Pandas and RAG agents
* ImportConfig.py – Configuration and Data Ingestion
* InsightSynthesisEngine.py – Report writing logic
* main.py / server.py – FastAPI application entry points
* requirements.txt – Python dependencies
* README.md – Project documentation
