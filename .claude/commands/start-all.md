Start both the backend and frontend dev servers.

Run both commands in the background:

1. Backend (FastAPI on port 8000):
```
cd /Users/repos/summary-feedback/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. Frontend (Angular on port 4200):
```
cd /Users/repos/summary-feedback/frontend && npm install && ng serve --port 4200
```

Use the Bash tool with `run_in_background: true` for each. Launch them in parallel. After both are launched, tell the user:
- Backend is running at http://localhost:8000
- Frontend is running at http://localhost:4200
- API docs available at http://localhost:8000/docs
