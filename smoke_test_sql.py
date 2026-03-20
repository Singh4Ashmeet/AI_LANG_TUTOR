import sys
import os
import asyncio
from sqlmodel import SQLModel

# Add the project root to sys.path
sys.path.append(os.getcwd())

async def smoke_test():
    print("Starting smoke test...")
    try:
        print("Importing config...")
        from backend.config import settings
        print(f"Config loaded. DB URL starts with: {settings.DATABASE_URL[:10]}...")

        print("Importing database...")
        from backend.database import engine, init_db
        
        print("Importing models...")
        from backend.models.user import User
        from backend.models.session import Session
        from backend.models.vocabulary import VocabularyItem
        from backend.models.extra import Curriculum, Achievement
        from backend.models.admin import AdminLog
        
        print("Importing routers...")
        from backend.routers import auth, users, lessons, chat, roleplay, voice
        
        print("Importing services...")
        from backend.services import agents, learner, seed
        
        print("All imports successful.")
        
    except ImportError as e:
        print(f"ImportError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(smoke_test())
