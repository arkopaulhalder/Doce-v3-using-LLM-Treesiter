import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from langchain.tools import Tool
from langchain.graphs import StateGraph
import google.generativeai as genai
import json
from treesitter.code_search import CodeSearchEngine

load_dotenv()

class LLM:
    def __init__(
        self,
        api_key: str = None,
        model: str = "gemini-pro",
        max_tokens: int = 1000,
        max_retries: int = 3,
        retry_delay: int = 1
    ):
        # Initialize Gemini
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not provided and not found in environment")
        self.code_search = self.CodeSearchEngine()
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')

        # Initialize code search engine
        self.code_search = CodeSearchEngine()

        # Setup langchain workflow
        self.setup_workflow()

    def setup_workflow(self):
        """Setup the documentation generation workflow using langchain."""
        self.workflow = StateGraph(name="Documentation Generation")

        # Define workflow states
        self.workflow.add_state("identify_language")
        self.workflow.add_state("parse_code")
        self.workflow.add_state("search_similar_code")
        self.workflow.add_state("generate_docs")
        self.workflow.add_state("format_output")

        # Define tools
        self.tools = [
            Tool(
                name="identify_language",
                func=self._identify_language_tool,
                description="Identify the programming language of a code file"
            ),
            Tool(
                name="search_similar_code",
                func=self._search_similar_code_tool,
                description="Search for similar code patterns"
            ),
            Tool(
                name="generate_documentation",
                func=self._generate_documentation_tool,
                description="Generate documentation for code"
            )
        ]

        # Define transitions
        self.workflow.add_edge("identify_language", "parse_code")
        self.workflow.add_edge("parse_code", "search_similar_code")
        self.workflow.add_edge("search_similar_code", "generate_docs")
        self.workflow.add_edge("generate_docs", "format_output")

    def _identify_language_tool(self, file_path: str) -> Dict[str, str]:
        """Tool to identify programming language from file path."""
        if file_path.endswith('.py'):
            return {"language": "python"}
        elif file_path.endswith('.java'):
            return {"language": "java"}
        elif file_path.endswith(('.cpp', '.hpp')):
            return {"language": "cpp"}
        elif file_path.endswith(('.c', '.h')):
            return {"language": "c"}
        return {"language": "unknown"}

    def _search_similar_code_tool(self, code: str) -> List[Dict]:
        """Tool to search for similar code patterns."""
        return self.code_search.search_code_elements(keyword=code)

    def _generate_documentation_tool(self, code: str, language: str) -> Dict[str, Any]:
        """Tool to generate documentation for code using Gemini Pro."""
        try:
            prompt = self._create_documentation_prompt(code, language)
            response = self.model.generate_content(prompt)

            if response.text:
                return self._structure_documentation(response.text)
            else:
                return {"error": "Failed to generate documentation"}

        except Exception as e:
            print(f"Documentation generation error: {str(e)}")
            return {"error": str(e)}

    def _create_documentation_prompt(self, code: str, language: str) -> str:
        """Create a prompt for documentation generation."""
        return f"""
        Generate comprehensive documentation for the following {language} code:

        {code}

        Please include:
        1. Overall purpose and functionality
        2. Detailed method/function descriptions
        3. Parameters and return values
        4. Usage examples
        5. Dependencies and requirements
        6. Any important notes or warnings

        Format the documentation in a clear, structured manner.
        Focus on:
        - Clear explanations of complex logic
        - Accurate parameter descriptions
        - Real-world usage examples
        - Common pitfalls or edge cases
        - Best practices and optimization tips

        Return the documentation in a structured format that separates different sections.
        """

    def _structure_documentation(self, raw_docs: str) -> Dict[str, Any]:
        """Structure raw documentation into a standardized format."""
        sections = raw_docs.split('\n\n')

        structured_docs = {
            "overview": "",
            "methods": [],
            "examples": [],
            "dependencies": [],
            "notes": []
        }

        current_section = None

        for section in sections:
            if section.lower().startswith(('overview', 'purpose')):
                structured_docs["overview"] = section
            elif section.lower().startswith(('method', 'function')):
                structured_docs["methods"].append(section)
            elif section.lower().startswith('example'):
                structured_docs["examples"].append(section)
            elif section.lower().startswith('dependen'):
                structured_docs["dependencies"].append(section)
            elif section.lower().startswith(('note', 'warning')):
                structured_docs["notes"].append(section)

        return structured_docs

    async def generate_documentation(self, code: str, language: str) -> Dict[str, Any]:
        """Generate documentation using the workflow."""
        try:
            # Execute the workflow
            state = {"code": code, "language": language}

            # Identify language
            lang_result = self._identify_language_tool(state["language"])
            state["detected_language"] = lang_result["language"]

            # Search for similar code
            similar_code = self._search_similar_code_tool(state["code"])
            state["similar_patterns"] = similar_code

            # Generate documentation
            docs = self._generate_documentation_tool(
                code=state["code"],
                language=state["detected_language"]
            )

            if "error" in docs:
                return {
                    "success": False,
                    "error": docs["error"]
                }

            return {
                "success": True,
                "documentation": docs,
                "similar_patterns": state["similar_patterns"],
                "language": state["detected_language"]
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def save_documentation(self, documentation: Dict[str, Any], output_file: str) -> bool:
        """Save the generated documentation to a JSON file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(documentation, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving documentation: {str(e)}")
            return False

    async def generate_structured_documentation(self, language: str, methods: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate structured documentation for the given methods and context.

        Args:
            language (str): Programming language
            methods (List[Dict[str, Any]]): List of parsed methods
            context (Dict[str, Any]): Additional context for documentation generation

        Returns:
            Dict[str, Any]: Structured documentation
        """
        try:
            combined_code = "\n\n".join([method.get('method_source_code', '') for method in methods])
            prompt = self._create_documentation_prompt(combined_code, language)
            
            # Add context information to the prompt
            prompt += f"\n\nAdditional context:\n{json.dumps(context, indent=2)}"

            response = self.model.generate_content(prompt)

            if response.text:
                structured_docs = self._structure_documentation(response.text)
                
                # Add method-specific documentation
                structured_docs['methods'] = []
                for method in methods:
                    method_doc = self._generate_documentation_tool(method.get('method_source_code', ''), language)
                    structured_docs['methods'].append({
                        'name': method.get('name', ''),
                        'documentation': method_doc
                    })

                return {
                    "success": True,
                    "documentation": structured_docs
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to generate documentation"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }