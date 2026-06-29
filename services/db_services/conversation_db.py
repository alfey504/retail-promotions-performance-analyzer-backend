from services.db_services.session import SessionLocal
from services.db_services.models import Conversation
from datetime import datetime

from sqlalchemy import select
def create_conversation(
    conversation_title: str,
    user_id: int,
    created_at: datetime,
    promotion_id: int | None,
) -> Conversation:
    
    session = SessionLocal()
    conversation = Conversation(
        conversation_title = conversation_title,
        user_id = user_id,
        created_at = created_at, 
        promotion_id = promotion_id,   
    )
    try:
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation
    except Exception as e:
        print(e)
        raise e
    finally:
        session.close()

def conversation_by_user_id(user_id: int) -> list[Conversation]:
    session = SessionLocal()
    try:
        statement = select(Conversation).where(Conversation.user_id == user_id)
        conversations = session.scalars(statement).all()
        return list(conversations)
    except Exception as e:
        print(e)
    finally:
        session.close()