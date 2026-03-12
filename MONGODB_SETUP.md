# MongoDB Setup

This project reads `MONGODB_URL` from `.env` in the repo root.

## Option 1: Local MongoDB
1. Install MongoDB Community Server.
2. Start the service.
3. Use this connection string:

```
MONGODB_URL=mongodb://localhost:27017/linguai
```

## Option 2: MongoDB Atlas (Cloud)
1. Create a free cluster in MongoDB Atlas.
2. Create a database user (username + password).
3. Allow your IP in Network Access (or use `0.0.0.0/0` for development).
4. Click **Connect** and copy the connection string.
5. Replace `<username>`, `<password>`, and `<cluster-url>`:

```
MONGODB_URL=mongodb+srv://<username>:<password>@<cluster-url>/linguai?retryWrites=true&w=majority
```

## Other .env Values
Typical local defaults:

```
FRONTEND_URL=http://localhost:5173
VITE_API_URL=http://localhost:8000
```

If you run with `python app.py`, any `VITE_` variables in `.env` are passed to the frontend dev server.
