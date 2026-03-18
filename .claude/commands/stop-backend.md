Stop the FastAPI backend dev server.

Find and kill any process listening on port 8000 or running uvicorn:

```
lsof -ti :8000 | xargs kill -9 2>/dev/null; pkill -f "uvicorn app.main:app" 2>/dev/null
```

Run this with the Bash tool. Confirm the process was stopped and tell the user the backend has been stopped.
