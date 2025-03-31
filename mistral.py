import os
import re
import json
import time
import uuid
import zipfile
import logging
import io
import hashlib
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import requests
from typing import Optional, Dict
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

# Get API key from environment
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("Error: MISTRAL_API_KEY is not set in the environment.")

MODEL = "mistral-small-latest"

SYSTEM_PROMPT = """
You are an autonomous problem solver. Follow these rules:

1. FILE PROCESSING:
- Handle ZIP/PDF/CSV/JSON/Excel in memory
- Use correct encodings: UTF-8, CP-1252, UTF-16
- For ZIP files: Process all files in memory

2. DATA ANALYSIS:
- Convert columns: marks→int, value→float, date→datetime
- Use pandas for tabular data, pdfplumber for PDFs
- Handle missing values appropriately

3. OUTPUT:
- Return ONLY the final answer
- For files: SHA256 hash
- Calculations: numeric only
- Dates: ISO 8601 format

4. SAFETY:
- Never execute external commands
- Validate all inputs
- Use memory-based operations only

Generate Python code in ```python blocks following these rules exactly.
"""

app = FastAPI()
handler = Mangum(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

class SecureFileProcessor:
    @staticmethod
    async def handle_upload(file: UploadFile) -> dict:
        """Process uploads in memory with size limits"""
        MAX_SIZE = 4_500_000  # Vercel's payload limit
        
        try:
            contents = await file.read()
            if len(contents) > MAX_SIZE:
                raise HTTPException(413, "File exceeds 4.5MB limit")
                
            if file.filename.endswith('.zip'):
                return SecureFileProcessor.process_zip(contents)
                
            return {
                "filename": file.filename,
                "content": contents,
                "extracted": None
            }
        except Exception as e:
            logging.error(f"Upload failed: {str(e)}")
            raise HTTPException(500, f"File processing error: {str(e)}")

    @staticmethod
    def process_zip(zip_data: bytes) -> dict:
        """Extract ZIP contents in memory"""
        file_lookup = {}
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                for file in z.namelist():
                    with z.open(file) as f:
                        file_lookup[file] = f.read()
            return {
                "filename": "archive.zip",
                "content": zip_data,
                "extracted": file_lookup
            }
        except zipfile.BadZipFile:
            raise HTTPException(400, "Invalid ZIP file")

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
            "temperature": 0.1
        }

        for attempt in range(self.retries):
            try:
                response = requests.post(MISTRAL_URL, json=data, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    wait = 2 ** attempt
                    logging.warning(f"Rate limited. Retrying in {wait}s")
                    time.sleep(wait)
                else:
                    raise
            except Exception as e:
                logging.error(f"Attempt {attempt+1} failed: {str(e)}")
                
        raise HTTPException(500, "Mistral API unavailable")

class SafeCodeExecutor:
    ALLOWED_MODULES = {'pandas', 'pdfplumber', 'zipfile', 'io', 'hashlib'}
    
    @staticmethod
    def validate_code(code: str) -> str:
        """Sanitize code for security"""
        # Remove dangerous constructs
        blacklist = ['__', 'eval', 'exec', 'system', 'subprocess', 'os.', 'shutil']
        for pattern in blacklist:
            if pattern in code:
                raise HTTPException(400, f"Disallowed code pattern: {pattern}")
                
        # Validate imports
        imports = re.findall(r'^\s*import\s+(\w+)', code, re.M)
        for imp in imports:
            if imp not in SafeCodeExecutor.ALLOWED_MODULES:
                raise HTTPException(400, f"Disallowed import: {imp}")
                
        return code

    @staticmethod
    def execute(code: str, context: dict) -> str:
        """Execute code in restricted environment"""
        restricted_globals = {
            '__builtins__': {
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'pd': None,
                'pdfplumber': None,
                'zipfile': None,
                'io': None,
                'hashlib': None
            }
        }
        
        try:
            # Add allowed modules
            if 'pandas' in code:
                import pandas as pd
                restricted_globals['pd'] = pd
            if 'pdfplumber' in code:
                import pdfplumber
                restricted_globals['pdfplumber'] = pdfplumber
                
            # Inject context variables
            restricted_globals.update(context)
            
            exec(code, restricted_globals)
            return str(restricted_globals.get('result', 'No result found'))
        except Exception as e:
            return f"Execution Error: {str(e)}"

@app.post("/submit")
async def submit(
    question: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    processor = SecureFileProcessor()
    generator = CodeGenerator()
    executor = SafeCodeExecutor()
    
    file_context = {}
    
    try:
        # Process file upload
        if file:
            file_info = await processor.handle_upload(file)
            if file_info['extracted']:
                file_context['extracted_files'] = file_info['extracted']
            else:
                file_context['file_content'] = file_info['content']
                
        # Generate solution code
        response = generator.query_mistral(question)
        
        if "```python" not in response:
            return {"answer": response.split('\n')[-1]}
            
        # Extract and sanitize code
        code = response.split("```python")[1].split("```")[0].strip()
        code = executor.validate_code(code)
        
        # Execute with context
        result = executor.execute(code, file_context)
        
        return {"answer": result.split('\n')[-1]}
        
    except HTTPException as he:
        raise
    except Exception as e:
        logging.error(f"Processing failed: {str(e)}")
        return {"answer": f"System Error: {str(e)}"}

# For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)