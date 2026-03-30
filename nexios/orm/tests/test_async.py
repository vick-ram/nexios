import pytest
from .test_models import User, Post, Address, Profile
from nexios.orm.query import select


class TestAsyncOperations:
    """Test async operations"""

    @pytest.mark.asyncio
    async def test_async_create_table(self, async_session):
        """Test async table creation"""
        await async_session.create_all(User, Post, Profile, Address)

        # Verify by inserting data
        user = User(
            username="asyncuser",
            email="async@example.com",
            password_hash="hash"
        )

        await async_session.add(user)
        await async_session.commit()

        assert user.id is not None

    @pytest.mark.asyncio
    async def test_async_insert_and_query(self, async_session):
        """Test async insert and query"""
        await async_session.create_all(User)

        # Insert multiple users
        for i in range(3):
            user = User(
                username=f"asyncuser{i}",
                email=f"async{i}@example.com",
                password_hash="hash"
            )
            await async_session.add(user)

        await async_session.commit()

        query_all = select(User)
        all_users = await async_session.exec(query_all).all()

        # Query asynchronously
        query = select(User).where(User.username.like("asyncuser%"))
        users = await async_session.exec(query).all()

        assert len(users) == 3

        # Test async first
        query = select(User).where(User.username == "asyncuser0")
        user = await async_session.exec(query).first()

        assert user is not None
        assert user.username == "asyncuser0"

    @pytest.mark.asyncio
    async def test_async_count(self, async_session):
        """Test async count operation"""
        await async_session.create_all(User)

        # Insert data
        for i in range(5):
            user = User(
                username=f"countuser{i}",
                email=f"count{i}@example.com",
                password_hash="hash"
            )
            await async_session.add(user)

        await async_session.commit()

        # Test async count
        query = select(User)
        count = await async_session.exec(query).count()

        assert count == 5

    @pytest.mark.asyncio
    async def test_async_exists(self, async_session):
        """Test async exists operation"""
        await async_session.create_all(User)

        # Empty table
        query = select(User).where(User.username == "nonexistent")
        exists = await async_session.exec(query).exists()
        assert exists is False

        # Insert user
        user = User(
            username="existuser",
            email="exist@example.com",
            password_hash="hash"
        )
        await async_session.add(user)
        await async_session.commit()

        # Should exist now
        query = select(User).where(User.username == "existuser")
        exists = await async_session.exec(query).exists()
        assert exists is True

    @pytest.mark.asyncio
    async def test_async_relationships(self, async_session):
        """Test async relationship loading"""
        await async_session.create_all(User, Post)

        # Create user with posts
        user = User(
            username="reluser",
            email="rel@example.com",
            password_hash="hash"
        )
        await async_session.add(user)
        await async_session.commit()

        post1 = Post(user_id=user.id, title="Async Post 1", content="Content 1")
        post2 = Post(user_id=user.id, title="Async Post 2", content="Content 2")

        await async_session.add(post1)
        await async_session.add(post2)
        await async_session.commit()

        # Query user with eager loading
        # query = select(User).where(User.username == "reluser").eager_load("posts")
        query = select(User).where(User.username == "reluser")
        fetched_user = await async_session.exec(query).first()
        fetched_posts = fetched_user.posts
        print(f"Fetched posts======================={fetched_posts}")

        # Posts should be loaded
        assert len(fetched_posts) == 2