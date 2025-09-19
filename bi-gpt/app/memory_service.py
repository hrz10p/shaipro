from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from app.models import Base, Session, Message
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

class MemoryService:
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self):
        return self.SessionLocal()
    
    def create_session(self) -> str:
        db = self.get_session()
        try:
            session = Session()
            db.add(session)
            db.commit()
            db.refresh(session)
            return session.id
        finally:
            db.close()
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        if session_id:
            db = self.get_session()
            try:
                session = db.query(Session).filter(Session.id == session_id).first()
                if session:
                    return session.id
            finally:
                db.close()
        
        return self.create_session()
    
    def add_message(self, session_id: str, content: str, sender: str) -> None:
        db = self.get_session()
        try:
            message = Message(
                session_id=session_id,
                content=content,
                sender=sender
            )
            db.add(message)
            db.commit()

            self._cleanup_old_messages(session_id)
        finally:
            db.close()
    
    def get_recent_messages(self, session_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        db = self.get_session()
        try:
            messages = db.query(Message).filter(
                Message.session_id == session_id
            ).order_by(desc(Message.timestamp)).limit(limit).all()
            
            return [
                {
                    "content": msg.content,
                    "sender": msg.sender,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in reversed(messages)
            ]
        finally:
            db.close()
    
    def _cleanup_old_messages(self, session_id: str) -> None:
        db = self.get_session()
        try:
            all_messages = db.query(Message).filter(
                Message.session_id == session_id
            ).order_by(desc(Message.timestamp)).all()
            
            if len(all_messages) > 3:
                messages_to_delete = all_messages[3:]
                for msg in messages_to_delete:
                    db.delete(msg)
                db.commit()
        finally:
            db.close()
    
    def get_session_context(self, session_id: str) -> str:
        messages = self.get_recent_messages(session_id, limit=3)
        
        if not messages:
            return ""
        
        context_parts = []
        for msg in messages:
            role = "User" if msg["sender"] == "user" else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    def clear_session(self, session_id: str) -> None:
        db = self.get_session()
        try:
            db.query(Message).filter(Message.session_id == session_id).delete()
            db.commit()
        finally:
            db.close()
    
memory_service = MemoryService()
