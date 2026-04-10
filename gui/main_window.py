# Janela principal do Mnemosyne
from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.config import AppConfig, load_config, save_config
from core.errors import ConfigError, VectorstoreNotFoundError
from core.indexer import load_vectorstore
from core.memory import SessionMemory
from core.ollama_client import OllamaModel, filter_chat_models, filter_embed_models
from gui.workers import (
    AskWorker,
    IndexFileWorker,
    IndexWorker,
    OllamaCheckWorker,
    SummarizeWorker,
)


class SetupDialog(QDialog):
    """Diálogo de configuração — seleção de pasta, modelo LLM e embedding."""

    def __init__(
        self,
        models: list[OllamaModel],
        current: AppConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuração do Mnemosyne")
        self.setMinimumWidth(540)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Configure o Mnemosyne.\n"
                "As configurações são salvas em config.json."
            )
        )

        form = QFormLayout()

        # Pasta monitorada
        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(current.watched_dir)
        self.folder_edit.setPlaceholderText("Selecione a pasta com seus documentos…")
        folder_btn = QPushButton("Escolher…")
        folder_btn.clicked.connect(self._pick_folder)
        folder_row.addWidget(self.folder_edit)
        folder_row.addWidget(folder_btn)
        form.addRow("Pasta monitorada:", folder_row)

        chat_models = filter_chat_models(models)
        embed_models = filter_embed_models(models)

        # Modelo LLM
        self.llm_combo = QComboBox()
        for m in chat_models:
            self.llm_combo.addItem(m.name)
        if not chat_models:
            self.llm_combo.addItem("(nenhum modelo de chat encontrado)")
        if current.llm_model:
            idx = self.llm_combo.findText(current.llm_model)
            if idx >= 0:
                self.llm_combo.setCurrentIndex(idx)
        form.addRow("Modelo LLM:", self.llm_combo)

        # Modelo embedding
        self.embed_combo = QComboBox()
        for m in embed_models:
            self.embed_combo.addItem(m.name)
        if not embed_models:
            self.embed_combo.addItem("(nenhum modelo de embedding encontrado)")
        if current.embed_model:
            idx = self.embed_combo.findText(current.embed_model)
            if idx >= 0:
                self.embed_combo.setCurrentIndex(idx)
        form.addRow("Modelo de embedding:", self.embed_combo)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Selecionar pasta de documentos"
        )
        if folder:
            self.folder_edit.setText(folder)

    def get_values(self) -> tuple[str, str, str]:
        """Retorna (watched_dir, llm_model, embed_model)."""
        return (
            self.folder_edit.text().strip(),
            self.llm_combo.currentText(),
            self.embed_combo.currentText(),
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Mnemosyne — Seu Bibliotecário Celeste")
        self.setMinimumSize(900, 650)

        self.vectorstore = None
        self._available_models: list[OllamaModel] = []
        self._session_memory = SessionMemory()

        try:
            self.config = load_config()
        except ConfigError as exc:
            QMessageBox.critical(None, "Erro de configuração", str(exc))
            self.config = AppConfig(
                llm_model="",
                embed_model="",
                chunk_size=800,
                chunk_overlap=100,
                retriever_k=4,
                watched_dir="",
                auto_index_on_change=True,
            )

        self._build_ui()
        self.apply_style()
        self._start_ollama_check()

    # ── Construção da UI ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(6)

        # Banner Ollama indisponível
        self.ollama_banner = QLabel(
            "⚠  Ollama não encontrado. Inicie o Ollama para usar o Mnemosyne."
        )
        self.ollama_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ollama_banner.setStyleSheet(
            "background:#C9A87C; color:#1E2A3E; padding:6px; font-weight:bold;"
        )
        self.ollama_banner.setVisible(False)
        root.addWidget(self.ollama_banner)

        # Barra superior
        top = QHBoxLayout()
        self.folder_label = QLabel(self.config.watched_dir or "Pasta não configurada")
        self.folder_label.setStyleSheet("color:#4A4A4A; font-style:italic;")

        self.config_btn = QPushButton("Configurar")
        self.config_btn.setEnabled(False)
        self.config_btn.clicked.connect(self.open_config)

        self.index_btn = QPushButton("Indexar tudo")
        self.index_btn.setEnabled(False)
        self.index_btn.clicked.connect(self.start_indexing)

        self.progress = QProgressBar()
        self.progress.setVisible(False)

        top.addWidget(QLabel("Pasta:"))
        top.addWidget(self.folder_label, 1)
        top.addWidget(self.config_btn)
        top.addWidget(self.index_btn)
        top.addWidget(self.progress)
        root.addLayout(top)

        # Abas
        self.tabs = QTabWidget()
        self._build_tab_ask()
        self._build_tab_summary()
        self._build_tab_manage()
        root.addWidget(self.tabs)

    def _build_tab_ask(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        q_row = QHBoxLayout()
        self.question_edit = QLineEdit()
        self.question_edit.setPlaceholderText("Pergunte à sua memória…")
        self.question_edit.returnPressed.connect(self.ask_question)
        self.ask_btn = QPushButton("Perguntar")
        self.ask_btn.setEnabled(False)
        self.ask_btn.clicked.connect(self.ask_question)
        q_row.addWidget(self.question_edit)
        q_row.addWidget(self.ask_btn)
        layout.addLayout(q_row)

        self.similar_label = QLabel()
        self.similar_label.setVisible(False)
        self.similar_label.setStyleSheet("color:#C9A87C; font-style:italic; padding:4px;")
        layout.addWidget(self.similar_label)

        layout.addWidget(QLabel("Resposta:"))
        self.answer_text = QTextEdit()
        self.answer_text.setReadOnly(True)
        self.answer_text.setPlaceholderText("A resposta aparecerá aqui…")
        layout.addWidget(self.answer_text)

        layout.addWidget(QLabel("Fontes:"))
        self.sources_text = QTextEdit()
        self.sources_text.setReadOnly(True)
        self.sources_text.setMaximumHeight(80)
        layout.addWidget(self.sources_text)

        self.tabs.addTab(tab, "Perguntar")

    def _build_tab_summary(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.summary_btn = QPushButton("Gerar resumo geral")
        self.summary_btn.setEnabled(False)
        self.summary_btn.clicked.connect(self.summarize)
        layout.addWidget(self.summary_btn)
        layout.addWidget(QLabel("Resumo:"))
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)
        self.tabs.addTab(tab, "Resumir")

    def _build_tab_manage(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        info = QGroupBox("Pasta monitorada")
        info_form = QFormLayout(info)
        self.manage_path_label = QLabel(self.config.watched_dir or "—")
        self.manage_path_label.setWordWrap(True)
        self.manage_watcher_label = QLabel("Inativo")
        self.manage_files_label = QLabel("—")
        self.manage_types_label = QLabel("—")
        self.manage_date_label = QLabel("—")
        info_form.addRow("Caminho:", self.manage_path_label)
        info_form.addRow("Watcher:", self.manage_watcher_label)
        info_form.addRow("Arquivos indexados:", self.manage_files_label)
        info_form.addRow("Tipos:", self.manage_types_label)
        info_form.addRow("Última indexação:", self.manage_date_label)
        layout.addWidget(info)

        actions = QHBoxLayout()
        self.refresh_manage_btn = QPushButton("Atualizar informações")
        self.refresh_manage_btn.clicked.connect(self.refresh_manage_info)
        self.clear_index_btn = QPushButton("Remover índice")
        self.clear_index_btn.setEnabled(False)
        self.clear_index_btn.clicked.connect(self.clear_index)
        actions.addWidget(self.refresh_manage_btn)
        actions.addWidget(self.clear_index_btn)
        layout.addLayout(actions)

        layout.addWidget(QLabel("Log de eventos:"))
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        layout.addWidget(self.event_log)

        self.tabs.addTab(tab, "Gerenciar")

    # ── Inicialização Ollama ──────────────────────────────────────────────────

    def _start_ollama_check(self) -> None:
        self.statusBar().showMessage("Verificando Ollama…")
        self._ollama_worker = OllamaCheckWorker()
        self._ollama_worker.models_loaded.connect(self._on_models_loaded)
        self._ollama_worker.ollama_unavailable.connect(self._on_ollama_unavailable)
        self._ollama_worker.start()

    def _on_models_loaded(self, models: list) -> None:
        self._available_models = models
        self.config_btn.setEnabled(True)
        self.statusBar().showMessage(
            f"Ollama ativo — {len(models)} modelo(s) disponível(is)."
        )
        if not self.config.is_configured:
            self._show_setup_dialog()
        else:
            self._post_config_init()

    def _on_ollama_unavailable(self, message: str) -> None:
        self.ollama_banner.setVisible(True)
        self.config_btn.setEnabled(True)
        self.statusBar().showMessage("Ollama indisponível.")
        self._log_event(f"Ollama indisponível: {message}")

    # ── Configuração ─────────────────────────────────────────────────────────

    def _show_setup_dialog(self) -> None:
        dialog = SetupDialog(self._available_models, self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            folder, llm, embed = dialog.get_values()
            if not folder:
                QMessageBox.warning(self, "Aviso", "Selecione uma pasta para continuar.")
                return
            self.config.watched_dir = folder
            self.config.llm_model = llm
            self.config.embed_model = embed
            save_config(self.config)
            self._post_config_init()
        else:
            self.statusBar().showMessage("Configuração cancelada.")

    def open_config(self) -> None:
        dialog = SetupDialog(self._available_models, self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            folder, llm, embed = dialog.get_values()
            if not folder:
                return
            changed_dir = folder != self.config.watched_dir
            self.config.watched_dir = folder
            self.config.llm_model = llm
            self.config.embed_model = embed
            save_config(self.config)
            self.folder_label.setText(folder)
            self.manage_path_label.setText(folder)
            if changed_dir:
                self.vectorstore = None
                self._disable_query_buttons()
            self._log_event("Configuração atualizada.")
            self._post_config_init()

    def _post_config_init(self) -> None:
        """Chamado após configuração válida estar disponível."""
        self.folder_label.setText(self.config.watched_dir)
        self.manage_path_label.setText(self.config.watched_dir)

        try:
            self.vectorstore = load_vectorstore(self.config)
            self._enable_query_buttons()
            self.statusBar().showMessage("Memória carregada.")
            self._log_event("Vectorstore carregado com sucesso.")
        except VectorstoreNotFoundError:
            self.statusBar().showMessage(
                "Nenhum índice encontrado. Use 'Indexar tudo'."
            )
            self._log_event("Nenhum índice encontrado — use 'Indexar tudo'.")

        self.index_btn.setEnabled(True)
        self.refresh_manage_info()

        if self.config.auto_index_on_change:
            self._start_watcher()

    # ── Watcher ───────────────────────────────────────────────────────────────

    def _start_watcher(self) -> None:
        from core.watcher import FolderWatcher

        if hasattr(self, "_watcher") and self._watcher is not None:
            self._watcher.stop()

        self._watcher = FolderWatcher(self)
        self._watcher.file_added.connect(self._on_file_added)
        self._watcher.watch(self.config.watched_dir)
        self._update_watcher_label()
        self._log_event(f"Watcher ativo em: {self.config.watched_dir}")

    def _update_watcher_label(self) -> None:
        watcher = getattr(self, "_watcher", None)
        if watcher and watcher.is_active:
            self.manage_watcher_label.setText("✔ Ativo")
            self.manage_watcher_label.setStyleSheet("color:#2E7D32; font-weight:bold;")
        else:
            self.manage_watcher_label.setText("Inativo")
            self.manage_watcher_label.setStyleSheet("color:#4A4A4A;")

    def _on_file_added(self, file_path: str) -> None:
        name = os.path.basename(file_path)
        self.statusBar().showMessage(f"Novo arquivo: {name} — indexando…")
        self._log_event(f"Novo arquivo detectado: {name}")

        self._file_worker = IndexFileWorker(file_path, self.config)
        self._file_worker.finished.connect(self._on_file_indexed)
        self._file_worker.start()

    def _on_file_indexed(self, success: bool, message: str) -> None:
        self._log_event(message)
        if success:
            try:
                self.vectorstore = load_vectorstore(self.config)
                self._enable_query_buttons()
                self.refresh_manage_info()
            except VectorstoreNotFoundError:
                pass
        self.statusBar().showMessage(message)

    # ── Indexação ─────────────────────────────────────────────────────────────

    def start_indexing(self) -> None:
        if not self.config.watched_dir or not os.path.isdir(self.config.watched_dir):
            QMessageBox.warning(
                self, "Aviso", "Pasta monitorada inválida. Configure primeiro."
            )
            return

        self.index_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.statusBar().showMessage("Indexando documentos…")
        self._log_event(f"Iniciando indexação de: {self.config.watched_dir}")

        self._index_worker = IndexWorker(self.config)
        self._index_worker.finished.connect(self._on_index_finished)
        self._index_worker.start()

    def _on_index_finished(self, success: bool, message: str) -> None:
        self.index_btn.setEnabled(True)
        self.progress.setVisible(False)
        self._log_event(message)

        if success:
            try:
                self.vectorstore = load_vectorstore(self.config)
                self._enable_query_buttons()
                self.refresh_manage_info()
            except VectorstoreNotFoundError as exc:
                QMessageBox.critical(self, "Erro", str(exc))
        else:
            QMessageBox.critical(self, "Erro na indexação", message)

        self.statusBar().showMessage(message)

    # ── Consulta ──────────────────────────────────────────────────────────────

    def ask_question(self) -> None:
        if self.vectorstore is None:
            QMessageBox.warning(
                self, "Aviso", "Nenhuma memória indexada. Indexe primeiro."
            )
            return
        question = self.question_edit.text().strip()
        if not question:
            return

        similar = self._session_memory.find_similar(question)
        if similar:
            preview = similar.question[:60]
            self.similar_label.setText(f'Pergunta similar encontrada: "{preview}…"')
            self.similar_label.setVisible(True)
        else:
            self.similar_label.setVisible(False)

        self.ask_btn.setEnabled(False)
        self.answer_text.setPlainText("Pensando…")
        self.sources_text.clear()
        self.statusBar().showMessage("Consultando Mnemosyne…")

        self._ask_worker = AskWorker(self.vectorstore, question, self.config)
        self._ask_worker.finished.connect(self._on_answer)
        self._ask_worker.start()

    def _on_answer(self, success: bool, text: str, sources: list) -> None:
        if success:
            self.answer_text.setPlainText(text)
            self._session_memory.save_query(
                self.question_edit.text().strip(), text, sources
            )
            if sources:
                lines = [f"• {os.path.basename(s)}" for s in sources]
                self.sources_text.setPlainText("\n".join(lines))
            else:
                self.sources_text.setPlainText("(nenhuma fonte identificada)")
        else:
            self.answer_text.setPlainText(f"Erro: {text}")
            self.sources_text.clear()

        self.ask_btn.setEnabled(True)
        self.statusBar().showMessage("Pronto.")

    # ── Resumo ────────────────────────────────────────────────────────────────

    def summarize(self) -> None:
        if self.vectorstore is None:
            QMessageBox.warning(
                self, "Aviso", "Nenhuma memória indexada. Indexe primeiro."
            )
            return
        self.summary_btn.setEnabled(False)
        self.summary_text.setPlainText("Gerando resumo…")
        self.statusBar().showMessage("Sintetizando documentos…")

        self._summary_worker = SummarizeWorker(self.vectorstore, self.config)
        self._summary_worker.finished.connect(self._on_summary)
        self._summary_worker.start()

    def _on_summary(self, success: bool, text: str) -> None:
        self.summary_text.setPlainText(text)
        self.summary_btn.setEnabled(True)
        self.statusBar().showMessage("Pronto.")

    # ── Tab Gerenciar ─────────────────────────────────────────────────────────

    def refresh_manage_info(self) -> None:
        if not self.config.persist_dir:
            return

        from collections import Counter
        import os

        # Inspecionar arquivos no watched_dir (sem depender do vectorstore)
        if self.config.watched_dir and os.path.isdir(self.config.watched_dir):
            supported = {".pdf", ".docx", ".txt", ".md"}
            count = 0
            types: Counter = Counter()
            for root, dirs, files in os.walk(self.config.watched_dir):
                dirs[:] = [d for d in dirs if d != ".mnemosyne"]
                for f in files:
                    _, ext = os.path.splitext(f.lower())
                    if ext in supported:
                        count += 1
                        types[ext] += 1

            self.manage_files_label.setText(
                f"{count} arquivo(s) na pasta"
                + (" (indexados)" if self.vectorstore else " (não indexados)")
            )
            if types:
                self.manage_types_label.setText(
                    "  ".join(f"{ext}: {n}" for ext, n in sorted(types.items()))
                )
            else:
                self.manage_types_label.setText("—")
        else:
            self.manage_files_label.setText("—")
            self.manage_types_label.setText("—")

        self.clear_index_btn.setEnabled(
            bool(self.config.persist_dir and os.path.exists(self.config.persist_dir))
        )
        self._update_watcher_label()

    def clear_index(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "Remover o índice apagará todos os dados do vectorstore.\nDeseja continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        import shutil

        persist_dir = self.config.persist_dir
        if persist_dir and os.path.exists(persist_dir):
            try:
                shutil.rmtree(persist_dir)
                self.vectorstore = None
                self._disable_query_buttons()
                self.clear_index_btn.setEnabled(False)
                self._log_event("Índice removido.")
                self.refresh_manage_info()
                self.statusBar().showMessage("Índice removido.")
            except OSError as exc:
                QMessageBox.critical(
                    self, "Erro", f"Não foi possível remover o índice: {exc}"
                )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _enable_query_buttons(self) -> None:
        self.ask_btn.setEnabled(True)
        self.summary_btn.setEnabled(True)
        self.clear_index_btn.setEnabled(True)

    def _disable_query_buttons(self) -> None:
        self.ask_btn.setEnabled(False)
        self.summary_btn.setEnabled(False)

    def _log_event(self, message: str) -> None:
        from datetime import datetime

        ts = datetime.now().strftime("%H:%M:%S")
        self.event_log.append(f"[{ts}] {message}")

    def apply_style(self) -> None:
        style_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(style_path):
            with open(style_path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        else:
            self.setStyleSheet(
                """
                QMainWindow { background-color: #FDF8F0; }
                QLabel { color: #4A4A4A; }
                QPushButton {
                    background-color: #D4C4B0;
                    border: 1px solid #C9A87C;
                    padding: 5px 12px;
                    border-radius: 3px;
                }
                QPushButton:hover { background-color: #C9A87C; }
                QPushButton:disabled { background-color: #EDE8E0; color: #9A9A9A; }
                QLineEdit, QTextEdit {
                    background-color: white;
                    border: 1px solid #D4C4B0;
                    border-radius: 2px;
                    padding: 2px;
                }
                QTabWidget::pane { border: 1px solid #D4C4B0; }
                QTabBar::tab { background-color: #F0E8DC; padding: 8px 16px; }
                QTabBar::tab:selected {
                    background-color: #FDF8F0;
                    border-bottom: 2px solid #C9A87C;
                }
                QGroupBox {
                    border: 1px solid #D4C4B0;
                    border-radius: 4px;
                    margin-top: 8px;
                    padding: 8px;
                }
                QGroupBox::title { color: #1E2A3E; font-weight: bold; }
                """
            )


def run() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
