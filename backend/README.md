# iHubPT Backend

A FastAPI-based backend service for managing AI agents with Human-in-the-Loop (HITL) capabilities.

## Features

- Agent management (create, list, get, update)
- Tool registration and management
- LangGraph workflow creation
- HITL pause/resume functionality
- FastAPI with automatic API documentation

## Project Structure

```
backend/
├── app/
│   ├── config.py      # Application settings
│   ├── models.py      # Data models
│   ├── tools.py       # Tool registry
│   ├── engine.py      # LangGraph workflow engine
│   └── endpoints.py   # API endpoints
├── main.py           # FastAPI application
├── requirements.txt  # Project dependencies
└── README.md        # This file
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your configuration:
```env
DATABASE_URL=sqlite:///./ihubpt.db
SECRET_KEY=your-secret-key-here
```

4. Run the application:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the application is running, you can access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

The application uses:
- FastAPI for the web framework
- Pydantic for data validation
- LangChain for LLM integration
- SQLAlchemy for database operations

## License

MIT License 