from tree_sitter import Parser

class TreeSitterBase:
    def __init__(self, language):
        # Initialize the Tree-sitter parser with a specific language
        self.parser = Parser()
        self.parser.set_language(language)

    def parse(self, code):
        # Method to parse code using Tree-sitter
        if self.parser:
            return self.parser.parse(bytes(code, "utf8"))
        else:
            raise NotImplementedError("Parser not implemented")

def create_tree_sitter_instance(language):
    """
    Creates an instance of TreeSitterBase with the specified language and returns it.
    """
    instance = TreeSitterBase(language)
    return instance