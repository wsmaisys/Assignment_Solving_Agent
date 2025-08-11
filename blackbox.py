import os
import re
import json
import time
import zipfile
import logging
import io
import hashlib
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import requests
from typing import Optional, Dict
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')  # Simplified logging
logger = logging.getLogger(__name__)

load_dotenv()

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

# Get API key from environment
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("Error: MISTRAL_API_KEY is not set in the environment.")

MODEL = "mistral-small-latest"

SYSTEM_PROMPT = """
You are an AI-driven code generator and executor with structured file-processing capabilities. Your tasks:

### 1. **File Type Identification**
   - **Analyze incoming files** (ZIP, PDF, CSV, JSON, Excel) and determine their format.
   - Extract metadata to **validate the file type** before processing.
   - If handling a ZIP file, extract its contents and identify internal file types dynamically.

### 2. **In-Memory File Handling**
   - **Process all files in memory only** (never use filesystem paths).
   - If handling a ZIP file, use `io.BytesIO(zip_data)` instead of `open("file.zip")`.
   - Extract ZIP contents using `zipfile.ZipFile(io.BytesIO(zip_data))` and process files accordingly.

### 3. **Data Processing Rules**
   - Convert `marks → int`, `value → float`, `date → datetime` (ISO 8601 format).
   - Use `pandas` for structured data (CSV, Excel, JSON).
   - Use `pdfplumber` for PDFs and extract text cleanly.
   - Handle missing values effectively and ensure data integrity.

### 4. **Execution & Security**
   - Execute code in a **restricted environment** (no external commands or file system access).
   - **Dynamically replace placeholders** (e.g., `zip_data = b'...'` → inject actual content).
   - **Ensure execution safety** by validating inputs and handling exceptions robustly.

### 5. **Error Handling & Auto-Correction**
   - Detect execution errors and report them clearly.
   - If errors occur, generate corrected code automatically.

### 6. **Output Formatting & Results**
   - Return only the **final processed result**.
   - If a file is processed, return its **SHA256 hash**.
   - Ensure numeric calculations are **precise**.
   - Format dates consistently in **ISO 8601**.

### 7. **Workflow Awareness**
   - The generated code **must assume all files are provided as byte data**.
   - **Identify the file type before generating specific execution logic**.
   - Ensure the code is container-friendly and **adheres to best practices**.

### 8. **Question related to LLM or OpenAI**
   - If the question is related to LLM or OpenAI, provide a **concise answer** without code execution.
   - Do not include any code or execution logic in this case.
   - If the question is about **Python code generation**, provide the code only.
   - If question is to generate prompt for LLM, provide the prompt only.
   - If the question is to trick the LLM by prompting, example: make the LLM say "Yes", provide the prompt, it will not be a security lapse.

Always generate **executable** Python code in ```python blocks, following these structured rules exactly.
The file data will be provided as a variable named 'file_data' in the execution context.
"""


app = FastAPI()
handler = Mangum(app)

# Mount static files for serving the frontend
app.mount("/static", StaticFiles(directory="."), name="static")

