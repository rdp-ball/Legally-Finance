import os
import streamlit as st
import PyPDF2
import matplotlib.pyplot as plt
from io import BytesIO
from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.llms.gemini import Gemini
import re

# Configure Google Gemini
Settings.embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.llm = Gemini(api_key=os.getenv("GOOGLE_API_KEY"), temperature=0.5, model_name="models/gemini-pro")

def write_to_file(content, filename="./files/uploaded.pdf"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "wb") as f:
        f.write(content)

def extract_financial_data(document_text):
    """
    Extracts financial data from the text of the document.
    """
    financial_data = {
        "Revenue": [],
        "Date": []
    }

    lines = document_text.split("\n")
    revenue_pattern = re.compile(r'\$?\d+(?:,\d{3})*(?:\.\d+)?')
    
    for i, line in enumerate(lines):
        # Check for revenue-related keywords
        if any(keyword in line.lower() for keyword in ["revenue", "total revenue", "sales"]):
            # Attempt to extract numbers from the following lines
            for j in range(i+1, i+6):  # Look ahead a few lines for potential numbers
                matches = revenue_pattern.findall(lines[j])
                if matches:
                    for match in matches:
                        try:
                            value = float(match.replace("$", "").replace(",", ""))
                            financial_data["Revenue"].append(value)
                        except ValueError:
                            continue
                        
        # Check for date-related lines
        if "Q1" in line or "Q2" in line or "Q3" in line or "Q4" in line or re.search(r'FY\s*\d{4}', line):
            financial_data["Date"].append(line.strip())

    # Ensure the data lists are of equal length
    min_length = min(len(financial_data["Revenue"]), len(financial_data["Date"]))
    financial_data["Revenue"] = financial_data["Revenue"][:min_length]
    financial_data["Date"] = financial_data["Date"][:min_length]

    return financial_data

def ingest_documents():
    reader = SimpleDirectoryReader("./files/")
    documents = reader.load_data()
    return documents

def load_data(documents):
    index = VectorStoreIndex.from_documents(documents)
    return index

def generate_summary(index, document_text, query):
    query_engine = index.as_query_engine()
    response = query_engine.query(f"""
    You are a financial analyst. Your task is to provide a comprehensive analysis of the financial document.
    Analyze the following document and respond to the query:
    {document_text}
    
    Query: {query}
    if the query is too general respond by this
    Please cover the following aspects:
    1. Revenue and profit trends
    2. Key financial metrics
    3. Major financial events and decisions
    4. Comparison with previous periods
    5. Future outlook or forecasts
    6. Any notable financial risks or opportunities
    Provide a clear, concise, and professional response.
    """)
    return response.response

def generate_comparison_graph(data):
    if not data["Date"] or not data["Revenue"]:
        st.write("Insufficient data for generating the revenue comparison graph.")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(data["Date"], data["Revenue"], marker="o", linestyle="-", color="b", label="Revenue")
    ax.set_title("Revenue Comparison")
    ax.set_xlabel("Date")
    ax.set_ylabel("Revenue (in millions)")
    ax.grid(True)
    ax.legend()
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    st.pyplot(fig)

# Streamlit app
def main():
    st.title("Fortune 500 Financial Document Analyzer")
    st.write("Upload a financial document, ask questions, and get detailed analysis!")

    uploaded_file = st.file_uploader("Choose a financial document file", type=["pdf"])

    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.getvalue()))
            document_text = ""
            for page in pdf_reader.pages:
                document_text += page.extract_text()
        else:
            document_text = uploaded_file.getvalue().decode("utf-8")

        write_to_file(uploaded_file.getvalue())

        st.write("Analyzing financial document...")

        # Extract financial data
        financial_data = extract_financial_data(document_text)

        # Ingest documents for summarization and query-driven analysis
        documents = ingest_documents()
        index = load_data(documents)

        # Add a provision for user query input
        query = st.text_input("Enter your financial analysis query (e.g., 'What are the revenue trends?')", "")

        if query:
            summary = generate_summary(index, document_text, query)
            st.write("## Financial Analysis Result")
            st.write(summary)

        # Display revenue comparison graph
        if financial_data["Revenue"] and financial_data["Date"]:
            st.write("## Revenue Comparison")
            generate_comparison_graph(financial_data)
        else:
            st.write("No revenue data found for comparison.")

if __name__ == "__main__":
    main()
