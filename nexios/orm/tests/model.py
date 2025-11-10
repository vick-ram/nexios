import asyncio
from uuid import uuid4
from nexios.orm.backends.engine import create_engine
from nexios.orm.backends.sessions import Session, AsyncSession
from nexios.orm.field import Field
from nexios.orm.model import Model


class User(Model):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    name: str
    email: str
    password: str

user = User(id=str(uuid4()), name='Vickram Odero', email='vickram@gmail.com', password='Password1234')

postgres_config = {
    'host': 'localhost',
    'dbname': 'p_orm',
    'user': 'vickram',
    'password': 'Vickram9038'
}

postgres_engine = create_engine(dialect='postgres', echo=True, **postgres_config)

database = "example.db"
# url="sqlite:///example.db"

engine = create_engine(dialect="sqlite", database=database, echo=True)

async def async_main():
    async with AsyncSession(engine) as session:
        await session.create_all([User])
        await session.add(user)
        await session.commit()
    # import aiosqlite
    # async with aiosqlite.connect(":memory") as db:
    #     async with db.execute("SELECT 1") as cursor:
    #         cu = db.cursor()
    #         print(f"Is Cursor instance of cusor: {isinstance(cursor,aiosqlite.Cursor)}")
    #         print(f"Row count: {cursor.rowcount}")

if __name__=="__main__":
    with Session(postgres_engine) as session:
        session.create_all([User])
        print(f"Table name: {user.get_table_name()}")
        print(f"Table already exists: {session.query(User).exists()}")
        session.add(user)
        session.commit()
        print(f"Table already exists again after add: {session.query(User).exists()}")
    # asyncio.run(async_main())
    # with Session(engine) as session:
        #     session.create_all([User])
        #     session.add(user)
        #     session.commit()
        # users = (
        #     session.query(User)
        #     .limit(10)
        #     .all()
        # )
        # print(f"Users in database: {users}")
