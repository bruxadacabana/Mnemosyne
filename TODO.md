# Mnemosyne — TODO de Desenvolvimento

## Padrões obrigatórios (não negociáveis)

- **Tratamento de erros com tipagem é prioridade absoluta.**
  Python: nunca `except Exception` sem re-tipar. Retornar `T | None` ou usar exceções específicas.
  Nenhum item está "pronto" se o caminho de erro não for tratado com o mesmo cuidado que o caminho feliz.

- **Manter este TODO atualizado.**
  Acrescentar aqui ANTES de implementar qualquer coisa que não conste.
  Marcar como `[x]` imediatamente ao terminar cada item.

- **Commit após cada item individual do TODO.**
  Ao marcar um item como `[x]`, fazer commit com mensagem clara.

- **Nunca passar de fase sem aprovação explícita.**
  Ao terminar todos os itens de uma fase, perguntar antes de começar a próxima.

---

## Fase 1 — Qualidade e robustez

- [x] `core/errors.py` — hierarquia de exceções tipadas
- [x] `TODO.md` — este arquivo criado com todas as fases
- [ ] `core/config.py` + `config.json` — sistema de configuração (modelos, pasta)
- [ ] `core/ollama_client.py` — detecção dinâmica de modelos disponíveis no Ollama
- [ ] `core/loaders.py` — suporte a `.md` + erros tipados (sem `except Exception` genérico)
- [ ] `core/indexer.py` — recebe `AppConfig`, erros tipados
- [ ] `core/rag.py` — recebe `AppConfig`, retorna `AskResult` tipado
- [ ] `core/summarizer.py` — recebe `AppConfig`, erros tipados
- [ ] `core/__init__.py` — re-exportar todos os novos tipos
- [ ] `gui/workers.py` — `OllamaCheckWorker` + workers com erros específicos
- [ ] `gui/main_window.py` — seleção de modelo, pasta via diálogo, verificação Ollama
- [ ] `requirements.txt` — version pinning + dependências novas
- [ ] `README.md` — corrigir modelo (qwen3.5:9b, não llama3.2)

## Fase 2 — Gerenciamento de Contexto Pessoal (PCM)

- [x] `core/memory.py` — `SessionMemory` (histórico de queries) + `CollectionIndex` *(criado na Fase 1 por ser dependência direta de main_window.py)*
- [ ] `core/tracker.py` — rastreamento de hashes SHA-256 para indexação incremental
- [ ] `core/rag.py` — hybrid retrieval (semântico + BM25 via rank-bm25)
- [ ] `gui/main_window.py` — integrar SessionMemory (aviso de query similar)

## Fase 3 — Features e watcher

- [ ] `core/watcher.py` — `FolderWatcher` via `QFileSystemWatcher`, auto-indexação
- [ ] `core/indexer.py` — `index_single_file()` + `update_vectorstore()` incremental
- [ ] `gui/main_window.py` — tab Gerenciar completo, status do watcher, log de eventos
- [ ] `gui/styles.qss` — fontes do ecossistema (IM Fell English, Special Elite, Courier Prime)

## Fase 4 — UI e design

- [ ] `gui/styles.qss` — visual rico: inputs estilo ficha de biblioteca, cards de resultado
- [ ] `gui/main_window.py` — exibição de fontes com trecho, indicador de relevância

---

*Atualizado em: 2026-04-09*
