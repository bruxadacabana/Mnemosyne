# Main window with tabs and widgets

import sys
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog,
    QMessageBox, QProgressBar, QApplication
)
from PySide6.QtCore import Qt, QThreadPool
from gui.workers import IndexWorker, AskWorker, SummarizeWorker
from core.indexer import load_vectorstore

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mnemosyne — Seu Bibliotecário Celeste")
        self.setMinimumSize(800, 600)
        self.vectorstore = None
        self.index_path = "./chroma_db"

        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Barra superior: caminho da pasta e botão indexar
        top_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Caminho da pasta com seus documentos")
        self.folder_edit.setText("./meus_docs")
        top_layout.addWidget(QLabel("Pasta:"))
        top_layout.addWidget(self.folder_edit)

        self.index_btn = QPushButton("Indexar documentos")
        self.index_btn.clicked.connect(self.start_indexing)
        top_layout.addWidget(self.index_btn)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        top_layout.addWidget(self.progress)

        layout.addLayout(top_layout)

        # Abas
        self.tabs = QTabWidget()
        self.tab_ask = QWidget()
        self.tab_summary = QWidget()
        self.tab_manage = QWidget()
        self.tabs.addTab(self.tab_ask, "Perguntar")
        self.tabs.addTab(self.tab_summary, "Resumir")
        self.tabs.addTab(self.tab_manage, "Gerenciar")
        layout.addWidget(self.tabs)

        # Aba Perguntar
        ask_layout = QVBoxLayout(self.tab_ask)
        self.question_edit = QLineEdit()
        self.question_edit.setPlaceholderText("Faça uma pergunta sobre seus documentos...")
        self.ask_btn = QPushButton("Perguntar")
        self.ask_btn.clicked.connect(self.ask_question)
        self.answer_text = QTextEdit()
        self.answer_text.setReadOnly(True)
        ask_layout.addWidget(self.question_edit)
        ask_layout.addWidget(self.ask_btn)
        ask_layout.addWidget(QLabel("Resposta:"))
        ask_layout.addWidget(self.answer_text)

        # Aba Resumir
        summary_layout = QVBoxLayout(self.tab_summary)
        self.summary_btn = QPushButton("Gerar resumo geral")
        self.summary_btn.clicked.connect(self.summarize)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        summary_layout.addWidget(self.summary_btn)
        summary_layout.addWidget(QLabel("Resumo:"))
        summary_layout.addWidget(self.summary_text)

        # Aba Gerenciar
        manage_layout = QVBoxLayout(self.tab_manage)
        self.files_list = QTextEdit()
        self.files_list.setReadOnly(True)
        self.refresh_btn = QPushButton("Atualizar lista")
        self.refresh_btn.clicked.connect(self.refresh_files)
        manage_layout.addWidget(self.refresh_btn)
        manage_layout.addWidget(self.files_list)

        # Carrega vectorstore se existir
        self.load_vectorstore()

        # Aplica estilo (opcional)
        self.apply_style()

    def apply_style(self):
        # Carrega um arquivo .qss se existir, senão usa um estilo simples
        style_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(style_path):
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
        else:
            # estilo básico off-white
            self.setStyleSheet("""
                QMainWindow { background-color: #FDF8F0; }
                QLabel { color: #4A4A4A; }
                QPushButton { background-color: #D4C4B0; border: 1px solid #C9A87C; padding: 5px; }
                QPushButton:hover { background-color: #C9A87C; }
                QLineEdit, QTextEdit { background-color: white; border: 1px solid #D4C4B0; }
                QTabWidget::pane { border: 1px solid #D4C4B0; }
                QTabBar::tab { background-color: #F0E8DC; padding: 8px; }
                QTabBar::tab:selected { background-color: #E8DDD0; }
            """)

    def load_vectorstore(self):
        if os.path.exists(self.index_path):
            try:
                self.vectorstore = load_vectorstore(self.index_path)
                self.statusBar().showMessage("Memória carregada.")
            except Exception as e:
                self.statusBar().showMessage(f"Erro ao carregar memória: {e}")

    def start_indexing(self):
        folder = self.folder_edit.text().strip()
        if not folder:
            QMessageBox.warning(self, "Aviso", "Informe o caminho da pasta.")
            return
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Aviso", "Pasta não encontrada.")
            return

        self.index_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # modo indeterminado
        self.statusBar().showMessage("Indexando documentos...")

        self.worker = IndexWorker(folder, self.index_path)
        self.worker.finished.connect(self.on_index_finished)
        self.worker.start()

    def on_index_finished(self, success, message):
        self.index_btn.setEnabled(True)
        self.progress.setVisible(False)
        if success:
            QMessageBox.information(self, "Sucesso", message)
            self.load_vectorstore()
        else:
            QMessageBox.critical(self, "Erro", message)
        self.statusBar().showMessage("Pronto.")

    def ask_question(self):
        if self.vectorstore is None:
            QMessageBox.warning(self, "Aviso", "Nenhuma memória indexada. Indexe primeiro.")
            return
        question = self.question_edit.text().strip()
        if not question:
            return
        self.ask_btn.setEnabled(False)
        self.answer_text.setPlainText("Pensando...")
        self.statusBar().showMessage("Consultando Mnemosyne...")

        self.ask_worker = AskWorker(self.vectorstore, question)
        self.ask_worker.finished.connect(self.on_answer)
        self.ask_worker.start()

    def on_answer(self, answer):
        self.answer_text.setPlainText(answer)
        self.ask_btn.setEnabled(True)
        self.statusBar().showMessage("Pronto.")

    def summarize(self):
        if self.vectorstore is None:
            QMessageBox.warning(self, "Aviso", "Nenhuma memória indexada. Indexe primeiro.")
            return
        self.summary_btn.setEnabled(False)
        self.summary_text.setPlainText("Gerando resumo...")
        self.statusBar().showMessage("Sintetizando documentos...")

        self.summary_worker = SummarizeWorker(self.vectorstore)
        self.summary_worker.finished.connect(self.on_summary)
        self.summary_worker.start()

    def on_summary(self, summary):
        self.summary_text.setPlainText(summary)
        self.summary_btn.setEnabled(True)
        self.statusBar().showMessage("Pronto.")

    def refresh_files(self):
        folder = self.folder_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            self.files_list.setPlainText("Pasta inválida ou não encontrada.")
            return
        try:
            files = os.listdir(folder)
            text = "\n".join(files)
            self.files_list.setPlainText(text)
        except Exception as e:
            self.files_list.setPlainText(f"Erro: {e}")

def run():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())