# 📖 Mnemosyne — Seu Bibliotecário Celeste

> *Guardião silencioso dos seus arquivos, onde a memória encontra o cosmos.*

Mnemosyne é um assistente de aprendizado local que organiza, resume e responde perguntas sobre seus documentos pessoais. Totalmente offline, ele usa RAG (Retrieval-Augmented Generation) com modelos locais via Ollama para transformar sua pasta de arquivos em uma biblioteca inteligente.

## 🌌 Por que Mnemosyne?

Na mitologia grega, **Mnemosyne** é a Titã da memória e mãe das musas. Seu nome significa "memória" e ela representa a fonte de todo conhecimento. Este programa leva seu nome para simbolizar a preservação e recuperação da sua informação pessoal, de forma ordenada e eterna.

Mnemosyne completa a tríade de ferramentas que desenvolvo:

- **OGMA** — gerenciador de projetos, estudos e leitura (a palavra em ação)
- **KOSMOS** — gerenciador de notícias (a ordem do mundo)
- **MNEMOSYNE** — assistente de arquivos locais (a memória pessoal)

Juntos, eles formam um ecossistema de conhecimento: o que você faz, o que acontece lá fora e o que você guarda.

---

## ✨ Funcionalidades

- **Indexação de documentos** — lê arquivos de uma pasta (e subpastas) e cria um índice vetorial local.
- **Respostas baseadas em RAG** — faça perguntas e receba respostas fundamentadas nos seus documentos.
- **Resumos automáticos** — gere resumos de um documento ou de toda a sua coleção.
- **Interface gráfica nativa** — construída com PySide6 (Qt), sem necessidade de navegador.
- **Totalmente offline** — após baixar os modelos, todos os dados permanecem no seu computador.
- **Multi‑formato** — suporte a `.txt`, `.pdf`, `.docx` (fácil expansão para outros).

---

## 🎨 Estética e Filosofia de Design

Mnemosyne foi projetada para ser uma experiência visual que une o acolhedor de uma biblioteca antiga com o infinito do cosmos.

- **Paleta de cores**:
  - Off‑white (`#FDF8F0`) como base, evocando papel envelhecido.
  - Marrom‑sépia (`#D4C4B0`) e ouro queimado (`#C9A87C`) para detalhes.
  - Azul‑meia‑noite (`#1E2A3E`) para elementos de destaque, como o céu estrelado.
- **Tipografia**:
  - Títulos em *Playfair Display* (serifada elegante, remetendo a livros antigos).
  - Corpo e respostas em *Cormorant Garamond* ou *Courier Prime* (estilo máquina de escrever).
- **Elementos visuais**:
  - Fundo com textura sutil de papel envelhecido.
  - Constelações discretas aparecem em cantos ou como sublinhados.
  - Botões com bordas de "fita datilográfica" e ícones dourados.
  - Animações suaves durante indexação e recuperação (estrelas cadentes, espirais de luz).
- **Metáfora central**: **"O Arquivo Celeste"** — um fichário infinito onde cada documento é uma estrela, e a busca traça constelações entre eles.

Essa identidade visual dialoga com OGMA e KOSMOS, mas dá a Mnemosyne uma personalidade própria: a guardiã silenciosa e organizada, entre o bibliotecário antiquário e o astrônomo místico.

---

## 📦 Requisitos

