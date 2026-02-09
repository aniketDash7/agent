# Quick Start Guide

## Prerequisites

Before running the system, ensure you have:

1. **Python 3.9+** installed
2. **Docker Desktop** running (for Milvus)
3. **Ollama** installed with models downloaded

## Step 1: Install Ollama Models

```bash
# Install LLM model
ollama pull llama3

# Install embedding model  
ollama pull nomic-embed-text

# Verify installation
ollama list
```

## Step 2: Start Milvus Vector Database

```bash
# Navigate to project directory
cd "c:\Users\anike\Documents\Data Science\agentic-rag-system"

# Start Milvus containers
docker-compose up -d

# Verify containers are running
docker ps
```

You should see 3 containers: `milvus-standalone`, `milvus-etcd`, `milvus-minio`

## Step 3: Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 4: Configure Models

Edit `config.yaml` to match your Ollama models:

```yaml
ollama:
  llm_model: "llama3"           # Change if using different model
  embedding_model: "nomic-embed-text"  # Change if using different embedding
```

## Step 5: Run the Application

```bash
python app.py
```

You should see:

```
🚀 AGENTIC RAG SYSTEM
============================================================
LLM Model: llama3
Embedding Model: nomic-embed-text
Vector DB: Milvus (localhost:19530)
============================================================

📍 Navigate to: http://localhost:5000
```

## Step 6: Use the System

1. **Upload Documents**: Drag and drop PDF, DOCX, PPTX, XLSX, or TXT files
2. **Wait for Processing**: System will extract text, chunk, and embed documents
3. **Ask Questions**: Type your question and press "Ask"
4. **Watch Agents Work**: See real-time agent reasoning in the Activity panel

## Sample Queries to Try

After uploading the sample documents in `sample_data/`:

- **Simple**: "When was TechNova founded?"
- **Complex**: "Compare TechNova's revenue in 2023 to their client count and explain the relationship"
- **Multi-doc**: "What are TechNova's main products and what was their revenue last year?"

## Troubleshooting

### Milvus Connection Error
```
Error: Failed to connect to Milvus
```
**Solution**: Ensure Docker is running and Milvus containers are up:
```bash
docker-compose up -d
docker ps
```

### Ollama Model Not Found
```
Warning: Some models not available
```
**Solution**: Install required models:
```bash
ollama pull llama3
ollama pull nomic-embed-text
```

### Port Already in Use
```
Error: Address already in use: Port 5000
```
**Solution**: Change port in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

## Stopping the System

1. **Stop Flask**: Press `Ctrl+C` in terminal
2. **Stop Milvus**:
```bash
docker-compose down
```

## Next Steps

- Add your own documents
- Experiment with complex queries
- Adjust agent parameters in `config.yaml`
- Review agent reasoning in Activity panel
