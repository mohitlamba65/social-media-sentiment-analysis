import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize the Groq client
llm = ChatGroq(
    temperature=0, 
    groq_api_key=GROQ_API_KEY, 
    model_name="llama-3.3-70b-versatile"
)

def get_ollama_response(query: str, data_summary: str) -> str:
    """Chat with the data."""
    system_prompt = f"""
    You are a Data Analyst. Answer based ONLY on this summary:
    {data_summary}
    If the answer isn't there, say so. Keep answers concise.
    """
    
    messages = [
        ("system", system_prompt),
        ("human", query),
    ]
    
    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        return f"AI Error: {str(e)}"

def get_ai_insights(df, filename):
    """
    Generates automatic insights (the 'AI Insights' button).
    """
    # Create a mini-summary specifically for insights
    stats = {
        "rows": len(df),
        "cols": list(df.columns),
        "sentiment_counts": df['sentiment'].value_counts().to_dict() if 'sentiment' in df.columns else "No sentiment data",
    }
    
    prompt = f"""
    Analyze this dataset metadata for '{filename}': {json.dumps(stats)}
    
    Provide 3 brief, high-level business insights or observations in a numbered list. 
    Focus on sentiment balance and data volume.
    """
    
    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"Could not generate insights. Error: {str(e)}"