import asyncio
from uuid import uuid4
from nexios.orm.backends.engine import create_engine
from nexios.orm.backends.sessions import Session, AsyncSession
from nexios.orm.field import Field, ForeignConstraint
from nexios.orm.model import Model


class User(Model):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    name: str
    email: str
    password: str

class Address(Model):
    # user_id: Field(foreign_key='User')
    county: str
    city: str
    state: str
    postal_code: str
    zip_code: str

user = User(
    id=str(uuid4()),
      name='Vickram Odero', 
      email='vickram@gmail.com', 
      password='Password1234'
      )
user2 = User(
    id=str(uuid4()),
      name='Brian Johnson', 
      email='brian@gmail.com', 
      password='Password1234'
      )

postgres_config = {
    'host': 'localhost',
    'dbname': 'p_orm',
    'user': 'vickram',
    'password': 'Vickram9038',
    'port': 5432
}

postgres_engine = create_engine(**postgres_config, echo=True)

if __name__=="__main__":
    with Session(postgres_engine) as session:
        # session.create_all([User])
        # session.add(user)
        # session.commit()

        existing_user = session.query(User).filter(id=user.id).first()
        exi = session.query(User).select('name', 'email', 'password').first() 
        if exi:
            print(f"Also print existing user with selected fields: {exi.dict()}")
        if existing_user:
            print(f"Table name: {existing_user.get_table_name()}")
            print(existing_user.dict())
