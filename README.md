# Agentic RAG System

An intelligent document Question-Answering system powered by AI agents that demonstrate multi-step reasoning, self-reflection, and adaptive retrieval strategies.

## 🎯 Features

- **Multi-Agent Architecture**: 6 specialized agents (Router, Planner, Retriever, Reranker, Synthesizer, Validator)
- **Multi-Format Support**: PDF, DOCX, PPT, Excel, and text files
- **Vector Database**: Milvus for scalable similarity search
- **Hybrid Retrieval**: Dense (vector) + Sparse (BM25) search
- **Self-Hosted LLM**: Powered by Ollama (local, private, free)
- **Agentic Workflows**: Query decomposition, self-correction, quality validation
- **Clean UI**: Minimalist Flask interface with real-time agent activity

## 🏗️ Architecture

```
User Query → Router Agent → [Simple] → Retriever → Reranker → Synthesizer → Validator → Response
                         ↓
                    [Complex] → Planner → Sub-queries → [continues as above]
```

## 📋 Prerequisites

- Python 3.9+
- Docker & Docker Compose (for Milvus)
- Ollama installed with models:
  - LLM model (e.g., `llama3`, `mistral`)
  - Embedding model (e.g., `nomic-embed-text`)

## 🚀 Quick Start

### 1. Install Ollama Models

```bash
# Install LLM
ollama pull llama3

# Install embedding model
ollama pull nomic-embed-text
```

### 2. Start Milvus

```bash
docker-compose up -d
```

### 3. Install Dependencies

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 4. Configure

Edit `config.yaml` to match your Ollama models:

```yaml
ollama:
  llm_model: "llama3"
  embedding_model: "nomic-embed-text"
```

### 5. Run Application

```bash
python app.py
```

Navigate to `http://localhost:5000`

## 📁 Project Structure

```
agentic-rag-system/
├── src/
│   ├── agents/          # Agentic workflow components
│   ├── database/        # Milvus & BM25 integration
│   ├── ingestion/       # Document loaders & chunking
│   ├── llm/            # Ollama client & prompts
│   ├── retrieval/      # Hybrid search strategies
│   └── utils/          # Helper functions
├── templates/          # Flask HTML templates
├── static/             # CSS & JavaScript
├── sample_data/        # Example documents
├── tests/              # Unit & integration tests
├── app.py              # Flask application
├── config.yaml         # Configuration
└── docker-compose.yml  # Milvus setup
```

## 🎮 Usage

1. **Upload Documents**: Drag & drop PDFs, Word docs, PowerPoints, Excel files
2. **Ask Questions**: Type your query in the chat interface
3. **Watch Agents Work**: See real-time reasoning steps in the activity panel
4. **Get Cited Answers**: Responses include source references

## 🧪 Running Tests

```bash
pytest tests/ -v
```

## 🔧 Advanced Configuration

See `config.yaml` for:
- Chunking parameters
- Retrieval hyperparameters
- Agent quality thresholds
- UI settings

## 📊 System Design

For detailed architecture explanation, see `docs/system_design.pdf`

## 🎥 Demo Video

[Link to demo video showing system in action]

## 🤝 Contributing

This is a demonstration project for showcasing agentic RAG capabilities.

## 📄 License

MIT

## 🙏 Acknowledgments

- Milvus for vector database
- Ollama for local LLM inference
- LangChain for document processing utilities
