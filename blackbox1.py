import os
import re
import json
import time
import zipfile
import logging
import io
import hashlib
import gzip
import ast
import traceback
from typing import Optional, Dict, Any, List, Set, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
from dotenv import load_dotenv
load_dotenv()

# FastAPI imports
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import requests
from functools import lru_cache

# API Configuration
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("Error: MISTRAL_API_KEY is not set in the environment.")

# Model Configuration
MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "2"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))

# Available modules mapping - modules guaranteed to be in the Docker container
AVAILABLE_MODULES = {
    'pandas': 'pd', 
    'numpy': 'np', 
    'PIL': 'PIL',
    'PIL.Image': 'Image',
    'zipfile': 'zipfile', 
    'io': 'io', 
    'hashlib': 'hashlib',
    'json': 'json', 
    're': 're',
    'pdfplumber': 'pdfplumber',
    'datetime': 'datetime',
    'csv': 'csv',
    'os': 'os',
    'sys': 'sys',
    'bs4': 'bs4',
    'bs4.BeautifulSoup': 'BeautifulSoup',
    'requests': 'requests',
    'openpyxl': 'openpyxl',
    'dateutil.parser': 'date_parser',
    'gzip': 'gzip',
    'feedparser': 'feedparser',
    'github': 'Github',
    'prettier': 'prettier'
}

# Enhanced system prompt with file processing improvements and available libraries
SYSTEM_PROMPT = f"""
You are an AI-driven code generator and executor with structured file-processing capabilities. Your tasks:

### 1. **File Type Identification & Handling**
   - Analyze incoming files (ZIP, PDF, CSV, JSON, Excel, etc.) and determine their format.
   - Use file signatures and content analysis, not just file extensions.
   - For ZIP files: Properly extract contents using io.BytesIO and process each file.
   - For text files: Check multiple encodings (UTF-8, CP-1252, UTF-16) if standard fails.

### 2. **Memory-Only Processing**
   - Process all files in memory (never use filesystem).
   - When working with ZIP files: Extract using zipfile.ZipFile(io.BytesIO(zip_data)).
   - Use BytesIO/StringIO for all file operations.

### 3. **Data Processing Standards**
   - Convert numeric fields appropriately: marks→int, value→float, date→datetime (ISO 8601).
   - Use pandas with proper error handling for structured data.
   - Handle date strings consistently (parse with dateutil.parser if needed).
   - For PDFs, use pdfplumber with appropriate extraction methods.

### 4. **Direct Answer Format**
   - Return ONLY the specific answer to the question in the simplest format.
   - For numeric answers, return just the number without explanations.
   - For text answers, return minimally formatted text.
   - Format dates in ISO 8601 (YYYY-MM-DD) unless otherwise specified.

### 5. **Error Handling & Debugging**
   - Catch and report specific errors, not generic messages.
   - Include detailed diagnostics in error reporting.
   - Always verify data before processing (e.g., check CSV headers).

### 6. **Question Categorization**
   - For data analysis: Process and return the specific value requested.
   - For GitHub/API requests: Return only the specific information asked.
   - For complex transformations: Focus only on reporting the final result.

### 7. **Efficient Processing**
   - Use vectorized operations when possible with pandas.
   - Prefer faster libraries (numpy vs. loops, pandas vs. csv).
   - Optimize memory usage for large files.

### 8. **Available Libraries**
   - You can ONLY use these libraries in your code:
     {', '.join(AVAILABLE_MODULES.keys())}
   - Do NOT import any other libraries as they will cause ImportError.
   - Always handle potential ImportError gracefully in your code.
   - Use try/except blocks for risky operations.

Remember: Answer questions DIRECTLY and CONCISELY. Return only the specific value, number, or brief text that answers the question without explanation or commentary.

Always generate **executable** Python code in ```python blocks following these rules exactly.
The file data will be provided as a variable named 'file_data' in the execution context.
"""

