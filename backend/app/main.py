from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import tasks, users, chat, manager, manager_chat, board

app = FastAPI(title="Nexus PM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router, prefix="/api", tags=["Tasks"])
app.include_router(users.router, prefix="/api", tags=["Users"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(manager.router, prefix="/api", tags=["Manager"]) 
app.include_router(manager_chat.router, prefix="/api", tags=["Manager Chat"])
app.include_router(board.router, prefix="/api", tags=["Kanban Board"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Nexus PM API"}