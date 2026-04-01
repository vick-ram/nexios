---
title: Querying Data
icon: search
description: Learn how to perform CRUD operations, filter, sort, and join data using Nexios ORM's query API.
head:
  - - meta
    - property: og:title
      content: Querying Data
  - - meta
    - property: og:description
      content: Learn how to perform CRUD operations, filter, sort, and join data using Nexios ORM's query API.
---

# Querying Data

Once you have defined your models and set up your database engine, the next step is to interact with your data. Nexios ORM provides a powerful and intuitive query API to perform common database operations like creating, reading, updating, and deleting (CRUD) records, as well as more complex filtering, sorting, and joining.

All query operations are performed through a `Session` object. Remember to use `AsyncSession` for asynchronous contexts (like Nexios route handlers) and `Session` for synchronous contexts.

The query system is:

- **Composable** → chain methods to build queries  
- **Typed** → model-aware results  
- **Dialect-aware** → generates correct SQL for PostgreSQL, MySQL, SQLite  
- **Async-first** → works seamlessly with `AsyncSession`  

---

## Setup for Examples

Let's assume you have the following models and an `AsyncSession` dependency set up:

```python
# my_app/models.py
from nexios_orm import NexiosModel, Field
from datetime import datetime

class User(NexiosModel):
    __tablename__ = "users"
    id: int = Field(primary_key=True, index=True)
    username: str
    email: str
    is_active: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Post(BaseModel):
    __tablename__ = "posts"
    id: int = Field(primary_key=True, index=True)
    title: str
    content: str
    user_id: int = Field(foreign_key="User.id")
    created_at: datetime = Field(DateTime, default_factory=datetime.utcnow)
```

```python
# my_app/database.py (or similar)
from nexios_orm import create_engine, AsyncSession, BaseModel
from nexios import Depend

DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/dbname"
engine = create_engine(DATABASE_URL, is_async=True)

async def get_db():
    async with AsyncSession(engine) as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
```

## Advanced Querying (Joins, Relationships, etc.)

For more complex scenarios involving multiple tables, you'll use relationships and joins. These are covered in detail in the Defining Relationships guide.

Next: Defining Relationships