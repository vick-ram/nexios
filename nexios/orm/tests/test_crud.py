import pytest

from nexios.orm.config import PostgreSQLDialect
from nexios.orm.tests.test_models import User, Profile, Address, Post

class TestCRUDOperations:
    """Test basic create, read, update, delete operations."""

    def test_create_table(self, sync_session):
        sync_session.create_all(User, Profile, Address, Post)

        # Verify
        if isinstance(sync_session.engine.dialect, PostgreSQLDialect):
            results = sync_session.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ).fetchall()
            tables = [row[0] for row in results]
            assert 'users' in tables
            assert 'profiles' in tables
            assert 'addresses' in tables
            assert 'posts' in tables

    def test_insert_user(self, sync_session):
        """Test inserting a single user"""
        # Create tables
        from nexios.orm.query import select

        sync_session.create_all(User)

        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password"
        )

        # Insert
        sync_session.add(user)
        sync_session.commit()

        # Verify insertion
        assert user.id is not None
        assert user.created_at is not None

        # Query back
        query = select(User).where(User.username == "testuser")
        fetched_user = sync_session.exec(query).first()

        print(f"Fetched user in insert test function: {fetched_user}")

        assert fetched_user is not None
        assert fetched_user.id == user.id
        assert fetched_user.username == "testuser"
        assert fetched_user.email == "test@example.com"

    def test_insert_multiple_users(self, sync_session):
        """Test inserting multiple users"""
        from nexios.orm.query import select

        sync_session.create_all(User)

        users = [
            User(username=f"user{i}", email=f"user{i}@example.com", password_hash="hash")
            for i in range(5)
        ]

        for user in users:
            sync_session.add(user)
        sync_session.commit()

        # Verify all inserted
        assert User.count(sync_session) == 5

        # Query with limit
        query = select(User).limit(3)
        results = sync_session.exec(query).all()
        assert len(results) == 3

    def test_update_user(self, sync_session):
        """Test updating a user"""
        from nexios.orm.query import select

        sync_session.create_all(User)

        # Create user
        user = User(
            username="original",
            email="original@example.com",
            password_hash="hash"
        )
        sync_session.add(user)
        sync_session.commit()

        # Update
        user.username = "updated"
        user.email = "updated@example.com"
        sync_session.add(user)  # Should trigger update
        sync_session.commit()

        # Verify update
        query = select(User).where(User.id == user.id)
        updated_user = sync_session.exec(query).first()

        assert updated_user.username == "updated"
        assert updated_user.email == "updated@example.com"

    def test_delete_user(self, sync_session):
        """Test deleting a user"""
        from nexios.orm.query import select

        sync_session.create_all(User)

        # Create users
        user1 = User(username="user1", email="user1@example.com", password_hash="hash")
        user2 = User(username="user2", email="user2@example.com", password_hash="hash")

        sync_session.add(user1)
        sync_session.add(user2)
        sync_session.commit()

        # Delete one user
        sync_session.delete(user1)
        sync_session.commit()

        # Verify deletion
        assert User.count(sync_session) == 1

        query = select(User).where(User.username == "user1")
        deleted_user = sync_session.exec(query).first()
        assert deleted_user is None

        # Other user should still exist
        query = select(User).where(User.username == "user2")
        existing_user = sync_session.exec(query).first()
        assert existing_user is not None

    def test_where_clause(self, sync_session):
        """Test WHERE clause with various conditions"""
        from nexios.orm.query import select

        sync_session.create_all(User)

        users = [
            User(username="alice", email="alice@example.com", password_hash="hash", is_active=True),
            User(username="bob", email="bob@example.com", password_hash="hash", is_active=False),
            User(username="charlie", email="charlie@example.com", password_hash="hash", is_active=True),
        ]

        for user in users:
            sync_session.add(user)
        sync_session.commit()

        # Test equality
        query = select(User).where(User.username == "alice")
        result = sync_session.exec(query).first()
        assert result.username == "alice"

        # Test inequality
        query = select(User).where(User.username != "alice")
        results = sync_session.exec(query).all()
        assert len(results) == 2

        # Test boolean
        query = select(User).where(User.is_active == True)
        results = sync_session.exec(query).all()
        assert len(results) == 2

        # Test multiple conditions
        query = select(User).where(
            (User.is_active == True) & (User.username != "charlie")
        )
        results = sync_session.exec(query).all()
        assert len(results) == 1
        assert results[0].username == "alice"

    def test_order_by(self, sync_session):
        """Test ORDER BY clause"""
        from nexios.orm.query import select

        sync_session.create_all(User)

        users = [
            User(username="zack", email="z@example.com", password_hash="hash"),
            User(username="alice", email="a@example.com", password_hash="hash"),
            User(username="bob", email="b@example.com", password_hash="hash"),
        ]

        for user in users:
            sync_session.add(user)
        sync_session.commit()

        # Ascending order
        query = select(User).order_by(User.username)
        results = sync_session.exec(query).all()
        assert [u.username for u in results] == ["alice", "bob", "zack"]

        # Descending order
        query = select(User).order_by(User.username.desc())
        results = sync_session.exec(query).all()
        assert [u.username for u in results] == ["zack", "bob", "alice"]

    def test_limit_offset(self, sync_session):
        """Test LIMIT and OFFSET"""
        from nexios.orm.query import select

        sync_session.create_all(User)

        for i in range(10):
            user = User(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password_hash="hash"
            )
            sync_session.add(user)
        sync_session.commit()

        # Test limit
        query = select(User).limit(3)
        results = sync_session.exec(query).all()
        assert len(results) == 3

        # Test offset
        query = select(User).offset(5)
        results = sync_session.exec(query).all()
        assert len(results) == 5

        # Test limit + offset
        query = select(User).limit(2).offset(3)
        results = sync_session.exec(query).all()
        assert len(results) == 2
        assert results[0].username == "user3"
        assert results[1].username == "user4"

    def test_count(self, sync_session):
        """Test COUNT operation"""
        from nexios.orm.query import select

        sync_session.create_all(User)

        # Insert 5 users
        for i in range(5):
            user = User(
                username=f"countuser{i}",
                email=f"count{i}@example.com",
                password_hash="hash"
            )
            sync_session.add(user)
        sync_session.commit()

        # Test total count
        query = select(User)
        count = sync_session.exec(query).count()
        assert count == 5

        # Test filtered count
        query = select(User).where(User.username.like("countuser%"))
        count = sync_session.exec(query).count()
        assert count == 5

        # Test count with condition
        query = select(User).where(User.username == "countuser0")
        count = sync_session.exec(query).count()
        assert count == 1

    def test_exists(self, sync_session):
        """Test EXISTS operation"""
        from nexios.orm.query import select

        sync_session.create_all(User)

        # Empty table
        query = select(User).where(User.username == "nonexistent")
        # print(f"User is======: {sync_session.exec(query).one().username}")
        exists = sync_session.exec(query).exists()
        print(f"User exists in database: {exists}")
        assert exists is False

        # Insert user
        user = User(username="existsuser", email="exists@example.com", password_hash="hash")
        sync_session.add(user)
        sync_session.commit()

        # Should exist now
        query = select(User).where(User.username == "existsuser")
        assert sync_session.exec(query).exists() is True