app = FastAPI()
handler = Mangum(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

class CodeGenerator:
    def __init__(self):
        self.retries = MAX_RETRIES
        self.timeout = REQUEST_TIMEOUT
        self.retry_delay = RETRY_DELAY

    @lru_cache(maxsize=128)
    def get_file_type_hint(self, filename: str, first_bytes: bytes) -> str:
        """Determine file type based on filename and content signatures."""
        # Check file signatures first
        if first_bytes.startswith(b'PK\x03\x04'):
            return "ZIP archive"
        elif first_bytes.startswith(b'%PDF'):
            return "PDF document"
        elif first_bytes.startswith(b'\xff\xd8\xff'):
            return "JPEG image"
        elif first_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return "PNG image"
        elif first_bytes.startswith(b'RIFF') and b'WEBP' in first_bytes[:12]:
            return "WebP image"
        
        # Fall back to extension checks
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        extension_map = {
            'zip': "ZIP archive",
            'csv': "CSV file",
            'json': "JSON file",
            'jsonl': "JSONL file",
            'xlsx': "Excel file",
            'xls': "Excel file",
            'pdf': "PDF document",
            'txt': "Text file",
            'gz': "GZIP compressed file",
            'webp': "WebP image"
        }
        
        return extension_map.get(extension, "unknown")

    def query_mistral(self, prompt: str) -> str:
        """Query the Mistral API with exponential backoff."""
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
            "temperature": 0.1  # Lower temperature for more deterministic outputs
        }

        for attempt in range(self.retries):
            try:
                logger.info(f"Sending request to Mistral API (attempt {attempt+1}/{self.retries})")
                response = requests.post(
                    MISTRAL_URL, 
                    json=data, 
                    headers=headers, 
                    timeout=self.timeout
                )
                
                if response.status_code == 429:
                    wait = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited. Retrying in {wait}s")
                    time.sleep(wait)
                    continue
                    
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {str(e)}")
                wait = self.retry_delay * (2 ** attempt)
                logger.warning(f"Request failed. Retrying in {wait}s")
                time.sleep(wait)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                logger.error(f"Response parsing error: {str(e)}")
                if attempt == self.retries - 1:
                    raise HTTPException(500, f"Failed to parse Mistral API response: {str(e)}")
                wait = self.retry_delay * (2 ** attempt)
                time.sleep(wait)
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                if attempt == self.retries - 1:
                    raise HTTPException(500, f"Mistral API error: {str(e)}")
                wait = self.retry_delay * (2 ** attempt)
                time.sleep(wait)
                
        raise HTTPException(503, "Mistral API unavailable after multiple attempts")

