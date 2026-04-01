# NexiosORM Session Management Guide

Sessions are the core unit of work in NexiosORM. They manage database interactions, handle transactions, and ensure consistency across operations.

NexiosORM is designed to be async-first, but provides a unified and predictable API for both asynchronous and synchronous workflows.

## Core Concepts

- **Engine**: The entry point to your database (PostgreSQL, MySQL, SQLite).
- **Session**: A short-lived object representing a single transaction or unit of work.
- **AsyncSession**: Optimized for high-concurrency Nexios web handlers.
- **Session (Sync)**: Useful for CLI tools, scripts, or legacy synchronous code.

---

## 1. Asynchronous Sessions (Recommended)

In most Nexios applications, you should use AsyncSession to avoid blocking the event loop during database operations.

### Basic Usage

```python
from nexios_orm import create_async_engine, AsyncSession
from my_app.models import User

# 1. Setup the engine
engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")

async def create_user():
    # 2. Create a session instance
    async with AsyncSession(engine) as session:
        new_user = User(username="nexios_dev", email="dev@nexios.io")
        
        # 3. Add and commit
        session.add(new_user)
        await session.commit()
        
        # 4. Refresh to get DB-generated IDs
        await session.refresh(new_user)
        return new_user
```

### Integration with Nexios Dependency Injection

The most powerful way to use sessions is by injecting them into your routes:

```python
from nexios import NexiosApp, Depend
from nexios_orm import AsyncSession

app = NexiosApp()

async def get_db():
    async with AsyncSession(engine) as session:
        yield session

@app.post("/users")
async def add_user(data: dict, db: AsyncSession = Depend(get_db)):
    user = User(**data)
    db.add(user)
    await db.commit()
    return {"status": "created"}
```

---

## 2. Synchronous Sessions

Use Session when working outside async environments (scripts, migrations, background jobs).

### Basic Usage

```python
from nexios_orm import create_engine, Session
from my_app.models import User

engine = create_engine("sqlite:///database.db")

def sync_task():
    with Session(engine) as session:
        user = session.query(User).filter(id=1).first()
        user.is_active = True
        session.commit()
```

---

## 3. Transaction Management

### Manual Rollbacks
If an error occurs within a session block, NexiosORM typically handles the cleanup, but you can manage it manually for complex logic:

```python
async with AsyncSession(engine) as session:
    try:
        # Perform multiple operations
        session.add(item1)
        session.add(item2)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

### Flushing vs. Committing

---

## 4. Best Practices

1.  **One Session per Request**: In web apps, always create a new session at the start of a request and close it at the end (using Dependency Injection).
2.  **Avoid Global Sessions**: Never share a single session instance across multiple threads or async tasks; it is not thread-safe.
3.  **Use Context Managers**: Always use `with` or `async with` to ensure sessions are closed properly, even if an exception occurs.
4.  **Async for Web**: Always prefer `AsyncSession` when working inside `NexiosApp` route handlers to maintain high performance.

For more details on querying, see the [Querying Guide](guides/queries.md).