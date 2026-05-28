# ResearchGPT

ResearchGPT is a Flask-based research paper assistant that lets you upload PDF papers, index them into a local Chroma vector database, and ask citation-backed questions using Gemini.

## Features

- Upload and manage research paper PDFs.
- Automatically split and embed paper text for semantic retrieval.
- Ask questions across uploaded papers or focus on a single paper.
- Generate structured summaries for individual papers.
- View cited source chunks with filenames and page numbers.
- Run standalone semantic search over indexed papers.

## Tech Stack

- Python and Flask
- LangChain
- ChromaDB
- Hugging Face sentence-transformer embeddings
- Google Gemini via `langchain-google-genai`
- HTML, CSS, and JavaScript frontend

## Project Structure

```text
ResearchGPT/
├── app.py                 # Flask routes and API endpoints
├── config.py              # Environment and path configuration
├── rag_engine.py          # PDF processing, retrieval, chat, summary logic
├── requirements.txt       # Python dependencies
├── static/                # CSS and JavaScript assets
├── templates/             # Flask HTML templates
├── uploads/               # Local uploaded PDFs, ignored by git
└── data/chromadb/         # Local vector database, ignored by git
```

## Setup

1. Clone the repository.

```bash
git clone https://github.com/Nimisha1518/ResearchGPT.git
cd ResearchGPT
```

2. Create and activate a virtual environment.

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies.

```bash
pip install -r requirements.txt
```

4. Create your environment file.

```bash
copy .env.example .env
```

5. Add your Gemini API key in `.env`.

```env
GEMINI_API_KEY=your-gemini-api-key
```

## Run

```bash
python app.py
```

Open the app at:

```text
http://localhost:5000
```

## Usage

1. Open the upload page and upload one or more PDF research papers.
2. Wait for the app to process and index the papers.
3. Use the chat page to ask questions about the uploaded papers.
4. Review the cited source chunks returned with each answer.
5. Generate summaries or delete papers from the interface when needed.

## Notes

- Uploaded PDFs and the local Chroma database are intentionally ignored by git.
- The app requires a valid `GEMINI_API_KEY` for chat and summary generation.
- The embedding model is downloaded locally the first time the app initializes.