class DynamicCodeExecutor:
    @staticmethod
    def get_required_modules(code_string: str) -> Set[str]:
        """Parse code string and detect required modules."""
        try:
            # Parse the code
            parsed = ast.parse(code_string)
            
            # Extract import statements
            imports = []
            for node in ast.walk(parsed):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:  # Check if module is not None
                        imports.append(node.module)
            
            return set(imports)
        except SyntaxError:
            # If code can't be parsed, return empty set
            logger.warning("Failed to parse code for module extraction")
            return set()

    @staticmethod
    def load_modules_dynamically(required_modules: Set[str]) -> Tuple[Dict[str, Any], List[str]]:
        """Dynamically import modules as needed."""
        modules = {}
        unavailable = []
        
        # First try to import predefined modules that might be needed
        for module_name, alias in AVAILABLE_MODULES.items():
            if module_name in required_modules or any(m.startswith(f"{module_name}.") for m in required_modules):
                try:
                    if '.' in module_name:
                        # For submodules like bs4.BeautifulSoup
                        base_module = module_name.split('.')[0]
                        base = __import__(base_module)
                        for comp in module_name.split('.')[1:]:
                            base = getattr(base, comp)
                        modules[alias] = base
                    else:
                        modules[alias] = __import__(module_name)
                except ImportError:
                    unavailable.append(module_name)
                    logger.warning(f"Failed to import module: {module_name}")
        
        # Then try to import any other required modules not in our predefined list
        for module_name in required_modules:
            if '.' not in module_name and module_name not in AVAILABLE_MODULES.keys():
                try:
                    modules[module_name] = __import__(module_name)
                except ImportError:
                    unavailable.append(module_name)
                    logger.warning(f"Failed to import module: {module_name}")
        
        return modules, unavailable

    @staticmethod
    def execute(code: str, file_data=None) -> Dict[str, Any]:
        """Execute code in a dynamic environment with enhanced error handling."""
        # Extract required modules from code
        required_modules = DynamicCodeExecutor.get_required_modules(code)
        logger.info(f"Required modules detected: {required_modules}")
        
        # Load necessary modules
        modules_dict, unavailable = DynamicCodeExecutor.load_modules_dynamically(required_modules)
        
        if unavailable:
            logger.warning(f"Unavailable modules: {unavailable}")
            
        try:
            # Create the globals dictionary with common modules
            globals_dict = {
                # Standard libraries always included
                'io': io,
                'StringIO': io.StringIO,
                'BytesIO': io.BytesIO,
                'file_data': file_data,
                'os': os,
                'sys': __import__('sys'),
                're': re,
                'json': json,
                'csv': __import__('csv'),
                'zipfile': zipfile,
                'hashlib': hashlib,
                'time': time,
                'datetime': __import__('datetime'),
                'calendar': __import__('calendar'),
                'shutil': __import__('shutil'),
                'pathlib': __import__('pathlib'),
                'gzip': __import__('gzip'),
                'subprocess': __import__('subprocess'),
                'collections': __import__('collections'),

                # Third-party libraries (assumed pre-installed or handled via Docker)
                'pandas': __import__('pandas'),
                'chardet': __import__('chardet'),
                'feedparser': __import__('feedparser'),
                'requests': __import__('requests'),
                'openpyxl': __import__('openpyxl'),
                'PIL': __import__('PIL.Image'),
            }

            
            # Create a local namespace for execution
            local_dict = {}
            
            # Execute the code with detailed error tracking
            try:
                exec(code, globals_dict, local_dict)
            except Exception as e:
                # Get detailed traceback
                tb = traceback.format_exc()
                logger.error(f"Execution error: {str(e)}\n{tb}")
                return {
                    "success": False,
                    "error": f"Execution Error: {str(e)}",
                    "traceback": tb,
                    "unavailable_modules": unavailable
                }
            
            # Check for result in the local namespace
            if 'result' in local_dict:
                return {
                    "success": True,
                    "result": local_dict['result']
                }
            elif any(var for var in local_dict if not var.startswith('_')):
                # Return the last non-private variable as fallback
                vars_list = [var for var in local_dict if not var.startswith('_')]
                return {
                    "success": True,
                    "result": local_dict[vars_list[-1]]
                }
            else:
                return {
                    "success": True,
                    "result": "Execution successful but no result was returned."
                }
                
        except Exception as e:
            logger.error(f"Setup Error: {str(e)}")
            return {
                "success": False,
                "error": f"System Error: {str(e)}",
                "traceback": traceback.format_exc(),
                "unavailable_modules": unavailable
            }

    @staticmethod
    def debug_and_retry(question: str, file_info: Dict[str, Any], error_data: Dict[str, Any]) -> str:
        """Generate improved code based on error analysis."""
        logger.info("Generating corrected code with detailed error information")
        
        # Extract relevant error details
        error_message = error_data.get("error", "Unknown error")
        traceback_info = error_data.get("traceback", "No traceback available")
        unavailable_modules = error_data.get("unavailable_modules", [])
        
        # Create list of available modules (excluding unavailable ones)
        available_modules = [m for m in AVAILABLE_MODULES.keys() if m not in unavailable_modules]
        
        # Create detailed debug prompt
        debug_prompt = f"""
        Error Analysis Required:
        
        Original Question: {question}
        
        File Details:
        - Name: {file_info.get('filename', 'Unknown')}
        - Type: {file_info.get('type', 'Unknown')}
        - Size: {file_info.get('size', 'Unknown')} bytes
        
        Error Information:
        {error_message}
        
        Traceback:
        {traceback_info}
        
        Available modules:
        {', '.join(available_modules)}
        
        Unavailable modules (DO NOT USE THESE):
        {', '.join(unavailable_modules) if unavailable_modules else "None"}
        
        Please generate corrected code that:
        1. Uses ONLY the available modules listed above
        2. Addresses the specific error in the traceback
        3. Uses robust error handling with try/except blocks
        4. Returns ONLY the precise answer to the question
        5. For numeric answers, return just the number
        6. For text answers, return minimal text
        
        Important: The file data is already available as the variable 'file_data'.
        DO NOT use any of the unavailable modules.
        """
        
        corrected_code = CodeGenerator().query_mistral(debug_prompt)
        
        # Extract code from response
        if "```python" in corrected_code:
            corrected_code = corrected_code.split("```python")[1].split("```")[0].strip()
        
        return corrected_code