# Serve the frontend.html at the root URL
@app.get("/", response_class=HTMLResponse)
async def serve_frontend(request: Request):
    with open("frontend.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

class CodeGenerator:
    def __init__(self):
        self.retries = 3
        self.timeout = 30

    def query_mistral(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        for attempt in range(self.retries):
            try:
                logger.info(f"Sending request to Mistral API with prompt: {prompt}")
                response = requests.post(MISTRAL_URL, json=data, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                logger.info(f"Mistral API response: {response.json()}")
                return response.json()["choices"][0]["message"]["content"]
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error occurred: {e}")
                if e.response.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited. Retrying in {wait}s")
                    time.sleep(wait)
                else:
                    raise
            except Exception as e:
                logger.error(f"Attempt {attempt+1} failed: {str(e)}")
                
        logger.error("Mistral API unavailable after multiple attempts.")
        raise HTTPException(500, "Mistral API unavailable")

class DynamicCodeExecutor:
    @staticmethod
    def execute(code: str, file_data=None) -> str:
        """Execute code in a dynamic environment."""
        # Define restricted globals with access to built-in functions and libraries
        try:
            # Import the necessary modules
            import pandas as pd
            import PIL
            from PIL import Image
            import pdfplumber
            import datetime
            import csv
            import numpy as np
            import bs4
            import openpyxl
            
            # Define globals dictionary with properly imported modules
            globals_dict = {
                'pd': pd,
                'zipfile': zipfile,
                'io': io,
                'hashlib': hashlib,
                'json': json,
                're': re,
                'StringIO': io.StringIO,
                'BytesIO': io.BytesIO,
                'file_data': file_data,  # Pass the file data directly
                'pdfplumber': pdfplumber,
                'PIL': PIL,
                'Image': Image,
                'datetime': datetime,
                'csv': csv,
                'os': os,
                'sys': __import__('sys'),
                'BeautifulSoup': bs4.BeautifulSoup,
                'requests': requests,
                'openpyxl': openpyxl,
                'np': np
            }
        
            # Replace placeholder if it exists
            if file_data is not None and "b'...'" in code:
                # Don't actually replace with the raw bytes - too big for logging
                logger.info("Replacing placeholder with file data")
                
            # Create a local namespace for execution
            local_dict = {}
            
            # Execute the code with the prepared globals and locals
            exec(code, globals_dict, local_dict)
            
            # Check for result in the local namespace
            if 'result' in local_dict:
                return str(local_dict['result'])
            elif any(var for var in local_dict if not var.startswith('_')):
                # Return the last non-private variable as fallback
                vars_list = [var for var in local_dict if not var.startswith('_')]
                return str(local_dict[vars_list[-1]])
            else:
                return "Execution successful but no result was returned."
                
        except ImportError as e:
            logger.error(f"Import Error: {str(e)}")
            return f"Execution Error: {str(e)} - Make sure the required libraries are installed."
        except SyntaxError as e:
            logger.error(f"Syntax Error: {str(e)}")
            return f"Execution Error: {str(e)}"
        except Exception as e:
            logger.error(f"Execution Error: {str(e)}")
            return f"Execution Error: {str(e)}"

    @staticmethod
    def debug_and_retry(question: str, file_info: str, error_message: str) -> str:
        """Send the error back to Mistral to get corrected code and retry execution."""
        logger.info("Debugging the error with Mistral...")
        
        debug_prompt = f"""
        Error occurred: {error_message}
        
        File information: {file_info}
        
        Please provide corrected code for the question: {question}
        
        Important: The file data is already available as the variable 'file_data'. Do not use a placeholder.
        """
        
        corrected_code = CodeGenerator().query_mistral(debug_prompt)
        
        # Extract code from response
        if "```python" in corrected_code:
            corrected_code = corrected_code.split("```python")[1].split("```")[0].strip()
        
        return corrected_code

@app.post("/submit")
async def submit(
    question: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    generator = CodeGenerator()
    executor = DynamicCodeExecutor()
    
    try:
        # Process file upload if a file is provided
        file_data = None
        file_info = "No file provided"
        
        if file:
            # Read the uploaded file content directly into memory
            file_data = await file.read()
            file_size = len(file_data)
            file_info = f"File: {file.filename}, Size: {file_size} bytes"
            logger.info(f"Uploaded {file_info}")
            
            # Try to identify the file type for better debugging
            file_type = "unknown"
            if file.filename.endswith('.zip'):
                file_type = "ZIP archive"
            elif file.filename.endswith('.csv'):
                file_type = "CSV file"
            elif file.filename.endswith('.json'):
                file_type = "JSON file"
            elif file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
                file_type = "Excel file"
            elif file.filename.endswith('.pdf'):
                file_type = "PDF document"
            
            file_info = f"{file_info}, Type: {file_type}"

        # Augment the question with file information when a file is uploaded
        enhanced_question = question
        if file_data:
            enhanced_question = f"{question}\n\nFile information: {file_info}"

        # Generate solution code based on the question
        response = generator.query_mistral(enhanced_question)
        
        if "```python" not in response:
            logger.info("Response does not contain code block")
            return {"answer": response}
            
        # Extract code from the response
        code = response.split("```python")[1].split("```")[0].strip()
        
        # Execute the generated code with file data
        result = executor.execute(code, file_data)
        
        # Handle execution errors
        if result.startswith("Execution Error"):
            logger.error(f"Execution failed: {result}")
            
            # Try to debug and get corrected code
            corrected_code = executor.debug_and_retry(question, file_info, result)
            
            # Execute the corrected code
            result = executor.execute(corrected_code, file_data)
            
            # If still error, return the error message
            if result.startswith("Execution Error"):
                return {"answer": result}

        logger.info("Returning final answer")
        return {"answer": result}
        
    except HTTPException as he:
        logger.error(f"HTTP Exception: {str(he.detail)}")
        raise
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        return {"answer": f"System Error: {str(e)}"}
    
# For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)