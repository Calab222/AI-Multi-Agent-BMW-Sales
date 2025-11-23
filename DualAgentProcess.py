import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
import os
import matplotlib.pyplot as plt
import seaborn as sns

# Initialize OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Agent 1: Pandas Agent (High-Level Aggregation) ---
class PandasAgent:
    def __init__(self, df):
        self.df = df
        self.output_dir = "artifacts"
        os.makedirs(self.output_dir, exist_ok=True)

    def execute_task(self, query):
        """Generates and executes Python code to solve a quantitative query."""
        
        # 1. Construct System Prompt
        schema_info = self.df.dtypes.to_string()
        prompt = f"""
        You are a Python Data Analyst. You have a pandas DataFrame named `df`.
        
        Schema:
        {schema_info}

        Task: {query}

        Requirements:
        1. Write python code to solve the task.
        2. Store the text summary in a variable called `final_answer`.
        3. If a plot is needed, save it to '{self.output_dir}/plot.png' and store path in `image_path`.
        4. Return ONLY the python code inside markdown blocks.
        """

        # 2. Call OpenAI to write code
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "system", "content": prompt}]
        )
        raw_code = response.choices[0].message.content
        cleaned_code = self._extract_code(raw_code)

        # 3. Execute Code in Sandbox
        local_scope = {"df": self.df, "plt": plt, "sns": sns, "pd": pd}
        
        try:
            exec(cleaned_code, {}, local_scope)
            return {
                "agent": "Pandas",
                "status": "success",
                "insight": local_scope.get("final_answer", "Calculation complete."),
                "image": local_scope.get("image_path", None),
                "code_executed": cleaned_code
            }
        except Exception as e:
            return {"agent": "Pandas", "status": "error", "error": str(e)}

    def _extract_code(self, text):
        if "```python" in text:
            return text.split("```python")[1].split("```")[0].strip()
        return text.strip()


# --- Agent 2: RAG Agent (Detailed Context) ---   
class RAGAgent:
    def __init__(self, df):
        self.df = df
        
        # --- CHANGE 1: Use PersistentClient to save data to disk ---
        self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Use OpenAI Embeddings
        self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )
        
        # --- CHANGE 2: Get existing collection or create new one ---
        self.collection = self.client.get_or_create_collection(
            name="sales_details",
            embedding_function=self.embedding_fn
        )
        
        # --- CHANGE 3: Only process data if DB is empty (skip on 2nd run) ---
        if self.collection.count() == 0:
            print(f"Collection is empty. Starting ingestion of {len(df)} rows...")
            self._ingest_data()
        else:
            print(f"Loaded {self.collection.count()} existing documents from disk. Skipping ingestion.")

    def _ingest_data(self):
        """Converts ALL rows to semantic text and stores in Vector DB using batches."""
        documents = []
        ids = []
        
        # 1. Prepare all data
        print("Preparing documents (this may take a moment)...")
        for idx, row in self.df.iterrows():
            doc = f"Vehicle: {row.get('Model')} ({row.get('Year')}). Region: {row.get('Region')}. Specs: {row.get('Transmission')}, {row.get('Fuel_Type')}. Price: ${row.get('Price_USD')}."
            documents.append(doc)
            ids.append(str(idx))
            
        # 2. Send to ChromaDB/OpenAI in batches to avoid token limits
        BATCH_SIZE = 500
        total_docs = len(documents)
        
        print(f"Ingesting {total_docs} documents in batches of {BATCH_SIZE}...")
        
        for i in range(0, total_docs, BATCH_SIZE):
            end_index = min(i + BATCH_SIZE, total_docs)
            
            # Slice the list
            batch_docs = documents[i : end_index]
            batch_ids = ids[i : end_index]
            
            # Add batch
            self.collection.add(documents=batch_docs, ids=batch_ids)
            print(f"  Processed batch {i} to {end_index}")
            
        print("Ingestion complete. Data saved to ./chroma_db")

    def execute_task(self, query):
        """Retrieves specific records and generates a qualitative answer."""
        
        # 1. Retrieve relevant rows
        results = self.collection.query(query_texts=[query], n_results=5)
        
        if not results['documents'][0]:
            return {"agent": "RAG", "status": "error", "insight": "No relevant data found."}

        retrieved_context = "\n".join(results['documents'][0])

        # 2. Synthesize Answer with OpenAI
        response = client.chat.completions.create(
            model="gpt-5.1", # Updated valid model
            messages=[
                {"role": "system", "content": "You are a detailed researcher. Use the provided context to answer the query."},
                {"role": "user", "content": f"Context:\n{retrieved_context}\n\nQuestion: {query}"}
            ]
        )

        return {
            "agent": "RAG",
            "status": "success",
            "insight": response.choices[0].message.content,
            "context_used": retrieved_context
        }

# --- EXECUTION FLOW ---
if __name__ == "__main__":
    # Import from the first file (assuming it is named config_ingestion.py)
    from ImportConfig import DataIngestion, AppConfig

    print("=== 1. Data Import & Configuration ===")
    # Use the DataIngestion class to handle loading and cleaning
    ingestion = DataIngestion(AppConfig.DATA_PATH)
    df = ingestion.load_data()

    # Generate schema for verification (optional, but good for logging)
    schema = ingestion.get_schema()
    print("Schema extracted successfully.")

    print("\n=== 2. Initializing Dual Agents ===")
    # Pass the processed dataframe to both agents
    pandas_agent = PandasAgent(df)
    rag_agent = RAGAgent(df)

    print("\n=== 3. Processing Report Instructions ===")
    # Iterate through the instructions defined in AppConfig
    for i, task in enumerate(AppConfig.REPORT_INSTRUCTIONS, 1):
        print(f"\n[Section {i}: {task['section']}]")
        print(f"Query: {task['query']}")
        
        if task['type'] == 'high_level':
            # Route to Pandas Agent
            print(f"Routing to: Pandas Agent")
            result = pandas_agent.execute_task(task['query'])
            
            if result['status'] == 'success':
                print(f"Result: {result['insight']}")
                if result.get('image'):
                    print(f"Chart generated at: {result['image']}")
            else:
                print(f"Error: {result.get('error')}")

        elif task['type'] == 'detailed':
            # Route to RAG Agent
            print(f"Routing to: RAG Agent")
            result = rag_agent.execute_task(task['query'])
            
            if result['status'] == 'success':
                print(f"Result: {result['insight']}")
            else:
                print(f"Error: {result.get('error')}")