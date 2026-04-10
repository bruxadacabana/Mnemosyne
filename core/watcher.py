"""
Monitoramento em tempo real da pasta de documentos via QFileSystemWatcher.
"""
from __future__ import annotations

import os

from PySide6.QtCore import QFileSystemWatcher, QObject, Signal


_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


class FolderWatcher(QObject):
    """
    Monitora uma pasta e seus subdiretórios em tempo real.
    Emite `file_added` quando um arquivo suportado é detectado pela primeira vez.
    """

    file_added = Signal(str)  # path absoluto do arquivo novo

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_directory_changed)
        self._known_files: set[str] = set()
        self._watched_root: str = ""

    def watch(self, directory: str) -> None:
        """Inicia o monitoramento de `directory` e seus subdiretórios."""
        self.stop()
        if not os.path.isdir(directory):
            return

        self._watched_root = directory
        dirs_to_watch: list[str] = []

        for root, dirs, files in os.walk(directory):
            # Ignorar diretório interno do Mnemosyne
            dirs[:] = [d for d in dirs if d != ".mnemosyne"]
            dirs_to_watch.append(root)
            for filename in files:
                _, ext = os.path.splitext(filename.lower())
                if ext in _SUPPORTED_EXTENSIONS:
                    self._known_files.add(os.path.join(root, filename))

        if dirs_to_watch:
            self._watcher.addPaths(dirs_to_watch)

    def stop(self) -> None:
        """Para o monitoramento e limpa o estado interno."""
        paths = self._watcher.directories() + self._watcher.files()
        if paths:
            self._watcher.removePaths(paths)
        self._known_files.clear()
        self._watched_root = ""

    @property
    def is_active(self) -> bool:
        return bool(self._watched_root)

    def _on_directory_changed(self, path: str) -> None:
        """Chamado pelo Qt quando um diretório monitorado muda."""
        try:
            entries = os.listdir(path)
        except OSError:
            return

        for filename in entries:
            _, ext = os.path.splitext(filename.lower())
            if ext not in _SUPPORTED_EXTENSIONS:
                continue
            full_path = os.path.join(path, filename)
            if full_path not in self._known_files and os.path.isfile(full_path):
                self._known_files.add(full_path)
                self.file_added.emit(full_path)

        # Registrar subdiretórios novos para monitoramento
        for filename in entries:
            full_path = os.path.join(path, filename)
            if (
                os.path.isdir(full_path)
                and filename != ".mnemosyne"
                and full_path not in self._watcher.directories()
            ):
                self._watcher.addPath(full_path)
