import asyncio
from uuid import uuid4
from typing import List, Optional
from nexios.orm.engine import create_engine
from nexios.orm.sessions import Session, AsyncSession
from nexios.orm.model import BaseModel, Field
from nexios.orm.query import select
from pydantic import BaseModel as PydanticBaseModel
from nexios.orm._model import NexiosModel, Field as NexiosField, one_to_many, _SESSION


# class User(BaseModel):
#     __tablename__ = "users"

#     id: str = Field(primary_key=True)
#     name: str
#     email: str = Field(unique=True)
#     password: str

#     addresses: List["Address"]

class Address(NexiosModel):
    __tablename__ = "addresses"

    user_id: str = NexiosField(foreign_key='User')
    county: str
    city: str
    state: str
    postal_code: str
    zip_code: str

class User(NexiosModel):
    __tablename__ = "users"

    id: str = NexiosField(primary_key=True)
    name: str
    email: str = NexiosField(unique=True)
    password: str
    phone: Optional[str] = None

    @one_to_many("Address", back_populates="user")
    def addresses(self): List["Address"]

user = User(
    id=str(uuid4()),
      name='Vickram Odero', 
      email='vickram@gmail.com', 
      password='Password1234'
      )
# user2 = User(
#     id=str(uuid4()),
#       name='Brian Johnson', 
#       email='brian@gmail.com', 
#       password='Password1234'
#       )

postgres_config = {
    'host': 'localhost',
    'dbname': 'p_orm',
    'user': 'vickram',
    'password': 'Vickram9038',
    'port': 5432
}

postgres_engine = create_engine(echo=True, **postgres_config, use_pool=True)

if __name__=="__main__":
    with Session(postgres_engine) as session:
        # session.create_all([User, Address])
        # session.add(user)
        # session.commit()

        # fields = []

        # keys = user.get_fields().keys()
        # for field in keys:
        #     fields.append(field)
        # print(f"Model fields: {fields} Length: {len(keys)}")

        # existing_user_query = select(User.c('vickram@gmail.com'))
        # existing_user_query = select(User).where(User.email == "vickramodero6@gmail.com").order_by(User.id)
        # existing_user = session.exec(existing_user_query).one()
        # users_query = select(User).distinct()
        # users = session.exec(users_query).all()
        # print(users)
        print(f"Nexios model data: {User.model_fields}")
        print(f"Get relationships: {User.get_relationships()}")
        print(f"Testing known error with session: {Address.get_relationships()}")
        # print(f"Annotations: {User.__annotations__}")
        print(f"Session wit error: {_SESSION}")