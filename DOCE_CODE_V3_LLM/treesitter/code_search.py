from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, List
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from langchain.graphs import StateGraph
from langchain.tools import Tool
from dotenv import load_dotenv
import os

load_dotenv()

class SearchCodeElementsParams(BaseModel):
    """Model for validating code search parameters."""
    element_type: Optional[str] = Field(
        None,
        description="Type of code element (function_definition, class_definition, etc.)"
    )
    keyword: Optional[str] = Field(
        None,
        description="Keyword for BM25-based text search"
    )
    index_name: str = Field(
        default="code_elements",
        description="Elasticsearch index name"
    )

    @model_validator(mode="before")
    def validate_element_type(cls, values):
        valid_types = {
            "function_definition",
            "class_definition",
            "decorated_definition",
            "method_definition"
        }

        element_type = values.get("element_type")
        if element_type and element_type not in valid_types:
            raise ValueError(f"element_type must be one of {valid_types}")
        return values

class CodeSearchEngine:
    def __init__(self):
        self.es = Elasticsearch([os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")])
        self.setup_workflow()

    def setup_workflow(self):
        """Setup LangGraph workflow for code search and documentation."""
        self.workflow = StateGraph(name="Documentation Generation")

        # Define states
        self.workflow.add_state("parse_code")
        self.workflow.add_state("search_similar")
        self.workflow.add_state("generate_docs")
        self.workflow.add_state("format_output")

        # Add tools
        self.tools = [
            Tool(
                name="search_code_elements",
                func=self.search_code_elements,
                description="Search for similar code elements"
            ),
            Tool(
                name="index_code_elements",
                func=self.index_code_elements,
                description="Index new code elements"
            )
        ]

        # Define transitions
        self.workflow.add_edge("parse_code", "search_similar")
        self.workflow.add_edge("search_similar", "generate_docs")
        self.workflow.add_edge("generate_docs", "format_output")

    def search_code_elements(self, **kwargs) -> List[Dict]:
        """Search for code elements using Elasticsearch."""
        params = SearchCodeElementsParams(**kwargs)

        query = {
            "bool": {
                "must": [],
                "filter": []
            }
        }

        if params.element_type:
            query["bool"]["filter"].append({
                "term": {"type": params.element_type}
            })

        if params.keyword:
            query["bool"]["must"].append({
                "match": {"text": params.keyword}
            })

        try:
            response = self.es.search(
                index=params.index_name,
                body={"query": query},
                size=5  # Limit results
            )

            results = [{
                "id": hit["_id"],
                "type": hit["_source"]["type"],
                "text": hit["_source"]["text"],
                "file_path": hit["_source"]["file_path"],
                "score": hit["_score"]
            } for hit in response["hits"]["hits"]]

            return results

        except Exception as e:
            print(f"Search error: {str(e)}")
            return []

    def index_code_elements(self, flattened_data: List[Dict], index_name: str) -> bool:
        """Index code elements into Elasticsearch."""
        try:
            actions = [{
                "_index": index_name,
                "_id": doc["id"],
                "_source": doc
            } for doc in flattened_data]

            bulk(self.es, actions)
            return True

        except Exception as e:
            print(f"Indexing error: {str(e)}")
            return False

    def find_similar_code(self, code_element: Dict) -> List[Dict]:
        """Find similar code elements for better documentation."""
        try:
            params = {
                "element_type": code_element["type"],
                "keyword": code_element["text"][:100]  # Use first 100 chars as search text
            }
            return self.search_code_elements(**params)
        except Exception as e:
            print(f"Error finding similar code: {str(e)}")
            return []

    def prepare_documentation_context(self, code_element: Dict, similar_elements: List[Dict]) -> Dict:
        """Prepare context for documentation generation."""
        return {
            "primary_element": code_element,
            "similar_elements": similar_elements,
            "combined_context": "\n".join([
                "Similar code patterns found:",
                *[f"- {elem['text']}" for elem in similar_elements[:3]]
            ])
        }