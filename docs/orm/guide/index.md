---
title: Nexios ORM Overview
icon: database
description: An introduction to Nexios ORM, its features, and core concepts for efficient database interaction.
head:
  - - meta
    - property: og:title
      content: Nexios ORM Overview
  - - meta
    - property: og:description
      content: An introduction to Nexios ORM, its features, and core concepts for efficient database interaction.
---

# Nexios ORM Overview

Nexios ORM is a powerful, asynchronous-first Object-Relational Mapper designed to integrate seamlessly with the Nexios framework. It provides an elegant way to interact with your database using Python objects, abstracting away raw SQL queries and offering a more productive development experience.

Built with performance and developer experience in mind, Nexios ORM supports various relational databases and leverages Python's `async/await` syntax for non-blocking database operations, crucial for high-performance web applications.

## Key Features

- **Async-First Design**: Fully embraces Python's `async/await` for efficient, non-blocking I/O operations, making it ideal for concurrent web applications.
- **Declarative Model Definition**: Define your database schema using Python classes, making your code more readable and maintainable.
- **Flexible Querying**: A rich query API for performing CRUD (Create, Read, Update, Delete) operations, filtering, sorting, and complex joins.
- **Session Management**: Robust session handling for managing database transactions and ensuring data integrity.
- **Relationship Mapping**: Easily define one-to-one, one-to-many, and many-to-many relationships between your models.
- **Type Hinting Support**: Excellent integration with Python type hints for better IDE support, static analysis, and reduced errors.
- **Extensible**: Designed to be extensible, allowing for custom data types, query extensions, and integration with other tools.
- **Migration Support**: Integrates well with database migration tools like Alembic for managing schema changes.

## Why Use an ORM?

Using an ORM like Nexios ORM offers several significant advantages:

- **Abstraction**: You interact with Python objects instead of writing raw SQL, which can be less error-prone and faster to develop.
- **Maintainability**: Database schema changes are reflected in your models, making it easier to manage and understand your application's data layer.
- **Security**: ORMs often provide built-in protection against common SQL injection attacks.
- **Portability**: While not entirely database-agnostic, ORMs can make it easier to switch between different database backends with minimal code changes.
- **Productivity**: Reduces boilerplate code for common database operations, allowing you to focus on business logic.

## Core Concepts

Before diving into the specifics, it's helpful to understand the fundamental concepts of Nexios ORM:

- **Engine**: The central component that establishes a connection to your database. It's responsible for managing connection pools and dialect-specific configurations.
- **Model**: A Python class that represents a table in your database. Each attribute of the model typically maps to a column in the table.
- **Field/Column**: Attributes defined within a model that correspond to columns in the database table, specifying their type, constraints, and default values.
- **Session**: A temporary workspace for your database operations. It tracks changes to your objects and is responsible for committing (persisting) those changes to the database or rolling them back.
- **Query**: The mechanism used to retrieve, filter, and manipulate data from the database through your models.
- **Relationship**: Defines how different models (tables) are linked to each other (e.g., a `User` can have many `Posts`).

## Getting Started

To begin using Nexios ORM, you'll typically follow these steps:

1.  **Engine Setup**: Configure and create an `Engine` instance to connect to your database.
2.  **Model Definition**: Define your Python classes that map to database tables.
3.  **Session Management**: Learn how to create and use sessions to perform database operations.
4.  **Querying Data**: Interact with your database using the ORM's query API.

Let's dive into defining your first models!