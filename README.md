# LinguAI

AI-powered language tutor built with FastAPI, React, and MongoDB.

## Setup

### Backend
1. Create a `.env` file in the repo root based on `.env.example`.
2. Install dependencies:

```
python -m pip install -r requirements.txt
```
3. Run the API:

```
uvicorn backend.main:app --reload
```

### Frontend
1. Install dependencies and run:

```
npm install
npm run dev
```

### Run Both
You can start the frontend and backend together with:

```
python app.py
```

### MongoDB Setup
See `MONGODB_SETUP.md` for step-by-step guidance and example connection strings.

## Admin Accounts
Admin users must be created directly in MongoDB with `role="admin"` and a bcrypt-hashed password. There is no admin registration route.
