// Frontend JavaScript for Agentic RAG System

let conversationHistory = [];

// Upload files
async function uploadFiles() {
    const fileInput = document.getElementById('file-input');
    const files = fileInput.files;
    
    if (files.length === 0) {
        showUploadStatus('Please select files to upload', 'error');
        return;
    }
    
    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }
    
    showUploadStatus('Uploading and processing...', 'loading');
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showUploadStatus(`✓ Uploaded ${result.processed} document(s)`, 'success');
            updateStats();
            refreshDocList();
            fileInput.value = '';
        } else {
            showUploadStatus(`✗ Error: ${result.error}`, 'error');
        }
    } catch (error) {
        showUploadStatus(`✗ Upload failed: ${error.message}`, 'error');
    }
}

// Submit query
async function submitQuery() {
    const queryInput = document.getElementById('query-input');
    const query = queryInput.value.trim();
    
    if (!query) {
        return;
    }
    
    // Clear activity log
    const activityLog = document.getElementById('activity-log');
    activityLog.innerHTML = '<p class="loading">Processing query</p>';
    
    // Show loading in answer
    const answerBox = document.getElementById('answer');
    answerBox.innerHTML = '<p class="loading">Agents are thinking</p>';
    
    try {
        const response = await fetch('/query', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query: query})
        });
        
        const result = await response.json();
        
        // Display answer
        if (result.success) {
            answerBox.innerHTML = formatAnswer(result.answer);
            displaySources(result.sources);
            displayActivity(result.activity_log);
            
            // Add to history
            conversationHistory.push({query, answer: result.answer});
            updateHistory();
            
            queryInput.value = '';
        } else {
            if (result.needs_clarification) {
                answerBox.innerHTML = `<strong>Need Clarification:</strong><br><br>${result.clarification_request}`;
            } else {
                answerBox.innerHTML = `<strong>Answer (Low Confidence):</strong><br><br>${result.answer}<br><br><em>Note: ${result.note || 'Quality below threshold'}</em>`;
                displaySources(result.sources);
            }
            displayActivity(result.activity_log);
        }
        
    } catch (error) {
        answerBox.innerHTML = `<strong>Error:</strong> ${error.message}`;
        activityLog.innerHTML = '<p class="error">Failed to process query</p>';
    }
}

// Format answer text
function formatAnswer(text) {
    // Simple formatting
    return text.replace(/\n/g, '<br>');
}

// Display sources
function displaySources(sources) {
    if (!sources || sources.length === 0) {
        document.getElementById('sources-section').style.display = 'none';
        return;
    }
    
    const sourcesDiv = document.getElementById('sources');
    sourcesDiv.innerHTML = '';
    
    sources.forEach((source, idx) => {
        const sourceItem = document.createElement('div');
        sourceItem.className = 'source-item';
        
        let location = '';
        if (source.page) location = `, Page ${source.page}`;
        else if (source.slide) location = `, Slide ${source.slide}`;
        else if (source.sheet) location = `, Sheet ${source.sheet}`;
        
        sourceItem.innerHTML = `
            <strong>[${idx + 1}] ${source.source}${location}</strong>
            <div>${source.file_type || ''}</div>
        `;
        
        sourcesDiv.appendChild(sourceItem);
    });
    
    document.getElementById('sources-section').style.display = 'block';
}

// Display agent activity
function displayActivity(activityLog) {
    const activityDiv = document.getElementById('activity-log');
    activityDiv.innerHTML = '';
    
    if (!activityLog || activityLog.length === 0) {
        activityDiv.innerHTML = '<p class="placeholder">No activity logged</p>';
        return;
    }
    
    activityLog.forEach(activity => {
        const item = document.createElement('div');
        item.className = 'activity-item';
        item.innerHTML = `
            <div class="agent-label">[${activity.agent}]</div>
            <div class="message">${activity.message}</div>
        `;
        activityDiv.appendChild(item);
    });
    
    // Scroll to bottom
    activityDiv.scrollTop = activityDiv.scrollHeight;
}

// Update conversation history
function updateHistory() {
    const historyDiv = document.getElementById('history');
    historyDiv.innerHTML = '';
    
    if (conversationHistory.length === 0) {
        historyDiv.innerHTML = '<p class="placeholder">No conversation yet</p>';
        return;
    }
    
    conversationHistory.slice().reverse().forEach(item => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.innerHTML = `
            <div class="query">Q: ${item.query}</div>
            <div class="answer">A: ${item.answer.substring(0, 150)}${item.answer.length > 150 ? '...' : ''}</div>
        `;
        historyDiv.appendChild(historyItem);
    });
}

// Update stats
async function updateStats() {
    try {
        const response = await fetch('/stats');
        const stats = await response.json();
        
        document.getElementById('doc-count').textContent = stats.documents || 0;
        document.getElementById('chunk-count').textContent = stats.chunks || 0;
    } catch (error) {
        console.error('Failed to update stats:', error);
    }
}

// Refresh document list
async function refreshDocList() {
    try {
        const response = await fetch('/documents');
        const docs = await response.json();
        
        const docList = document.getElementById('indexed-docs');
        docList.innerHTML = '<h4 style="margin-bottom: 10px;">Indexed Documents:</h4>';
        
        if (docs.documents && docs.documents.length > 0) {
            docs.documents.forEach(doc => {
                const docItem = document.createElement('div');
                docItem.className = 'doc-item';
                docItem.textContent = `• ${doc}`;
                docList.appendChild(docItem);
            });
        } else {
            docList.innerHTML += '<p class="placeholder">No documents yet</p>';
        }
    } catch (error) {
        console.error('Failed to refresh doc list:', error);
    }
}

// Show upload status
function showUploadStatus(message, type) {
    const statusDiv = document.getElementById('upload-status');
    statusDiv.textContent = message;
    statusDiv.className = type;
    statusDiv.style.display = 'block';
    
    if (type !== 'loading') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 5000);
    }
}

// Allow Enter key to submit
document.addEventListener('DOMContentLoaded', () => {
    const queryInput = document.getElementById('query-input');
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitQuery();
        }
    });
    
    // Load initial stats
    updateStats();
    refreshDocList();
});
