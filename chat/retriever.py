import pandas as pd
import io

def get_summary(df, filename, for_llm=False):
    """
    Generates a comprehensive summary of the DataFrame.
    
    Args:
        df (pd.DataFrame): The DataFrame to summarize.
        filename (str): The name of the file.
        for_llm (bool): If True, formats the summary as a text blob for an LLM.

    Returns:
        dict or str: A dictionary of summary stats, or a text blob if for_llm=True.
    """
    
    try:
        # Get column details (types, nulls)
        buffer = io.StringIO()
        df.info(buf=buffer)
        col_details = buffer.getvalue()
        
        # Get numerical summary
        numeric_df = df.select_dtypes(include=['number'])
        num_summary = "No numerical data."
        if not numeric_df.empty:
            num_summary = numeric_df.describe().to_string()
            
        # Get categorical summary
        cat_df = df.select_dtypes(include=['object', 'category'])
        cat_summary = "No categorical data."
        if not cat_df.empty:
            cat_summary = cat_df.describe().to_string()

        # Format for display (dict)
        if not for_llm:
            return {
                'Total Rows': df.shape[0],
                'Total Columns': df.shape[1],
                'File Name': filename.replace('data\\', '').replace('data/', ''),
                'Column Details': col_details,
                'Numerical Data Summary': num_summary,
                'Categorical Data Summary': cat_summary
            }
        
        # Format for LLM (text blob)
        else:
            llm_summary = f"""
            Here is a summary of the data from the file '{filename}':

            --- FILE INFO ---
            Total Rows: {df.shape[0]}
            Total Columns: {df.shape[1]}

            --- COLUMN DETAILS (Name, Type, Nulls) ---
            {col_details}

            --- NUMERICAL DATA SUMMARY ---
            {num_summary}

            --- CATEGORICAL DATA SUMMARY ---
            {cat_summary}
            """
            return llm_summary

    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Error generating data summary." if for_llm else {"Error": str(e)}