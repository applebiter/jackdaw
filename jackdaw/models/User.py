from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from jackdaw.models import Assistance, Base
from validators import email as email_validator
from validators import uuid as uuid_validator


class User(Base):
    """The User class represents a user in the system.

    Attributes
    ----------
        id: int
            The user's id
        uuid: str
            The user's UUID
        username: str
            The user's username
        email: str
            The user's email address
        password: str
            The user's password hash
        is_active: bool
            The user's active status
        is_banned: bool
            The user's banned status
        created: str
            The creation datetime of the user
        modified: str
            The last modification datetime of the user

    Methods
    -------
        __repr__()
            Returns a string representation of the user
        __str__()
            Returns a string representation of the user
        serialize()
            Returns a dictionary representation of the user
        unserialize(data: dict)
            Updates the user's attributes with the values from the dictionary
        validate_uuid(uuid: str)
            Validates the UUID's length and format
        validate_username(username: str)
            Validates the username's length
        validate_email(email: str)
            Validates the email's length
        validate_password(password: str)
            Validates the password's length
    """

    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[str] = mapped_column(DateTime, default=str(datetime.now()))
    modified: Mapped[str] = mapped_column(
        DateTime, default=str(datetime.now()), onupdate=str(datetime.now())
    )
    assistances: Mapped[Optional[List["Assistance"]]] = relationship(
        "Assistance", back_populates="user",
        cascade="all, delete, delete-orphan")

    def __repr__(self):
        """Returns a string representation of the user.

        Returns
        -------
        str
            A string representation of the user
        """

        return f'<User {self.id!r} - {self.username!r}>'

    def __str__(self):
        """Returns a string representation of the user.

        Returns
        -------
        str
            A string representation of the user
        """

        return f'{self.id!r} - {self.username}'

    def serialize(self) -> dict:
        """Returns a dictionary representation of the user.

        Returns
        -------
        dict
            A dictionary representation of the user
        """

        return {
            'id': self.id,
            'uuid': self.uuid,
            'username': self.username,
            'password': self.password,
            'email': self.email,
            'is_active': self.is_active,
            'is_banned': self.is_banned,
            'created': str(self.created),
            'modified': str(self.modified),
        }

    def unserialize(self, data: dict) -> "User":
        """Updates the user's attributes with the values from the dictionary.

        Parameters
        ----------
        data: dict
            The dictionary with the new values for the user

        Returns
        -------
        User
            The unserialized user
        """

        self.uuid = data.get('uuid', self.uuid)
        self.username = data.get('username', self.username)
        self.email = data.get('email', self.email)
        self.is_active = data.get('is_active', self.is_active)
        self.is_banned = data.get('is_banned', self.is_banned)
        self.created = data.get('created', self.created)
        self.modified = data.get('modified', self.modified)

        return self

    @validates("uuid")
    def validate_uuid(self, key, uuid: str) -> str:
        """Validates the UUID's length and format.

        Parameters
        ----------
        uuid: str
            The user's UUID

        Returns
        -------
        str
            The validated UUID
        """

        if not uuid:
            raise ValueError("A user UUID is required.")

        if len(uuid) != 36:
            raise ValueError("The user UUID must have 36 characters.")

        if not uuid_validator(uuid):
            raise ValueError("The user UUID is not valid.")

        return uuid

    @validates("username")
    def validate_username(self, key, username: str) -> str:
        """Validates the username's length.

        Parameters
        ----------
        username: str
            The user's username

        Returns
        -------
        str
            The validated username
        """

        if not username:
            raise ValueError("A username is required.")

        if len(username) > 50:
            raise ValueError("The username can have no more than 50 characters.")

        return username

    @validates("email")
    def validate_email(self, key, email: str) -> str:
        """Validates the email's length.

        Parameters
        ----------
        email: str
            The user's email address

        Returns
        -------
        str
            The validated email
        """

        if not email:
            raise ValueError("An email address is required.")

        if len(email) > 100:
            raise ValueError("The email address can have no more than 100 characters.")

        if not email_validator(email):
            raise ValueError("The email address is not valid.")

        return email

    @validates("password")
    def validate_password(self, key, password: str) -> str:
        """Validates the password's length.

        Parameters
        ----------
        password: str
            The user's password hash

        Returns
        -------
        str
            The validated password
        """

        if not password:
            raise ValueError("A password is required.")

        if len(password) > 250:
            raise ValueError("The password can have no more than 250 characters.")

        return password