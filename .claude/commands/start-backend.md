Start the FastAPI backend dev server.

Run the following command in the background from the `backend/` directory:

```
cd /Users/repos/summary-feedback/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Use the Bash tool with `run_in_background: true`. After launching, confirm it started and tell the user the backend is running at http://localhost:8000.
