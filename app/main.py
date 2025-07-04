from fastapi import FastAPI
from pydantic import BaseModel
from app.agent import AmenityAgent
from utils.db import init_db
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
agent = AmenityAgent()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    response = agent.handle_message(request.session_id, request.message)
    return {"response": response}
