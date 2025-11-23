import pandas as pd
import chromadb
import asyncio
import uuid
from chromadb.utils import embedding_functions
from openai import AsyncOpenAI
import os
import matplotlib.pyplot as plt
import seaborn as sns

# --- Agent 1: Pandas Agent (High-Level Aggregation) ---
class PandasAgent:
    def __init__(self, df):
        self.df = df
        self.output_dir = "artifacts"
        os.makedirs(self.output_dir, exist_ok=True)
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def execute_task(self, query):
        """Generates code asynchronously and executes it in a thread."""
        
        unique_id = uuid.uuid4().hex[:8]
        plot_filename = f"plot_{unique_id}.png"
        
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
        3. Create a matplotlib/seaborn plot if the result is a table or list of numbers.
        4. If a plot is needed, save it to '{self.output_dir}/{plot_filename}' and store path in `image_path`.
        5. Return ONLY the python code inside markdown blocks.
        """

        # 2. Call OpenAI (Non-blocking)
        response = await self.client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "system", "content": prompt}]
        )
        raw_code = response.choices[0].message.content
        cleaned_code = self._extract_code(raw_code)

        # 3. Execute Code in a separate thread (CPU-bound)
        return await asyncio.to_thread(self._run_code_sandbox, cleaned_code)

    def _run_code_sandbox(self, code):
        """Helper function to run exec() in a thread."""
        local_scope = {"df": self.df, "plt": plt, "sns": sns, "pd": pd}
        try:
            exec(code, {}, local_scope)
            return {
                "agent": "Pandas",
                "status": "success",
                "insight": local_scope.get("final_answer", "Calculation complete."),
                "image": local_scope.get("image_path", None),
                "code_executed": code
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
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # ChromaDB Client (Local)
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        # Standard embedding function for ingestion (Sync)
        self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )
        
        self.collection = self.chroma_client.get_or_create_collection(
            name="sales_details",
            embedding_function=self.embedding_fn
        )
        
        # Ingestion check
        if self.collection.count() == 0:
            print(f"Collection is empty. Starting ingestion of {len(df)} rows...")
            self._ingest_data()
        else:
            print(f"Loaded {self.collection.count()} existing documents from disk.")

    def _ingest_data(self):
        """Ingest data (Synchronous - happens rarely)."""
        documents = []
        ids = []
        
        print("Preparing documents...")
        for idx, row in self.df.iterrows():
            doc = f"Vehicle: {row.get('Model')} ({row.get('Year')}). Region: {row.get('Region')}. Specs: {row.get('Transmission')}, {row.get('Fuel_Type')}. Price: ${row.get('Price_USD')}."
            documents.append(doc)
            ids.append(str(idx))
            
        BATCH_SIZE = 500
        total_docs = len(documents)
        
        print(f"Ingesting {total_docs} documents...")
        for i in range(0, total_docs, BATCH_SIZE):
            end_index = min(i + BATCH_SIZE, total_docs)
            self.collection.add(documents=documents[i:end_index], ids=ids[i:end_index])
            
        print("Ingestion complete.")

    async def execute_task(self, query):
        """Retrieves records and generates answer asynchronously."""
        
        # 1. Generate Embedding Async (Prevents blocking during search)
        emb_response = await self.client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        query_embedding = emb_response.data[0].embedding
        
        # 2. Query Chroma with the embedding (Fast local read)
        results = self.collection.query(
            query_embeddings=[query_embedding], 
            n_results=5
        )
        
        if not results['documents'] or not results['documents'][0]:
            return {"agent": "RAG", "status": "error", "insight": "No relevant data found."}

        retrieved_context = "\n".join(results['documents'][0])

        # 3. Synthesize Answer Async
        response = await self.client.chat.completions.create(
            model="gpt-5.1",
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