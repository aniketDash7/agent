"""
Main Flask application for Agentic RAG System.
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pathlib import Path
import logging
import os

from src.utils.config import load_config
from src.llm.ollama_client import OllamaClient
from src.database.milvus_client import MilvusClient
from src.database.bm25_index import BM25Index
from src.ingestion.document_loader import DocumentLoader
from src.ingestion.chunking_strategy import TextChunker
from src.retrieval.hybrid_search import HybridSearch
from src.agents.orchestrator import AgentOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load configuration
config = load_config()

# Setup upload folder
UPLOAD_FOLDER = Path(config['ui']['upload_folder'])
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config['ui']['max_file_size_mb'] * 1024 * 1024

# Initialize components
logger.info("Initializing system components...")

# Initialize Ollama client
ollama_client = OllamaClient(
    base_url=config['ollama']['base_url'],
    llm_model=config['ollama']['llm_model'],
    embedding_model=config['ollama']['embedding_model'],
    temperature=config['ollama']['temperature']
)

# Check model availability
models_available = ollama_client.check_model_availability()
if not all(models_available.values()):
    logger.warning(f"Some models not available: {models_available}")

# Initialize Milvus
milvus_client = MilvusClient(
    host=config['milvus']['host'],
    port=config['milvus']['port'],
    collection_name=config['milvus']['collection_name'],
    embedding_dim=config['milvus']['embedding_dim']
)

# Initialize BM25
bm25_index = BM25Index(index_path="bm25_index.pkl")
bm25_index.load()  # Load existing index if available

# Initialize hybrid search
hybrid_search = HybridSearch(
    milvus_client=milvus_client,
    bm25_index=bm25_index,
    alpha=config['retrieval']['hybrid_alpha']
)

# Initialize orchestrator
orchestrator = AgentOrchestrator(
    llm_client=ollama_client,
    hybrid_search=hybrid_search,
    config=config
)

# Initialize text chunker
text_chunker = TextChunker(
    chunk_size=config['chunking']['chunk_size'],
    chunk_overlap=config['chunking']['chunk_overlap'],
    separators=config['chunking']['separators']
)

# Track indexed documents
indexed_documents = set()

logger.info("✓ System initialized successfully")


@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_documents():
    """Upload and process documents."""
    try:
        files = request.files.getlist('files')
        
        if not files or len(files) == 0:
            return jsonify({'success': False, 'error': 'No files provided'}), 400
        
        processed_count = 0
        all_chunks = []
        
        for file in files:
            if file.filename == '':
                continue
            
            # Check file extension
            ext = Path(file.filename).suffix.lower()
            if ext not in ['.pdf', '.docx', '.pptx', '.xlsx', '.txt']:
                continue
            
            # Save file
            filename = secure_filename(file.filename)
            filepath = UPLOAD_FOLDER / filename
            file.save(filepath)
            
            logger.info(f"Processing {filename}...")
            
            # Load document
            doc_data = DocumentLoader.load(str(filepath))
            
            # Chunk document
            chunks = text_chunker.chunk_document(doc_data)
            all_chunks.extend(chunks)
            
            # Track document
            indexed_documents.add(filename)
            processed_count += 1
        
        if processed_count == 0:
            return jsonify({'success': False, 'error': 'No valid files processed'}), 400
        
        # Generate embeddings and index
        logger.info(f"Generating embeddings for {len(all_chunks)} chunks...")
        
        texts = [chunk['text'] for chunk in all_chunks]
        metadatas = [chunk['metadata'] for chunk in all_chunks]
        
        embeddings = ollama_client.batch_embeddings(texts)
        
        # Insert into Milvus
        milvus_client.insert(embeddings, texts, metadatas)
        
        # Build BM25 index
        bm25_index.build_index(texts, metadatas)
        bm25_index.save()
        
        logger.info(f"✓ Indexed {processed_count} documents with {len(all_chunks)} chunks")
        
        return jsonify({
            'success': True,
            'processed': processed_count,
            'chunks': len(all_chunks)
        })
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/query', methods=['POST'])
def query():
    """Process user query."""
    try:
        data = request.get_json()
        user_query = data.get('query', '').strip()
        
        if not user_query:
            return jsonify({'success': False, 'error': 'No query provided'}), 400
        
        logger.info(f"Processing query: {user_query}")
        
        # Process through orchestrator
        result = orchestrator.process_query(user_query)
        
        # Format response
        response = {
            'success': result.get('success', False),
            'answer': result.get('answer', ''),
            'sources': result.get('sources', []),
            'activity_log': result.get('activity_log', []),
            'needs_clarification': result.get('needs_clarification', False),
            'clarification_request': result.get('clarification_request', ''),
            'note': result.get('note', '')
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Query error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'activity_log': [{'agent': 'system', 'message': f'Error: {str(e)}'}]
        }), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics."""
    try:
        return jsonify({
            'documents': len(indexed_documents),
            'chunks': milvus_client.get_count()
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'documents': 0, 'chunks': 0})


@app.route('/documents', methods=['GET'])
def get_documents():
    """Get list of indexed documents."""
    try:
        return jsonify({'documents': sorted(list(indexed_documents))})
    except Exception as e:
        logger.error(f"Documents list error: {e}")
        return jsonify({'documents': []})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("AGENTIC RAG SYSTEM")
    print("="*60)
    print(f"LLM Model: {config['ollama']['llm_model']}")
    print(f"Embedding Model: {config['ollama']['embedding_model']}")
    print(f"Vector DB: Milvus ({config['milvus']['host']}:{config['milvus']['port']})")
    print("="*60)
    print("\nNavigate to: http://localhost:5000\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
