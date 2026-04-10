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
- [x] `core/config.py` + `config.json` — sistema de configuração (modelos, pasta)
- [x] `core/ollama_client.py` — detecção dinâmica de modelos disponíveis no Ollama
- [x] `core/loaders.py` — suporte a `.md` + erros tipados (sem `except Exception` genérico)
- [x] `core/indexer.py` — recebe `AppConfig`, erros tipados, `index_single_file()`
- [x] `core/rag.py` — recebe `AppConfig`, retorna `AskResult` tipado
- [x] `core/summarizer.py` — recebe `AppConfig`, erros tipados
- [x] `core/__init__.py` — re-exportar todos os novos tipos
- [x] `gui/workers.py` — `OllamaCheckWorker`, `IndexFileWorker`, erros específicos
- [x] `gui/main_window.py` — seleção de modelo, pasta via diálogo, verificação Ollama
- [x] `requirements.txt` — version pinning + dependências novas (langchain-ollama, rank-bm25)
- [x] `README.md` — corrigir modelo (qwen3.5:9b, não llama3.2)

## Fase 2 — Gerenciamento de Contexto Pessoal (PCM)

- [x] `core/memory.py` — `SessionMemory` + `CollectionIndex` *(criado na Fase 1 — dependência de main_window.py)*
- [x] `core/watcher.py` — `FolderWatcher` via `QFileSystemWatcher` *(criado na Fase 1 — dependência de main_window.py)*
- [ ] `core/tracker.py` — rastreamento de hashes SHA-256 para indexação incremental
- [ ] `core/rag.py` — hybrid retrieval (semântico + BM25 via rank-bm25)
- [ ] `gui/main_window.py` — expor controle do watcher na UI (Fase 2 refinamentos)
- [ ] `core/watcher.py` — detectar remoção e renomeação de arquivos (emitir signal `file_removed`)
- [ ] `gui/main_window.py` — integrar `CollectionIndex` na UI: preencher "Última indexação" e metadata reais no tab Gerenciar
- [ ] `gui/main_window.py` — retry automático de conexão ao Ollama sem reiniciar o app
- [ ] **Suporte ao vault do Obsidian** — vectorstore único com metadata `source_type: "biblioteca" | "vault"`
  - `config.json`: campo `vault_dir` opcional
  - `core/loaders.py`: adicionar `source_type` ao metadata de cada chunk
  - `core/indexer.py`: aceitar múltiplas fontes com tipos distintos, watchers independentes
  - `core/rag.py`: parâmetro de filtro por `source_type` via ChromaDB `where`
  - `gui/main_window.py`: segundo picker de pasta na SetupDialog + seletor "Buscar em: Biblioteca / Vault / Ambos"

## Fase 3 — Features core

- [ ] `core/indexer.py` — `update_vectorstore()` incremental completo usando tracker
- [ ] `core/indexer.py` — remover chunks de arquivos deletados ou renomeados ao atualizar vectorstore (depende de tracker + signal `file_removed`)
- [ ] `gui/main_window.py` — botão "Atualizar índice" (incremental) no tab Gerenciar
- [ ] `core/summarizer.py` — substituir query fixa por múltiplas queries temáticas ou MMR para cobrir melhor coleções grandes

## Fase 4 — Inspirado no NotebookLM

### 4.1 Citação aprimorada
- [ ] `core/rag.py` — retornar trecho exato do chunk junto com o nome do arquivo (não só o path)
- [ ] `gui/main_window.py` — exibir fontes com trecho visível, não só nome do arquivo
- [ ] `gui/main_window.py` — indicador de relevância por fonte (similaridade do chunk)

### 4.2 Seleção de fontes por consulta
- [ ] `gui/main_window.py` — listar arquivos indexados com checkboxes; query respeita seleção
- [ ] `core/rag.py` — suporte a filtro por lista de arquivos via ChromaDB `where` metadata

### 4.3 Notebook Guide automático
- [ ] `core/guide.py` — ao terminar indexação, gerar automaticamente:
  - Resumo geral da coleção
  - 5 perguntas sugeridas sobre o conteúdo
- [ ] `gui/main_window.py` — exibir Guide na aba Resumir ou em painel lateral

### 4.4 FAQ Generator
- [ ] `core/faq.py` — gerar lista de perguntas frequentes a partir dos documentos indexados
- [ ] `gui/main_window.py` — botão "Gerar FAQ" na aba Resumir

### 4.5 Flashcards e Quiz
- [ ] `core/flashcards.py` — extrair termos-chave, datas e conceitos e formatar como flashcards (frente/verso)
- [ ] `core/quiz.py` — gerar perguntas de múltipla escolha com gabarito a partir dos documentos
- [ ] `gui/main_window.py` — nova aba "Estudar" com modo Flashcard e modo Quiz

### 4.6 Modos de consulta configuráveis
- [ ] `core/rag.py` — suporte a múltiplos modos de prompt:
  - `"resposta"` (padrão atual — responde diretamente)
  - `"socrático"` (Learning Guide — faz perguntas antes de revelar a resposta)
  - `"resumido"` (resposta curta e direta)
- [ ] `gui/main_window.py` — seletor de modo visível na aba Perguntar

### 4.7 Timeline automática
- [ ] `core/timeline.py` — extrair eventos com data/período dos documentos e ordenar cronologicamente
- [ ] `gui/main_window.py` — botão "Gerar linha do tempo" na aba Resumir

### 4.8 Audio Overview (futuro — requer TTS local)
- [ ] Pesquisar opções de TTS offline (ex: Kokoro, Piper TTS)
- [ ] `core/audio.py` — gerar áudio de síntese a partir do resumo geral
- [ ] `gui/main_window.py` — botão "Ouvir resumo" com player embutido

## Fase 5 — UI e design

- [ ] `gui/styles.qss` — fontes do ecossistema (IM Fell English, Special Elite, Courier Prime)
- [ ] `gui/styles.qss` — visual rico: inputs estilo ficha de biblioteca, cards de resultado

---

*Atualizado em: 2026-04-10*
