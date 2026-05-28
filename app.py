import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from config import Config
from rag_engine import ResearchPaperRAG

app = Flask(__name__)
app.config.from_object(Config)

# Initialize RAG Engine
# We pass Config.CHROMA_DB_DIR and the API key.
# Note: The API key can be updated dynamically if needed, but we read it from config.
rag = ResearchPaperRAG(
    chroma_db_dir=Config.CHROMA_DB_DIR,
    gemini_api_key=Config.GEMINI_API_KEY
)

def get_uploaded_files():
    """Helper to scan the uploads folder and return metadata for display."""
    if not os.path.exists(Config.UPLOAD_FOLDER):
        return []
    
    files_list = []
    for f in os.listdir(Config.UPLOAD_FOLDER):
        if f.lower().endswith('.pdf'):
            file_path = os.path.join(Config.UPLOAD_FOLDER, f)
            file_stat = os.stat(file_path)
            size_mb = file_stat.st_size / (1024 * 1024)
            files_list.append({
                "filename": f,
                "size_mb": round(size_mb, 2),
                "created_time": file_stat.st_mtime
            })
    # Sort files by creation time (newest first)
    files_list.sort(key=lambda x: x["created_time"], reverse=True)
    return files_list

@app.route('/')
def home():
    """Renders the Home page."""
    files = get_uploaded_files()
    return render_template('home.html', files=files)

@app.route('/upload')
def upload_page():
    """Renders the PDF upload management page."""
    files = get_uploaded_files()
    return render_template('upload.html', files=files)

@app.route('/chat')
def chat_page():
    """Renders the AI chat interface."""
    files = get_uploaded_files()
    return render_template('chat.html', files=files)

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Handles uploading of PDF files and initiates RAG processing."""
    if 'files' not in request.files:
        return jsonify({"success": False, "error": "No file part in request"}), 400
        
    uploaded_files = request.files.getlist('files')
    if not uploaded_files or uploaded_files[0].filename == '':
        return jsonify({"success": False, "error": "No files selected"}), 400
        
    success_count = 0
    errors = []
    
    for file in uploaded_files:
        if file and file.filename.lower().endswith('.pdf'):
            filename = secure_filename(file.filename)
            file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            
            try:
                # Save the file to local upload directory
                file.save(file_path)
                
                # Ingest into vector database
                rag.process_pdf(file_path)
                success_count += 1
            except Exception as e:
                errors.append(f"Failed to process {file.filename}: {str(e)}")
                # Clean up file if it was saved but failed processing
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
        else:
            errors.append(f"Ignored {file.filename} (only PDF files are supported)")
            
    if success_count > 0:
        return jsonify({
            "success": True, 
            "message": f"Successfully uploaded and indexed {success_count} paper(s).",
            "errors": errors
        })
    else:
        return jsonify({
            "success": False, 
            "error": "Failed to process any uploaded files.",
            "details": errors
        }), 400

@app.route('/api/files', methods=['GET'])
def api_get_files():
    """Returns lists of uploaded research papers."""
    return jsonify({"success": True, "files": get_uploaded_files()})

@app.route('/api/delete', methods=['POST'])
def api_delete_file():
    """Deletes an uploaded PDF from filesystem and ChromaDB index."""
    data = request.json or {}
    filename = data.get('filename')
    
    if not filename:
        return jsonify({"success": False, "error": "Filename is required"}), 400
        
    # Secure the filename
    filename = secure_filename(filename)
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    
    # 1. Delete from vector store
    try:
        rag.delete_paper(filename)
    except Exception as e:
        return jsonify({"success": False, "error": f"Error deleting from database: {str(e)}"}), 500
        
    # 2. Delete from filesystem
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            return jsonify({"success": False, "error": f"Error deleting file from disk: {str(e)}"}), 500
            
    return jsonify({"success": True, "message": f"Successfully deleted paper: {filename}"})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Endpoint to handle conversation queries and retrieve cited responses."""
    data = request.json or {}
    query = data.get('query')
    chat_history = data.get('chat_history', []) # Expected format: [["user", "hi"], ["assistant", "hello"]]
    filter_filename = data.get('filename') # Optional: focus query on specific paper
    
    if not query:
        return jsonify({"success": False, "error": "Query is required"}), 400
        
    # Check if Gemini key is set; if not, read dynamic headers or remind user
    # (Checking if user sent it or configured it)
    if not rag.gemini_api_key:
        # Check if they have updated their env since startup
        # Reload env key dynamically in case they just added it to .env
        from dotenv import load_dotenv
        load_dotenv(override=True)
        rag.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        
    result = rag.answer_query(query, chat_history, filter_filename)
    return jsonify({"success": True, **result})

@app.route('/api/summarize', methods=['POST'])
def api_summarize():
    """Generates a summary for a specific research paper."""
    data = request.json or {}
    filename = data.get('filename')
    
    if not filename:
        return jsonify({"success": False, "error": "Filename is required"}), 400
        
    filename = secure_filename(filename)
    summary = rag.summarize_paper(filename)
    return jsonify({"success": True, "summary": summary})

@app.route('/api/search', methods=['POST'])
def api_search():
    """Standalone semantic search route across all research chunks."""
    data = request.json or {}
    query = data.get('query')
    
    if not query:
        return jsonify({"success": False, "error": "Query is required"}), 400
        
    results = rag.semantic_search(query)
    return jsonify({"success": True, "results": results})

if __name__ == '__main__':
    # Running local server
    app.run(host='0.0.0.0', port=5000, debug=True)
