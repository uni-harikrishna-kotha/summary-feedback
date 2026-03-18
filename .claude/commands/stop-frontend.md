Stop the Angular frontend dev server.

Find and kill any process listening on port 4200 or running ng serve:

```
lsof -ti :4200 | xargs kill -9 2>/dev/null; pkill -f "ng serve" 2>/dev/null
```

Run this with the Bash tool. Confirm the process was stopped and tell the user the frontend has been stopped.
