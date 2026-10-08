from mitecoder.config.schema import RetrievalConfig
from mitecoder.retrieval.hybrid import HybridRetrieval
from mitecoder.retrieval.lexical import LexicalRetrieval
from mitecoder.retrieval.symbols import SymbolRetrieval


def create_retriever(config: RetrievalConfig):
    if config.strategy == "lexical":
        return LexicalRetrieval(config.max_files, config.max_lines_per_file)
    if config.strategy == "symbols":
        return SymbolRetrieval(config.max_files)
    if config.strategy == "hybrid":
        return HybridRetrieval(config.max_files, config.max_lines_per_file)
    raise ValueError(f"unknown retrieval strategy: {config.strategy}")
