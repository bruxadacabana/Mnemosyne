"""
Indexing and vectorstore
"""
from typing import List
from langchain.schema import Document
from langchain_community.vectorstores import Chroma

from .loaders import load_documents


def create_vectorstore(directory: str, persist_dir: str = "chroma_db") -> Chroma:
    """
    Cria um vectorstore a partir de documentos em um diretório.
    
    Args:
        directory: Caminho para o diretório com documentos
        persist_dir: Caminho para persistir o vectorstore
        
    Returns:
        Instância do Chroma vectorstore
    """
    documents = load_documents(directory)
    
    from langchain_community.embeddings import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_dir
    )
    vectorstore.persist()
    
    return vectorstore


def load_vectorstore(persist_dir: str = "chroma_db") -> Chroma:
    """
    Carrega um vectorstore existente.
    
    Args:
        persist_dir: Caminho do vectorstore persistido
        
    Returns:
        Instância do Chroma vectorstore
    """
    from langchain_community.embeddings import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings
    )
    
    return vectorstore

