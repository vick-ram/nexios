import pytest
from .test_models import User, Profile, Address, Post
from nexios.orm.query.builder import select


class TestRelationshipOperations:
    """Test relationship loading and operations"""

    def test_one_to_one_relationship(self, sync_session):
        """Test one-to-one relationship (User <-> Profile)"""
        sync_session.create_all(User, Profile)

        # Create user with profile
        user = User(
            username="profileuser",
            email="profile@example.com",
            password_hash="hash"
        )

        sync_session.add(user)
        sync_session.commit()

        profile = Profile(
            user_id=user.id,
            bio="Test bio",
            website="https://example.com"
        )

        sync_session.add(profile)
        sync_session.commit()

        print(f"User profile: {user.profile}")

        # Test forward relationship (User -> Profile)
        assert user.profile is not None # fails, profile is None
        assert user.profile.bio == "Test bio"
        assert user.profile.website == "https://example.com"

        # Test backward relationship (Profile -> User)
        assert profile.user is not None
        assert profile.user.username == "profileuser"
        assert profile.user.email == "profile@example.com"

        # Test foreign key is set
        assert profile.user_id == user.id

    def test_one_to_many_relationship(self, sync_session):
        """Test one-to-many relationship (User <-> Address)"""
        sync_session.create_all(User, Address, Post)

        # Create user with multiple addresses
        user = User(
            username="addressuser",
            email="address@example.com",
            password_hash="hash"
        )
        sync_session.add(user)
        sync_session.commit()

        addresses = [
            Address(user_id=user.id, street="123 Main St", city="City1", country="Country1", zip_code="12345"),
            Address(user_id=user.id, street="456 Oak Ave", city="City2", country="Country2", zip_code="67890"),
            Address(user_id=user.id, street="789 Pine Rd", city="City3", country="Country3", zip_code="11223"),
        ]

        for addr in addresses:
            sync_session.add(addr)
        sync_session.commit()

        posts = [
            Post(user_id=user.id, title="Post 1", content="Content 1"),
            Post(user_id=user.id, title="Post 2", content="Content 2"),
        ]

        for post in posts:
            sync_session.add(post)
        sync_session.commit()

        print(f"all addresses: {sync_session.exec(select(Address)).all()}") # This works

        print(f"User addresses: {user.addresses}")

        print(f"User posts: {user.posts}")

        # Test forward relationship (User -> Addresses)
        assert len(user.addresses) == 3
        assert {addr.street for addr in user.addresses} == {
            "123 Main St", "456 Oak Ave", "789 Pine Rd"
        }

        # Test backward relationship (Address -> User)
        for addr in addresses:
            assert addr.user is not None
            assert addr.user.username == "addressuser"
            assert addr.user_id == user.id

        # Test querying through relationship
        address_query = select(Address).where(Address.user_id == user.id)
        user_addresses = sync_session.exec(address_query).all()
        assert len(user_addresses) == 3

    def test_many_to_one_relationship(self, sync_session):
        """Test many-to-one relationship (Post -> User)"""
        sync_session.create_all(User, Post)

        user = User(
            username="postuser",
            email="post@example.com",
            password_hash="hash"
        )
        sync_session.add(user)
        sync_session.commit()

        posts = [
            Post(user_id=user.id, title="Post 1", content="Content 1"),
            Post(user_id=user.id, title="Post 2", content="Content 2"),
            Post(user_id=user.id, title="Post 3", content="Content 3"),
        ]

        for post in posts:
            sync_session.add(post)
        sync_session.commit()

        # Test forward relationship (Post -> User)
        for post in posts:
            assert post.user is not None
            assert post.user.username == "postuser"
            assert post.user_id == user.id

        # Test backward relationship (User -> Posts) with dynamic loading
        posts_query = user.posts  # This should return a query object

        # Apply filters to the dynamic query
        posts_query = posts_query.where(Post.title.like("Post %"))
        user_posts = sync_session.exec(posts_query).all()

        assert len(user_posts) == 3
        assert {post.title for post in user_posts} == {"Post 1", "Post 2", "Post 3"}

    def test_eager_loading(self, sync_session):
        """Test eager loading of relationships"""
        sync_session.create_all(User, Profile, Address, Post)

        # Create test data
        user = User(
            username="eageruser",
            email="eager@example.com",
            password_hash="hash"
        )
        sync_session.add(user)
        sync_session.commit()

        profile = Profile(user_id=user.id, bio="Eager bio", website="https://example.com")
        address1 = Address(user_id=user.id, street="123 St", city="City", country="Country", zip_code="12345")
        address2 = Address(user_id=user.id, street="456 St", city="City", country="Country", zip_code="67890")
        post = Post(user_id=user.id, title="Eager Post", content="Content")

        sync_session.add(profile)
        sync_session.add(address1)
        sync_session.add(address2)
        sync_session.add(post)
        sync_session.commit()

        # Test eager loading with .eager_load()
        query = select(User).where(User.username == "eageruser").eager_load("profile", "addresses")
        eager_user = sync_session.exec(query).first()

        # Profile and addresses should be loaded
        assert eager_user.profile is not None # fails, profile is None
        assert eager_user.profile.bio == "Eager bio"
        assert len(eager_user.addresses) == 2

    def test_lazy_loading_strategies(self, sync_session):
        """Test different lazy loading strategies"""
        sync_session.create_all(User, Post)

        user = User(
            username="lazyuser",
            email="lazy@example.com",
            password_hash="hash"
        )

        sync_session.add(user)
        sync_session.commit()

        # Test dynamic lazy loading
        posts_query = user.posts  # Returns query, not results
        assert hasattr(posts_query, 'where')  # Should be a query object

        # Test select lazy loading (default)
        # When we access the relationship, it should load
        new_posts = Post(user_id=user.id, title="Lazy Post", content="Content")
        sync_session.add(new_posts)
        sync_session.commit()

        # The posts should be accessible
        assert len(sync_session.exec(user.posts).all()) == 1  # all() on the query

    def test_cascade_operations(self, sync_session):
        """Test cascade operations (if implemented)"""
        sync_session.create_all(User, Profile)

        user = User(
            username="cascadeuser",
            email="cascade@example.com",
            password_hash="hash"
        )
        sync_session.add(user)
        sync_session.commit()

        profile = Profile(user_id=user.id, bio="Cascade bio", website="https://example.com")

        sync_session.add(profile)
        sync_session.commit()

        # Test that profile has user_id set
        assert profile.user_id == user.id

        # If cascade delete is implemented:
        # sync_session.delete(user)
        # sync_session.commit()
        #
        # # Profile should also be deleted
        # query = select(Profile).where(Profile.id == profile.id)
        # query._bind(sync_session)
        # assert query._first() is None

    def test_relationship_setter(self, sync_session):
        """Test setting relationships"""
        sync_session.create_all(User, Profile)

        user = User(
            username="setteruser",
            email="setter@example.com",
            password_hash="hash"
        )

        sync_session.add(user)
        sync_session.commit()

        profile = Profile(
            user_id=user.id or 1,
            bio="Setter bio",
            website="https://example.com"
            )

        sync_session.add(profile)
        sync_session.commit()

        # Set relationship
        user.profile = profile
        # Profile should automatically get user reference
        # assert profile.user is user

        # Verify foreign key is set
        assert profile.user_id == user.id