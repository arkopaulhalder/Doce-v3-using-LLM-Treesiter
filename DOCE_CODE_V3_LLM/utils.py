from typing import Dict, Any, List, Optional
import os
import json
from tree_sitter import Parser, Language
from datetime import datetime
from pathlib import Path

class CodeUtils:
    @staticmethod
    def parse_code(content: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse code content and extract structural information.

        Args:
            content (str): Source code content
            language (Optional[str]): Programming language identifier

        Returns:
            Dict[str, Any]: Parsed code structure
        """
        if not language:
            language = CodeUtils.detect_language(content)

        try:
            # Convert content to proper encoding
            if isinstance(content, str):
                content = content.encode('utf-8')

            return {
                'content': content.decode('utf-8'),
                'language': language,
                'size': len(content)
            }
        except Exception as e:
            return {
                'error': f"Failed to parse code: {str(e)}",
                'language': language
            }

    @staticmethod
    def get_language_name(file_path: str) -> Optional[str]:
        """
        Determine programming language from file extension.

        Args:
            file_path (str): Path to source code file

        Returns:
            Optional[str]: Language identifier or None if unsupported
        """
        extension_map = {
            '.py': 'python',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.js': 'javascript',
            '.ts': 'typescript'
        }

        ext = Path(file_path).suffix.lower()
        return extension_map.get(ext)

    @staticmethod
    def detect_language(content: str) -> Optional[str]:
        """
        Attempt to detect programming language from code content.

        Args:
            content (str): Source code content

        Returns:
            Optional[str]: Detected language or None
        """
        # Simple heuristic-based detection
        indicators = {
            'python': ['def ', 'import ', 'class ', '#!.*python'],
            'java': ['public class', 'private class', 'protected class'],
            'cpp': ['#include <', 'using namespace', 'std::'],
            'c': ['#include <stdio.h>', 'int main(']
        }

        content_sample = content[:1000].lower()  # Check first 1000 chars

        for lang, patterns in indicators.items():
            if any(pattern.lower() in content_sample for pattern in patterns):
                return lang

        return None

    @staticmethod
    def save_documentation(docs: Dict[str, Any], output_path: str) -> bool:
        """
        Save generated documentation to file.

        Args:
            docs (Dict[str, Any]): Documentation data
            output_path (str): Path to save output

        Returns:
            bool: Success status
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(docs, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving documentation: {str(e)}")
            return False
        
    @staticmethod
    def get_language_name(self, file_path: str) -> str:
           """
           Get the programming language name based on the file extension.
    
           Args:
               file_path (str): Path to the source code file
    
           Returns:
               str: Programming language name
           """
           _, ext = os.path.splitext(file_path)
           ext = ext.lower()
    
           # Mapping of file extensions to language names
           extension_to_language = {
               '.py': 'python',
               '.js': 'javascript',
               '.java': 'java',
               '.cpp': 'cpp',
               '.c': 'c',
               '.cs': 'csharp',
               '.rb': 'ruby',
               '.go': 'go',
               '.php': 'php',
               '.html': 'html',
               '.css': 'css',
               # Add more mappings as needed
           }
    
           return extension_to_language.get(ext, 'unknown')

    @staticmethod
    def format_documentation(docs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format documentation into a standardized structure.

        Args:
            docs (Dict[str, Any]): Raw documentation data

        Returns:
            Dict[str, Any]: Formatted documentation
        """
        formatted = {
            'metadata': {
                'generated_at': str(datetime.now()),
                'version': '1.0'
            },
            'files': {}
        }

        for file_path, file_docs in docs.items():
            if file_docs.get('status') == 'success':
                formatted['files'][file_path] = {
                    'language': file_docs.get('language', 'unknown'),
                    'documentation': file_docs.get('documentation', {}),
                    'similar_patterns': file_docs.get('similar_patterns', [])
                }

        return formatted