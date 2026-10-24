from typing import Callable, Dict, List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import llm, schemas
from .config import settings
from .db import Base, engine, get_db
from .models import Conversation, Message, User
from .security import create_token, get_current_user, hash_password, verify_password

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lumen API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_llm() -> Callable[[List[Dict[str, str]]], str]:
    return llm.generate_reply


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- auth ----------
@app.post("/auth/register", response_model=schemas.TokenOut, status_code=201)
def register(body: schemas.Credentials, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return schemas.TokenOut(access_token=create_token(user.id))


@app.post("/auth/login", response_model=schemas.TokenOut)
def login(body: schemas.Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return schemas.TokenOut(access_token=create_token(user.id))


@app.get("/auth/me", response_model=schemas.UserOut)
def me(user: User = Depends(get_current_user)):
    return user


# ---------- conversations (all scoped to the logged-in user) ----------
def _owned(db: Session, user: User, conv_id: int) -> Conversation:
    conv = db.get(Conversation, conv_id)
    if conv is None or conv.user_id != user.id:  # 404 for others' data: don't reveal it exists
        raise HTTPException(404, "Conversation not found")
    return conv


@app.get("/conversations", response_model=List[schemas.ConversationOut])
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.id.desc())
    return list(db.scalars(stmt))


@app.get("/conversations/{conv_id}", response_model=schemas.ConversationDetail)
def get_conversation(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _owned(db, user, conv_id)


@app.delete("/conversations/{conv_id}", status_code=204)
def delete_conversation(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, conv_id))
    db.commit()


@app.post("/chat", response_model=schemas.ChatResponse)
def chat(
    body: schemas.ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    generate=Depends(get_llm),
):
    if body.conversation_id is not None:
        conv = _owned(db, user, body.conversation_id)
    else:
        conv = Conversation(user_id=user.id, title=body.message.strip()[:60])
        db.add(conv)
        db.flush()

    conv.messages.append(Message(role="user", content=body.message))
    db.flush()
    history = [{"role": m.role, "content": m.content} for m in conv.messages[-settings.max_history_messages :]]
    try:
        text = generate(history)
    except llm.LLMError as exc:
        db.rollback()
        raise HTTPException(502, str(exc))

    reply = Message(role="assistant", content=text)
    conv.messages.append(reply)
    db.commit()
    db.refresh(reply)
    db.refresh(conv)
    return schemas.ChatResponse(conversation=conv, reply=reply)
