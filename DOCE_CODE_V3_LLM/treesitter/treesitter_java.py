from typing import Dict, Any, List
from tree_sitter import Language, Parser, Node
import tree_sitter_java as ts_java
from treesitter import TreeSitterBase

class JavaParser(TreeSitterBase):
    def __init__(self):
        super().__init__()
        self.language_name = "java"

    def _initialize_parser(self) -> None:
        """Initialize the parser with Java language."""
        JAVA_LANGUAGE = Language(ts_java.language())
        self.parser.set_language(JAVA_LANGUAGE)

    def get_language_name(self) -> str:
        return self.language_name

    def parse_code(self, code_bytes: bytes) -> Dict[str, Any]:
        """Parse Java code and extract relevant information."""
        tree = self.parser.parse(code_bytes)
        root_node = tree.root_node

        return {
            'imports': self._extract_imports(root_node),
            'package': self._extract_package(root_node),
            'classes': self._extract_classes(root_node),
            'functions': self._extract_methods(root_node),
            'interfaces': self._extract_interfaces(root_node)
        }

    def _extract_package(self, node: Node) -> str:
        """Extract package declaration."""
        for child in node.children:
            if child.type == 'package_declaration':
                return child.text.decode('utf-8')
        return ''

    def _extract_imports(self, node: Node) -> List[Dict[str, str]]:
        """Extract import statements."""
        imports = []
        for child in node.children:
            if child.type == 'import_declaration':
                imports.append({
                    'type': 'import',
                    'text': child.text.decode('utf-8')
                })
        return imports

    def _extract_methods(self, node: Node) -> List[Dict[str, Any]]:
        """Extract method declarations."""
        methods = []
        
        def visit_method(node):
            if node.type == 'method_declaration':
                name_node = None
                for child in node.children:
                    if child.type == 'identifier':
                        name_node = child
                        break

                if name_node:
                    method_info = {
                        'name': name_node.text.decode('utf-8'),
                        'source_code': node.text.decode('utf-8'),
                        'doc_comment': self._extract_doc_comment(node),
                        'start_point': node.start_point,
                        'end_point': node.end_point,
                        'parameters': self._extract_parameters(node),
                        'return_type': self._extract_return_type(node)
                    }
                    methods.append(method_info)

            for child in node.children:
                visit_method(child)

        visit_method(node)
        return methods

    def _extract_classes(self, node: Node) -> List[Dict[str, Any]]:
        """Extract class declarations."""
        classes = []
        
        def visit_class(node):
            if node.type == 'class_declaration':
                name_node = None
                for child in node.children:
                    if child.type == 'identifier':
                        name_node = child
                        break

                if name_node:
                    class_info = {
                        'name': name_node.text.decode('utf-8'),
                        'methods': self._extract_methods(node),
                        'doc_comment': self._extract_doc_comment(node),
                        'fields': self._extract_fields(node)
                    }
                    classes.append(class_info)

            for child in node.children:
                visit_class(child)

        visit_class(node)
        return classes

    def _extract_interfaces(self, node: Node) -> List[Dict[str, Any]]:
        """Extract interface declarations."""
        interfaces = []
        
        def visit_interface(node):
            if node.type == 'interface_declaration':
                name_node = None
                for child in node.children:
                    if child.type == 'identifier':
                        name_node = child
                        break

                if name_node:
                    interface_info = {
                        'name': name_node.text.decode('utf-8'),
                        'methods': self._extract_methods(node),
                        'doc_comment': self._extract_doc_comment(node)
                    }
                    interfaces.append(interface_info)

            for child in node.children:
                visit_interface(child)

        visit_interface(node)
        return interfaces

    def _extract_doc_comment(self, node: Node) -> str:
        """Extract Javadoc comment."""
        prev_sibling = node.prev_sibling
        if prev_sibling and prev_sibling.type == 'comment':
            return prev_sibling.text.decode('utf-8')
        return ''

    def _extract_parameters(self, method_node: Node) -> List[Dict[str, str]]:
        """Extract method parameters."""
        parameters = []
        for child in method_node.children:
            if child.type == 'formal_parameters':
                for param in child.children:
                    if param.type == 'formal_parameter':
                        param_type = None
                        param_name = None
                        for param_child in param.children:
                            if param_child.type == 'type_identifier':
                                param_type = param_child.text.decode('utf-8')
                            elif param_child.type == 'identifier':
                                param_name = param_child.text.decode('utf-8')
                        if param_type and param_name:
                            parameters.append({
                                'type': param_type,
                                'name': param_name
                            })
        return parameters

    def _extract_return_type(self, method_node: Node) -> str:
        """Extract method return type."""
        for child in method_node.children:
            if child.type in ['type_identifier', 'void_type']:
                return child.text.decode('utf-8')
        return 'void'

    def _extract_fields(self, class_node: Node) -> List[Dict[str, str]]:
        """Extract class fields."""
        fields = []
        for child in class_node.children:
            if child.type == 'field_declaration':
                field_type = None
                field_name = None
                for field_child in child.children:
                    if field_child.type == 'type_identifier':
                        field_type = field_child.text.decode('utf-8')
                    elif field_child.type == 'variable_declarator':
                        for var_child in field_child.children:
                            if var_child.type == 'identifier':
                                field_name = var_child.text.decode('utf-8')
                if field_type and field_name:
                    fields.append({
                        'type': field_type,
                        'name': field_name
                    })
        return fields