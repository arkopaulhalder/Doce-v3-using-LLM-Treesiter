from flask import Flask, request, jsonify
import os
from typing import Dict, Any
from dotenv import load_dotenv
from llm import LLM
import utils
import asyncio
import logging
from treesitter.treesitter_py import MultiLanguageParser
from treesitter.code_search import CodeSearchEngine, SearchCodeElementsParams

load_dotenv()

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize CodeSearchEngine
code_search_engine = CodeSearchEngine()

def get_language_from_extension(file_path: str) -> str:
    """Get the programming language based on the file extension."""
    _, ext = os.path.splitext(file_path)
    extension_to_language = {
        '.py': 'python',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.js': 'javascript'
    }
    return extension_to_language.get(ext.lower(), 'unknown')

def process(folder_path: str) -> Dict[str, Any]:
    """
    Process a folder to generate documentation.

    Args:
        folder_path (str): Path to the root folder

    Returns:
        Dict[str, Any]: Generated documentation and metadata
    """
    try:
        # Initialize documentation storage
        documentation = {}
        file_count = 0
        error_count = 0
        
        # Setup LLM
        llm = LLM()
        
        # Walk through the folder
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip hidden files and directories
                if any(part.startswith('.') for part in file_path.split(os.sep)):
                    continue
                
                # Get language for the file
                language = get_language_from_extension(file_path)
                if language == 'unknown':
                    logger.warning(f"Unsupported file extension for {file_path}")
                    continue
                
                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse code using MultiLanguageParser
                    parser = MultiLanguageParser(language)
                    parsed_code = parser.parse(content)
                    
                    # Find similar code elements
                    search_params = SearchCodeElementsParams(
                        element_type=parsed_code.get('type'),
                        keyword=content[:100],  # Use first 100 chars as search text
                        index_name='code_elements'
                    )
                    similar_elements = code_search_engine.search_code_elements(**search_params.dict())
                    
                    doc_context = {
                        'primary_element': parsed_code,
                        'similar_elements': similar_elements,
                        'combined_context': "\n".join([
                            "Similar code patterns found:",
                            *[f"- {elem['text']}" for elem in similar_elements[:3]]
                        ])
                    }
                    
                    doc_result = asyncio.run(llm.generate_structured_documentation(
                        language=language,
                        methods=parsed_code['functions'],
                        context=doc_context
                    ))
                    
                    if doc_result:
                        relative_path = os.path.relpath(file_path, folder_path)
                        documentation[relative_path] = {
                            "language": language,
                            "documentation": doc_result,
                            "similar_patterns": [elem['text'] for elem in similar_elements[:3]]
                        }
                        file_count += 1
                        logger.info(f"Processed file: {relative_path}")
                    else:
                        error_count += 1
                        logger.warning(f"Failed to generate documentation for: {relative_path}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing {file_path}: {str(e)}")
                    continue
        
        # Format and save documentation
        formatted_docs = utils.CodeUtils.format_documentation(documentation)
        output_dir = os.path.join(folder_path, 'documentation')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'documentation.json')
        
        if utils.CodeUtils.save_documentation(formatted_docs, output_file):
            logger.info(f"Documentation saved successfully to: {output_file}")
            return {
                "success": True,
                "files_processed": file_count,
                "errors": error_count,
                "output_file": output_file,
                "documentation": formatted_docs
            }
        else:
            logger.error("Failed to save documentation")
            return {
                "success": False,
                "error": "Failed to save documentation",
                "files_processed": file_count,
                "errors": error_count
            }
            
    except Exception as e:
        logger.error(f"Error processing folder: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@app.route('/generate-docs', methods=['POST'])
def generate_documentation():
    data = request.get_json()
    if not data or 'folder_path' not in data:
        return jsonify({'error': 'folder_path is required'}), 400

    folder_path = data['folder_path']
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return jsonify({'error': 'Invalid folder path'}), 400

    result = process(folder_path)

    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})