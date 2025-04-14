# Technical Context: Brain Dump App

## Core Technologies
- **Backend**: Python 3.12 with Flask framework
- **Frontend**: HTML/CSS/JavaScript
- **Database**: SQLite (for initial development)
- **Templating**: Jinja2

## Development Setup
- Python virtual environment (braindump/)
- Key dependencies:
  - Flask (web framework)
  - Flask-SQLAlchemy (database ORM)
  - Markdown (text processing)
  - Pygments (syntax highlighting)

## Project Structure
```
brain_dump_app/
├── app.py                # Main application entry point
├── requirements.txt      # Python dependencies
├── wsgi.py               # WSGI configuration
├── braindump/            # Virtual environment
└── memory_bank/          # Documentation and context
```

## Key Technical Decisions
1. **Flask Framework**: Chosen for its simplicity and flexibility
2. **SQLite**: Lightweight database for initial development
3. **Client-side Rendering**: Minimal server-side rendering for faster UI updates
4. **Markdown Support**: Using Python-Markdown for rich text formatting

## Development Workflow
1. Activate virtual environment: `source braindump/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Run development server: `flask run`
4. Access app at: `http://localhost:5000`