- **Python 3.9 ou superior**
- **Ollama** instalado e em execução (https://ollama.com/)
- Modelos baixados no Ollama:
  ```bash
  ollama pull llama3.2
  ollama pull nomic-embed-text
  ```
- **Dependências Python** (listadas no `requirements.txt`):
  - PySide6
  - langchain, langchain-community
  - chromadb
  - pypdf, python-docx
  - tiktoken

---

## 🚀 Instalação

1. **Clone ou crie o projeto**:

```bash
git clone https://github.com/seu-usuario/mnemosyne.git
cd mnemosyne
```

2. **Crie e ative um ambiente virtual**:

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

3. **Instale as dependências**:

```bash
pip install -r requirements.txt
```

4. **Certifique‑se de que o Ollama está rodando**:

```bash
ollama serve
```

---

## ▶️ Como usar

1. **Coloque seus documentos** em uma pasta (ex.: `./meus_docs`). Formatos suportados: `.txt`, `.pdf`, `.docx`.

2. **Execute o programa**:

```bash
python main.py
```

3. **Na interface**:
   - No campo superior, informe o caminho da pasta com seus documentos.
   - Clique em **Indexar documentos** e aguarde. O índice será criado na pasta `./chroma_db`.
   - Após a indexação, vá para a aba **Perguntar** e digite sua pergunta.
   - Na aba **Resumir**, clique em **Gerar resumo geral** para obter uma síntese de todos os documentos.
   - A aba **Gerenciar** mostra os arquivos da pasta selecionada.

---

## 🧩 Estrutura do Projeto

```
mnemosyne/
├── main.py                 # ponto de entrada
├── gui/
│   ├── __init__.py
│   ├── main_window.py      # janela principal
│   ├── workers.py          # threads para tarefas demoradas
│   └── styles.qss          # folha de estilo (opcional)
├── core/
│   ├── __init__.py
│   ├── indexer.py          # criação/carga do vectorstore
│   ├── loaders.py          # carregadores de documentos
│   ├── rag.py              # cadeia de QA
│   └── summarizer.py       # funções de resumo
├── requirements.txt
├── README.md
└── chroma_db/              # banco vetorial persistente (criado após indexação)
```

---

## ⚙️ Personalização

### Modelos do Ollama

Você pode alterar os modelos nos arquivos `core/indexer.py` e `core/rag.py`. Por exemplo, para usar `mistral` em vez de `llama3.2`:

```python
embeddings = OllamaEmbeddings(model="nomic-embed-text")  # embedding pode permanecer
llm = Ollama(model="mistral", temperature=0.2)
```

### Estilo visual

Edite `gui/styles.qss` para modificar cores, fontes e outros aspectos. Para adicionar uma imagem de fundo com constelações, você pode usar:

```css
QMainWindow {
    background-image: url(:/images/constellations.png);
    background-repeat: no-repeat;
    background-position: bottom right;
}
```

(É necessário adicionar o arquivo de recurso no Qt.)

---

## 🛠️ Solução de problemas

- **"Ollama não está rodando"**  
  Inicie o servidor com `ollama serve` em um terminal separado.

- **Erro ao indexar / perguntar**  
  Verifique se os modelos foram baixados (`ollama list`). Se não, execute `ollama pull llama3.2` e `ollama pull nomic-embed-text`.

- **A interface fica congelada**  
  As operações demoradas rodam em threads separadas. Se mesmo assim travar, pode ser um problema de recursos. Tente reduzir o `chunk_size` ou o número de documentos.

- **Arquivos não são carregados**  
  Confira se estão em um dos formatos suportados e se o caminho da pasta está correto. Para outros formatos, é necessário estender `loaders.py`.

---

## 🤝 Contribuições

Sugestões e melhorias são bem‑vindas! Abra uma issue ou envie um pull request. Áreas que podem ser expandidas:

- Suporte a mais formatos (`.epub`, `.md`, `.xlsx`, imagens com OCR).
- Atualização incremental do índice (monitoramento de pasta).
- Seleção de modelos na interface.
- Exportação de resumos e conversas.

---

## 📜 Licença

Este projeto está sob a licença MIT. Sinta‑se livre para usar, modificar e distribuir.

---

## 🌠 Créditos

- Ícones e design inspirados em **papel envelhecido** e **mapas estelares antigos**.
- Construído com [PySide6](https://doc.qt.io/qtforpython-6/), [LangChain](https://www.langchain.com/) e [Ollama](https://ollama.com/).

---

*Que sua memória seja tão vasta quanto o céu.*