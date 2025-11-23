import os
import pandas as pd
import logging

# --- Configuration ---
class AppConfig:
    # In production, load these from .env files
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DATA_PATH = "data\BMW sales data (2020-2024).xlsx"
    OUTPUT_DIR = "artifacts"
    
    # Instructions extracted from the user requirements
    REPORT_INSTRUCTIONS = [
        {
            "section": "Sales Trends",
            "type": "high_level",
            "query": "Group sales by Year and Month to show the trend over time. Calculate Year-over-Year growth."
        },
        {
            "section": "Regional Performance",
            "type": "high_level",
            "query": "Which region has the highest total sales volume? Compare the top 2 regions."
        },
        {
            "section": "Model Features",
            "type": "detailed",
            "query": "What are the specific key features or specs of the M5 in Europe versus other regions?"
        }
    ]
    
    DEFAULT_REPORT_INSTRUCTIONS = [
        {
            "section": "Regional Performance Drivers",
            "pandas_query": "Calculate total sales volume by Region. Sort descending. Identify the top performing region.",
            "rag_query": "What specific features or regulations make BMW models popular or unique in Europe?"
        }
    ]

# --- Data Ingestion Layer ---
class DataIngestion:
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None

    def load_data(self):
        """Loads and validates the dataset."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Data file not found at: {self.file_path}")

        print(f"Loading data from {self.file_path}...")
        # Handle CSV or Excel based on extension
        if self.file_path.endswith('.csv'):
            self.df = pd.read_csv(self.file_path)
        else:
            self.df = pd.read_excel(self.file_path)

        # Basic cleaning
        self._clean_data()
        return self.df

    def _clean_data(self):
        # Ensure numeric columns are actually numeric
        numeric_cols = ['Price_USD', 'Sales_Volume', 'Year', 'Engine_Size_L','Mileage_KM']
        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        # Drop rows with critical missing values
        self.df.dropna(subset=['Price_USD', 'Sales_Volume'], inplace=True)
        print(f"Data loaded successfully. Shape: {self.df.shape}")

    def get_schema(self):
        """Returns a string representation of the dataframe structure for the LLM."""
        buffer = []
        buffer.append(f"Columns: {', '.join(self.df.columns)}")
        buffer.append("Sample Data:")
        buffer.append(self.df.head(3).to_string())
        return "\n".join(buffer)

if __name__ == "__main__":
    # Test run
    ingest = DataIngestion(AppConfig.DATA_PATH)
    df = ingest.load_data()
    print(ingest.get_schema())