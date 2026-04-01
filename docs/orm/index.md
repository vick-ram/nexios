# NexiosORM

A modern ORM for the Nexios framework

## Why NexiosORM
- **Type Safety**: Fully compatible with Python type hints and Pydantic.
- **Async First**: Built from the ground up for asynchronous database operations.
- **Developer Experience**: Intuitive API that reduces boilerplate and prevents common pitfalls.
- **Seamless Integration**: Designed specifically to work with Nexios dependency injection and middleware.

## Highlights
- **Declarative Models**: Define your schema using standard Python classes.
- **Powerful Query Builder**: Chainable methods for complex filtering, joining, and aggregation.
- **Relationship Management**: Easy handling of One-to-One, One-to-Many, and Many-to-Many relations.
- **Migrations**: Built-in support for schema versioning and automated migrations.
- **Validation**: Automatic data validation before it ever hits your database.

## Core Concepts

### The Session
NexiosORM uses a session-based pattern to manage database transactions, ensuring data integrity and efficient connection pooling.

### Models
Models are the heart of NexiosORM. They map your database tables to Python objects, allowing for IDE autocompletion and compile-time checks.

### Engines
Configure multiple database backends including PostgreSQL, MySQL, and SQLite with a unified configuration interface.

## Get started

1. **[Installation](getting-started/installation.md)**: Add NexiosORM to your project.
2. **[Quickstart](getting-started/quickstart.md)**: Create your first model and run your first query in under 5 minutes.
3. **[Defining Models](guides/models.md)**: Learn how to map your data structures.
4. **[Querying](guides/queries.md)**: Master the expressive query API.
5. **[Migrations](guides/migrations.md)**: Keep your database schema in sync with your code.