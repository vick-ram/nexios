from datetime import datetime
from typing import Optional, List

from nexios.orm.relationships import Relationship
from nexios.orm.fields import Field
from nexios.orm.tests.conftest import BaseTestModel


class Profile(BaseTestModel):
    __tablename__ = 'profiles'

    id: Optional[int] = Field(primary_key=True, auto_increment=True, default=None)
    user_id: int = Field(foreign_key="User.id", unique=True)
    bio: Optional[str] = Field(nullable=True, max_length=500)
    website: Optional[str] = Field(nullable=True)
    created_at: datetime = Field(default_factory=datetime.now)

    user: "User" = Relationship(back_populates="profile")


class Address(BaseTestModel):
    __tablename__ = "addresses"

    id: Optional[int] = Field(primary_key=True, auto_increment=True, default=None)
    user_id: int = Field(foreign_key="User.id")
    street: str = Field(max_length=200)
    city: str = Field(max_length=100)
    country: str = Field(max_length=100)
    zip_code: str = Field(max_length=20)

    user: "User" = Relationship(back_populates="addresses")


class Post(BaseTestModel):
    __tablename__ = "posts"

    id: Optional[int] = Field(primary_key=True, auto_increment=True, default=None)
    user_id: int = Field(foreign_key="User.id")
    title: str = Field(max_length=200)
    content: str
    published: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)

    user: "User" = Relationship(back_populates="posts")


class User(BaseTestModel):
    __tablename__ = "users"

    id: Optional[int] = Field(primary_key=True, auto_increment=True, default=None)
    username: str = Field(max_length=50, unique=True, index=True)
    email: str = Field(max_length=100, unique=True)
    password_hash: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    profile: Optional[Profile] = Relationship(
        back_populates="user",
        lazy="select"
    )

    addresses: List[Address] = Relationship(
        back_populates="user",
        lazy="select"
    )

    posts: List[Post] = Relationship(
        back_populates="user",
        lazy="dynamic"  # Test dynamic loading
    )
