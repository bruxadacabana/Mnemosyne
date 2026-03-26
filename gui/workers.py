# Threads for indexing, questions, summaries

from PySide6.QtCore import QThread, Signal
import os
from core.indexer import create_vectorstore, load_vectorstore
from core.rag import setup_qa_chain, ask
from core.summarizer import summarize_all

class IndexWorker(QThread):
    finished = Signal(bool, str)  # sucesso, mensagem

    def __init__(self, docs_folder, persist_dir):
        super().__init__()
        self.docs_folder = docs_folder
        self.persist_dir = persist_dir

    def run(self):
        try:
            create_vectorstore(self.docs_folder, self.persist_dir)
            self.finished.emit(True, "Indexação concluída com sucesso.")
        except Exception as e:
            self.finished.emit(False, f"Erro: {str(e)}")

class AskWorker(QThread):
    finished = Signal(str)  # resposta

    def __init__(self, vectorstore, question):
        super().__init__()
        self.vectorstore = vectorstore
        self.question = question

    def run(self):
        try:
            chain = setup_qa_chain(self.vectorstore)
            answer = ask(chain, self.question)
            self.finished.emit(answer)
        except Exception as e:
            self.finished.emit(f"Erro: {str(e)}")

class SummarizeWorker(QThread):
    finished = Signal(str)

    def __init__(self, vectorstore):
        super().__init__()
        self.vectorstore = vectorstore

    def run(self):
        try:
            summary = summarize_all(self.vectorstore)
            self.finished.emit(summary)
        except Exception as e:
            self.finished.emit(f"Erro: {str(e)}")