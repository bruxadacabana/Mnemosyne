"""
Carregadores de documentos para diferentes formatos.
"""
import os
from typing import List
from langchain.schema import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    DirectoryLoader
)


def load_documents(directory: str) -> List[Document]:
    """
    Carrega todos os documentos de um diretório.
    Suporta PDF, DOCX e TXT.
    
    Args:
        directory: Caminho para o diretório com documentos
        
    Returns:
        Lista de documentos
    """
    documents = []
    
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Diretório não encontrado: {directory}")
    
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            
            try:
                if file.lower().endswith('.pdf'):
                    loader = PyPDFLoader(file_path)
                    documents.extend(loader.load())
                elif file.lower().endswith('.docx'):
                    loader = Docx2txtLoader(file_path)
                    documents.extend(loader.load())
                elif file.lower().endswith('.txt'):
                    loader = TextLoader(file_path, encoding='utf-8')
                    documents.extend(loader.load())
            except Exception as e:
                print(f"Erro ao carregar {file}: {e}")
                continue
    
    return documents


def load_single_file(file_path: str) -> List[Document]:
    """
    Carrega um único arquivo.
    
    Args:
        file_path: Caminho para o arquivo
        
    Returns:
        Lista com o documento carregado
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    
    file = os.path.basename(file_path)
    
    try:
        if file.lower().endswith('.pdf'):
            loader = PyPDFLoader(file_path)
            return loader.load()
        elif file.lower().endswith('.docx'):
            loader = Docx2txtLoader(file_path)
            return loader.load()
        elif file.lower().endswith('.txt'):
            loader = TextLoader(file_path, encoding='utf-8')
            return loader.load()
        else:
            raise ValueError(f"Formato não suportado: {file}")
    except Exception as e:
        print(f"Erro ao carregar {file}: {e}")
        return []

