Stop both the backend and frontend dev servers.

Kill all related processes:

```
lsof -ti :8000 | xargs kill -9 2>/dev/null; pkill -f "uvicorn app.main:app" 2>/dev/null; lsof -ti :4200 | xargs kill -9 2>/dev/null; pkill -f "ng serve" 2>/dev/null
```

Run this with the Bash tool. Confirm both processes were stopped and tell the user all services have been stopped.
