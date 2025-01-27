#File for multilanguage parser which makes use of tree-sitter library to parse source code in multiple languages the treesitter_java.py 
#file is just an example for java specific parser. The multilanguage parser is a class that can parse source code in multiple languages:
# and not nly for java. The class has a constructor that takes a language as an argument and initializes the parser with the specified language.
from typing import List, Dict, Any, Optional
from tree_sitter import Language, Parser, Node
import tree_sitter_python as ts_python
import tree_sitter_java as ts_java
import tree_sitter_cpp as ts_cpp
import tree_sitter_c as tsc
import tree_sitter_javascript as ts_javascript
from constants import Language as LangType
from tree_sitter import TSLanguage

class TreesitterMethodNode:
    def __init__(self, name: str, doc_comment: str, method_source_code: str, 
                 start_line: int, end_line: int):
        self.name = name
        self.doc_comment = doc_comment
        self.method_source_code = method_source_code
        self.start_line = start_line
        self.end_line = end_line

class MultiLanguageParser:
    LANGUAGE_CONFIGS = {
        'python': {
            'module': ts_python,
            'method_identifier': 'def_statement',
            'class_identifier': 'class',
            'import_identifiers': ['import statement', 'from statement import list'],
            'docstring_type': 'string',
            'name_field': 'name',
            'params_field': 'parameters'
        },
        'java': {
            'module': ts_java,
            'method_identifier': ['public void exampleMethod(){', 'public static void exampleMethod(){','private void exampleMethod(){'],
            'class_identifier': 'public class Example {',
            'import_identifiers': ['import Scanner', 'import java.util.Scanner', 'import java.util.*'],
            'docstring_type': 'comment',
            'name_field': 'name',
            'params_field': 'formal_parameters'
        },
        'cpp': {
            'module': ts_cpp,
            'method_identifier': 'void function_name(){',
            'class_identifier': 'class Example{',
            'import_identifiers': ['#include <iostream>', '#include <vector>', '#include <string>'],
            'docstring_type': 'comment',
            'name_field': 'declarator',
            'params_field': 'parameter_list'
        },
        'c': {
            'module': tsc,
            'method_identifier': 'void function_name(){',
            'class_identifier': 'struct Example{',
            'import_identifiers': ['#include <stdio.h>', '#include <stdlib.h>', '#include <string.h>'],
            'docstring_type': 'comment',
            'name_field': 'declarator',
            'params_field': 'parameter_list'
        },
        'javascript': {
            'module': ts_javascript,
            'method_identifier': 'function exampleFunction(){',
            'class_identifier': 'class declaration{',
            'import_identifiers': ['import * as fs from "fs"', 'import * as path from "path"', 'import { example } from "./example"'],
            'docstring_type': 'comment',
            'name_field': 'name',
            'params_field': 'formal_parameters'
        }
    }

    def __init__(self, language: str):
        self.language = language.lower()
        if self.language not in self.LANGUAGE_CONFIGS:
            raise ValueError(f"Unsupported language: {language}")
        
        self.config = self.LANGUAGE_CONFIGS[self.language]
        self.parser = Parser()
        self._initialize_parser(self.language)
        