def format_result(result: Any) -> str:
    """Format the execution result for the final response."""
    if isinstance(result, (int, float)):
        # For numeric results, return just the number
        return str(result)
    elif isinstance(result, dict):
        # For dictionaries, try to extract the most relevant information
        if len(result) == 1:
            # If there's only one key, return its value
            return str(list(result.values())[0])
        else:
            # Return the full dictionary as JSON
            return json.dumps(result, default=str)
    elif hasattr(result, 'to_dict') and callable(getattr(result, 'to_dict')):
        # For pandas Series or DataFrame, convert to dict first
        return str(result)
    else:
        # For everything else, convert to string
        return str(result)

@app.post("/submit")
async def submit(
    background_tasks: BackgroundTasks,
    question: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    generator = CodeGenerator()
    executor = DynamicCodeExecutor()
    
    try:
        # Process file upload if a file is provided
        file_data = None
        file_info = {"filename": "None", "type": "None", "size": 0}
        
        if file:
            # Read the uploaded file content directly into memory
            file_data = await file.read()
            file_size = len(file_data)
            
            # Get file type hint
            first_bytes = file_data[:32] if file_data else b''
            file_type = generator.get_file_type_hint(file.filename, first_bytes)
            
            # Update file info
            file_info = {
                "filename": file.filename,
                "type": file_type,
                "size": file_size,
                "first_bytes_hex": first_bytes.hex()[:20] + "..." if first_bytes else ""
            }
            
            logger.info(f"Processing file: {file_info['filename']}, Type: {file_info['type']}, Size: {file_info['size']} bytes")

        # Enhance the question with detailed file information
        enhanced_question = question
        if file_data:
            enhanced_question = f"""
            Question: {question}
            
            File Information:
            - Filename: {file_info['filename']}
            - File type: {file_info['type']}
            - File size: {file_info['size']} bytes
            - First bytes (hex): {file_info['first_bytes_hex']}
            
            Important notes:
            1. Use only these modules: {', '.join(AVAILABLE_MODULES.keys())}
            2. Return ONLY the precise answer to the question.
            3. Handle all potential errors with try/except blocks.
            """

        # Generate solution code based on the question
        response = generator.query_mistral(enhanced_question)
        
        # If response doesn't contain code, it's likely a direct answer
        if "```python" not in response:
            logger.info("Response contains no code block - returning direct answer")
            return {"answer": response.strip()}
            
        # Extract code from the response
        code = response.split("```python")[1].split("```")[0].strip()
        
        # Execute the generated code with file data
        result_data = executor.execute(code, file_data)
        
        # Handle execution errors
        if not result_data["success"]:
            logger.error(f"Execution failed: {result_data['error']}")
            
            # Try to debug and get corrected code
            corrected_code = executor.debug_and_retry(question, file_info, result_data)
            
            # Execute the corrected code
            result_data = executor.execute(corrected_code, file_data)
            
            # If still error, return the error message in a simplified format
            if not result_data["success"]:
                return {"answer": result_data["error"]}

        # Format the result for the final response
        formatted_result = format_result(result_data["result"])
        logger.info("Execution successful, returning answer")
        return {"answer": formatted_result}
        
    except HTTPException as he:
        logger.error(f"HTTP Exception: {str(he.detail)}")
        raise he
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        traceback_str = traceback.format_exc()
        logger.error(f"Traceback: {traceback_str}")
        return {"answer": f"Error: {str(e)}"}

# Optional background task for logging/analytics
async def log_request(question: str, file_info: Dict, result: str):
    """Log request details to a database or monitoring system."""
    # Implementation depends on your specific needs
    logger.info(f"Request logged: {question[:50]}...")

# For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)