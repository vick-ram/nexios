from datetime import datetime, timedelta

import pytest

from nexios.orm.query.builder import select
from .test_models import User, Post


class TestAdvancedQueries:
    """Test advanced query operations"""
    def test_join_operations(self, sync_session):
        """Test JOIN operations"""

        sync_session.create_all(User, Post)

        # Create test data
        users = [
            User(username="joinuser1", email="join1@example.com", password_hash="hash"),
            User(username="joinuser2", email="join2@example.com", password_hash="hash"),
        ]

        for user in users:
            sync_session.add(user)
        sync_session.commit()

        posts = [
            Post(user_id=users[0].id, title="User1 Post 1", content="Content"),
            Post(user_id=users[0].id, title="User1 Post 2", content="Content"),
            Post(user_id=users[1].id, title="User2 Post 1", content="Content")
        ]

        for post in posts:
            sync_session.add(post)
        sync_session.commit()

        # Test INNER JOIN
        query = (
            select(User, Post)
            .inner_join(Post, Post.user_id == User.id)
            .where(User.username == "joinuser1")
        )
        results = sync_session.exec(query).all()

        print(f"Results in test join==========: {results}")

        # Should get 2 results (user1 has 2 posts)
        assert len(results) == 2
        for user, post in results:
            assert user.username == "joinuser1"
            assert post.user_id == user.id

        # Test LEFT JOIN
        query = (
            select(User, Post)
            .left_join(Post, Post.user_id == User.id)
            .order_by(User.username, Post.title)
        )
        results = sync_session.exec(query).all()

        # Should get 3 results (user1: 2 posts, user2: 1 post)
        assert len(results) == 3

    def test_group_by_and_having(self, sync_session):
        """Test GROUP BY and HAVING clauses"""

        sync_session.create_all(User, Post)

        # Create test data
        users = [
            User(username="groupuser1", email="g1@example.com", password_hash="hash"),
            User(username="groupuser2", email="g2@example.com", password_hash="hash"),
            User(username="groupuser3", email="g3@example.com", password_hash="hash"),
        ]

        for user in users:
            sync_session.add(user)
        sync_session.commit()

        # User1: 3 posts, User2: 2 posts, User3: 0 posts
        for i in range(3):
            post = Post(user_id=users[0].id, title=f"Post {i}", content="Content")
            sync_session.add(post)

        for i in range(2):
            post = Post(user_id=users[1].id, title=f"Post {i}", content="Content")
            sync_session.add(post)

        sync_session.commit()

        # Test GROUP BY with COUNT
        # This depends on your GROUP BY implementation
        # Example:
        query = (
            select(User.username, "COUNT(*) AS post_count")
            .left_join(Post, Post.user_id == User.id)
            .group_by(User.username)
        )
        results = sync_session.exec(query).all()

        assert len(results) == 3
        # Sort by username for consistent ordering
        results_sorted = sorted(results, key=lambda x: x[0])

        assert results_sorted[0][0] == "groupuser1"
        assert results_sorted[0][1] == 3  # 3 posts

        assert results_sorted[1][0] == "groupuser2"
        assert results_sorted[1][1] == 2  # 2 posts

        assert results_sorted[2][0] == "groupuser3"
        # assert results_sorted[2][1] == 0  # 0 posts

    def test_subqueries(self, sync_session):
        """Test subquery operations"""

        sync_session.create_all(User, Post)

        # Create test data
        active_user = User(
            username="activeuser",
            email="active@example.com",
            password_hash="hash",
            is_active=True
        )

        inactive_user = User(
            username="inactiveuser",
            email="inactive@example.com",
            password_hash="hash",
            is_active=False
        )

        sync_session.add(active_user)
        sync_session.add(inactive_user)
        sync_session.commit()

        # Create posts for active user
        for i in range(3):
            post = Post(user_id=active_user.id, title=f"Active Post {i}", content="Content")
            sync_session.add(post)

        sync_session.commit()

        # Test subquery in WHERE
        # Get users who have posts
        subquery = select(Post.user_id).distinct()
        query = select(User).where(User.id.in_(subquery))
        results = sync_session.exec(query).all()

        assert len(results) == 1
        assert results[0].username == "activeuser"

    def test_transactions(self, sync_session):
        """Test transaction support"""

        sync_session.create_all(User)

        # Test successful transaction
        user1 = User(
            username="txuser1",
            email="tx1@example.com",
            password_hash="hash"
        )

        sync_session.add(user1)
        sync_session.commit()

        # Verify committed
        query = select(User).where(User.username == "txuser1")
        assert sync_session.exec(query).first() is not None

        # Test rollback
        try:
            user2 = User(
                username="txuser2",
                email="tx2@example.com",
                password_hash="hash"
            )
            sync_session.add(user2)
            # Intentionally cause an error
            sync_session.execute("INVALID SQL")
            sync_session.commit()
        except Exception:
            sync_session.rollback()

        # User2 should not exist
        query = select(User).where(User.username == "txuser2")
        assert sync_session.exec(query).first() is None

    def test_datetime_operations(self, sync_session):
        """Test datetime field operations"""

        sync_session.create_all(User)

        now = datetime.now()

        users = [
            User(
                username="timeuser1",
                email="time1@example.com",
                password_hash="hash",
                created_at=now - timedelta(days=2)
            ),
            User(
                username="timeuser2",
                email="time2@example.com",
                password_hash="hash",
                created_at=now - timedelta(days=1)
            ),
            User(
                username="timeuser3",
                email="time3@example.com",
                password_hash="hash",
                created_at=now
            ),
        ]

        for user in users:
            sync_session.add(user)
        sync_session.commit()

        # Test ordering by datetime
        query = select(User).order_by(User.created_at)
        results = sync_session.exec(query).all()

        assert [u.username for u in results] == ["timeuser1", "timeuser2", "timeuser3"]

        # Test filtering by datetime (if supported)
        yesterday = now - timedelta(days=1)
        query = select(User).where(User.created_at > yesterday)
        # query._bind(sync_session)
        results = sync_session.exec(query).all()
        assert len(results) == 1
        assert results[0].username == "timeuser3"