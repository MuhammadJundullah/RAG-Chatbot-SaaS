from pydantic import BaseModel

class ChatlogBase(BaseModel):
    question: str
    answer: str
    UsersId: int
    company_id: int
    conversation_id: str

class ChatlogCreate(ChatlogBase):
    pass

class Chatlog(ChatlogBase):
    id: int

    class Config:
        from_attributes = True