#@pytest.mark.filterwarnings("ignore:The constructor for class 'Language' is deprecated:DeprecationWarning")
    def _initialize_parser(self, language: str) -> None:
        """Initialize the parser with the specified language."""
        lang_module = self.config['module']
        try:
            self.parser.set_language(lang_module.language())
        except Exception as e:
            raise Exception(f"Failed to initialize parser for {language} language: {str(e)}")
        
    def parse(self, source_code: str) -> Dict[str, Any]:
        """Parse source code and extract all relevant information."""
        try:
            tree = self.parser.parse(bytes(source_code, 'utf8'))
            return {
                'imports': self._extract_imports(tree.root_node),
                'classes': self._extract_classes(tree.root_node),
                'functions': self._extract_functions(tree.root_node),
                'variables': self._extract_variables(tree.root_node)
            }
        except Exception as e:
            raise Exception(f"Failed to parse {self.language} source code: {str(e)}")

    def _extract_imports(self, node: Node) -> List[Dict[str, str]]:
        """Extract import statements based on language-specific syntax."""
        imports = []
        
        def visit_import(node):
            if node.type in self.config['import_identifiers']:
                imports.append({
                    'type': node.type,
                    'text': node.text.decode('utf-8')
                })
            for child in node.children:
                visit_import(child)
                
        visit_import(node)
        return imports

    def _extract_functions(self, node: Node) -> List[TreesitterMethodNode]:
        """Extract function/method definitions based on language-specific syntax."""
        functions = []
        
        def visit_function(node):
            if node.type == self.config['method_identifier']:
                # The `child_by_field_name` method in the `tree-sitter` library is
                # used to retrieve a specific child node of a given node based on the
                # field name associated with that child node.
                name_node = node.child_by_field_name(self.config['name_field'])
                name = self._extract_name(name_node)
                doc_comment = self._find_docstring(node)
                source_code = node.text.decode('utf-8')
                
                functions.append(TreesitterMethodNode(
                    name=name,
                    doc_comment=doc_comment,
                    method_source_code=source_code,
                    start_line=node.start_point[0],
                    end_line=node.end_point[0]
                ))
            
            for child in node.children:
                visit_function(child)
                
        visit_function(node)
        return functions

    def _extract_classes(self, node: Node) -> List[Dict[str, Any]]:
        """Extract class definitions based on language-specific syntax."""
        classes = []
        
        def visit_class(node):
            if node.type == self.config['class_identifier']:
                name_node = node.child_by_field_name(self.config['name_field'])
                name = self._extract_name(name_node)
                doc_comment = self._find_docstring(node)
                
                classes.append({
                    'name': name,
                    'docstring': doc_comment,
                    'methods': self._extract_functions(node),
                    'start_point': node.start_point,
                    'end_point': node.end_point
                })
            
            for child in node.children:
                visit_class(child)
                
        visit_class(node)
        return classes

    def _extract_variables(self, node: Node) -> List[Dict[str, str]]:
        """Extract variable declarations based on language-specific syntax."""
        variables = []
        
        def visit_variable(node):
            # Handle different variable declaration patterns based on language
            if self.language in ['python']:
                if node.type == 'assignment':
                    left_node = node.child_by_field_name('left')
                    right_node = node.child_by_field_name('right')
                    if left_node and right_node:
                        variables.append({
                            'name': left_node.text.decode('utf-8'),
                            'value': right_node.text.decode('utf-8')
                        })
            elif self.language in ['java', 'cpp', 'c']:
                if node.type == 'declaration':
                    name_node = node.child_by_field_name('declarator')
                    if name_node:
                        variables.append({
                            'name': name_node.text.decode('utf-8'),
                            'type': node.child_by_field_name('type').text.decode('utf-8') if node.child_by_field_name('type') else ''
                        })
            elif self.language == 'javascript':
                if node.type in ['variable_declaration', 'lexical_declaration']:
                    for declarator in node.children:
                        if declarator.type == 'variable_declarator':
                            name_node = declarator.child_by_field_name('name')
                            value_node = declarator.child_by_field_name('value')
                            if name_node:
                                variables.append({
                                    'name': name_node.text.decode('utf-8'),
                                    'value': value_node.text.decode('utf-8') if value_node else ''
                                })
            
            for child in node.children:
                visit_variable(child)
                
        visit_variable(node)
        return variables

    def _find_docstring(self, node: Node) -> str:
        """Extract documentation based on language-specific conventions."""
        # Handle Python-style doc_strings
        if self.language == 'python':
            for child in node.children:
                if child.type == 'expression_statement':
                    string_node = child.children[0]
                    if string_node.type == 'string':
                        return string_node.text.decode('utf-8')
        
        # Handle comment-style documentation
        prev_sibling = node.prev_named_sibling
        if prev_sibling and prev_sibling.type == self.config['docstring_type']:
            return prev_sibling.text.decode('utf-8')
        
        return ''

    def _extract_name(self, node: Node) -> str:
        """Extract name from a node based on language-specific patterns."""
        if not node:
            return ''
            
        if self.language in ['cpp', 'c']:
            # Handle complex C/C++ function declarators
            if node.type == 'function_declarator':
                for child in node.children:
                    if child.type == 'identifier':
                        return child.text.decode('utf-8')
            return node.text.decode('utf-8')
        
        return node.text.decode('utf-8')