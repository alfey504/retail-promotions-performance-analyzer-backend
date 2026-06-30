from services.db_services.session import SessionLocal
from services.db_services.models import Message
from datetime import datetime

from sqlalchemy import select

def add_message(
    conversation_id: str,
    role: str,
    content: str,
    created_at: datetime
) ->  Message: 
    session = SessionLocal()
    new_message = Message(
        conversation_id = conversation_id,
        role = role,
        content = content,
        created_at = created_at
    )

    try:
        session.add(new_message)
        session.commit()
        session.refresh(new_message)
        return new_message
    except Exception as e:
        print(e)
        raise e
    finally:
        session.close()

def get_messages_by_conversation_id(conversation_id: int) ->  list[Message]:
    session = SessionLocal()
    try:
        statement = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
        messages = session.scalars(statement).all()
        return list(messages)
    except Exception as e:
        print(e)
        raise e
    finally:
        session.close()