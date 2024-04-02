import uuid
from datetime import datetime
from typing import Type
import bcrypt
from sqlalchemy import func
from sqlalchemy.orm import Session
import jackdaw
from jackdaw.controllers.BaseController import BaseController
from jackdaw.models import User


def hash_password(password: str) -> str:
    """Hash a password, return hashed password"""

    if password == '':
        raise ValueError('The password cannot be empty.')

    if len(password) < 8:
        raise ValueError('The password must be at least 8 characters.')

    if len(password) > 24:
        raise ValueError('The password cannot be more than 24 characters.')

    return bcrypt.hashpw(
        password.encode('utf8'), bcrypt.gensalt(rounds=12)
    ).decode('utf8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password, return true if verified, false if not"""

    return bcrypt.checkpw(
        password.encode('utf8'), hashed_password.encode('utf8')
    )


class UserController(BaseController):
    """User controller encapsulates user management functionality

    Attributes
    ----------
    _self : UserController
        The instance of the user controller
    _owner : User
        The current user of the user controller
    _session : Session
        The database session

    Methods
    -------
    create_user(username: str, password: str, email: str)
        Create a new user
    register_user(username: str, password: str, repassword: str, email: str, reemail: str)
        Register a new user identity
    activate_user(user_id: int)
        Activate a user
    deactivate_user(user_id: int)
        Deactivate a user
    login(username: str, password: str)
        User login
    change_password(user_id: int, old_password: str, new_password, repassword: str)
        Change user password
    delete_user(user_id: int)
        Delete a user
    get_user_by_id(user_id: int)
        Get a user by id
    get_user_by_uuid(user_uuid: str)
        Get a user by uuid
    get_user_by_username(username: str)
        Get a user by username
    get_user_by_email(email: str)
        Get a user by email
    get_user_count()
        Get user count
    get_all_users()
        Get all users
    get_all_users_page(page: int, per_page: int)
        Get a single page of users from the database
    search_users(search: str)
        Search for users by username or email
    """

    def __init__(self, session: Session, owner: Type[User]):
        """Initialize the class"""

        super().__init__(session, owner)

    def create_user(self, username: str, password: str, email: str) -> User:
        """Create a new user

        This method is available to the desktop application owner and the web application owner. It is not available to
        secondary users of the desktop application or the web application. The method first checks if the username or
        email already exists. If either exists, an exception is raised. If neither exists, the method creates a new user
        and logs the activity. The method returns the new user's id on success and nothing on failure.

        Parameters
        ----------
        username : str
            The username of the new user
        password : str
            The password of the new user
        email : str
            The email of the new user

        Returns
        -------
        User
            The new user object
        """

        with self._session as session:

            try:

                username_exists = session.query(User).filter(
                    User.username == username
                ).first()

                if username_exists:
                    raise Exception('That username already exists.')

                email_exists = session.query(User).filter(
                    User.email == email
                ).first()

                if email_exists:
                    raise Exception('That email already exists.')

                uuid4 = str(uuid.uuid4())
                uuid_exists = session.query(User).filter(
                    User.uuid == uuid4
                ).first()

                while uuid_exists:

                    uuid4 = str(uuid.uuid4())
                    uuid_exists = session.query(User).filter(
                        User.uuid == uuid4
                    ).first()

                password = jackdaw.application.hash_password(password)
                created = datetime.now()
                modified = created

                user = User(
                    uuid=uuid4, username=username, password=password,
                    email=email, created=created, modified=modified,
                    is_active=True
                )

                session.add(user)

            except Exception as e:
                session.rollback()
                raise e

            else:
                session.commit()
                return user

    def register_user(self, username: str, password: str, repassword: str, email: str, reemail: str) -> User:
        """Register a new user identity

        This method is for self-registration of new users. It is available to secondary users of the website and the
        desktop application. The method first checks if the username or email already exists. If either exists, an
        exception is raised. If neither exists, the method creates a new user and logs the activity. The method returns
        the new user's id on success and nothing on failure.

        Parameters
        ----------
        username : str
            The username of the new user
        password : str
            The password of the new user
        repassword : str
            The password of the new user repeated
        email : str
            The email of the new user
        reemail : str
            The email of the new user repeated

        Returns
        -------
        int
            The id of the new user on success
        """

        with self._session as session:

            try:

                username_exists = session.query(User).filter(User.username == username).first()

                if username_exists:
                    raise Exception('That username already exists.')

                if email != reemail:
                    raise Exception('The email addresses do not match.')

                email_exists = session.query(User).filter(User.email == email).first()

                if email_exists:
                    raise Exception('That email address already exists.')

                if password != repassword:
                    raise Exception('The passwords do not match.')

                uuid4 = str(uuid.uuid4())
                uuid_exists = session.query(User).filter(User.uuid == uuid4).first()

                while uuid_exists:
                    uuid4 = str(uuid.uuid4())
                    uuid_exists = session.query(User).filter(User.uuid == uuid4).first()

                password = jackdaw.application.hash_password(password)
                created = datetime.now()
                modified = created
                user = User(
                    uuid=uuid4, username=username, password=password,
                    email=email, created=created, modified=modified,
                    is_active=False
                )

                session.add(user)

            except Exception as e:
                session.rollback()
                raise e

            else:
                session.commit()
                return user

    def activate_user(self, user_id: int) -> Type[User]:
        """Activate a user

        Parameters
        ----------
        user_id: int
            The id of the user to activate

        Returns
        -------
        User
            The activated user object
        """

        with self._session as session:

            user = session.query(User).filter(User.id == user_id).first()

            if not user:
                raise ValueError('User not found.')

            try:
                user.is_active = True
                user.modified = datetime.now()

                session.add(user)

            except Exception as e:
                session.rollback()
                raise e

            else:
                session.commit()
                return user

    def deactivate_user(self, user_id: int) -> Type[User]:
        """Deactivate a user

        Parameters
        ----------
        user_id: int
            The id of the user to deactivate

        Returns
        -------
        User
            The deactivated user object
        """

        with self._session as session:

            user = session.query(User).filter(User.id == user_id).first()

            if not user:
                raise ValueError('User not found.')

            try:
                user.is_active = False
                user.modified = datetime.now()

                session.add(user)

            except Exception as e:
                session.rollback()
                raise e

            else:
                session.commit()
                return user

    def login(self, username: str, password: str) -> Type[User]:
        """User login

        Parameters
        ----------
        username : str
            The username of the user
        password : str
            The password of the user

        Returns
        -------
        User
            The user object on success
        """

        with self._session as session:

            try:
                candidate = session.query(User).filter(
                    User.username == username
                ).first()

                if not candidate:
                    raise Exception('User not found.')

                if not jackdaw.application.verify_password(
                        password, candidate.password
                ):
                    raise ValueError('Invalid password.')

            except Exception as e:
                session.rollback()
                raise e

            else:
                session.commit()
                return candidate

    def change_password(
        self, user_id: int, old_password: str, new_password, repassword: str
    ) -> Type[User]:
        """Change user password

        Parameters
        ----------
        user_id : int
            The id of the user
        old_password : str
            The old password of the user
        new_password : str
            The new password of the user
        repassword : str
            The new password of the user repeated

        Returns
        -------
        User
            The user object on success
        """

        user = self.get_user_by_id(user_id)

        if not user:
            raise ValueError('User not found.')

        if not jackdaw.application.verify_password(old_password, user.password):
            raise ValueError('Invalid password.')

        if new_password != repassword:
            raise ValueError('The new passwords do not match.')

        new_password = jackdaw.application.hash_password(new_password)
        user.password = new_password
        user.modified = str(datetime.now())

        with self._session as session:

            try:

                session.add(user)

            except Exception as e:
                session.rollback()
                raise e

            else:
                session.commit()
                return user

    def delete_user(self, user_id: int) -> bool:
        """Delete a user

        Parameters
        ----------
        user_id : int
            The id of the user to delete

        Returns
        -------
        bool
            True on success
        """

        with self._session as session:

            try:
                user = session.query(User).filter(User.id == user_id).first()

                if not user:
                    raise ValueError('User not found.')

                session.delete(user)

            except Exception as e:
                session.rollback()
                raise e

            else:
                session.commit()
                return True

    def get_user_by_id(self, user_id: int) -> Type[User] | None:
        """Get a user by id

        Parameters
        ----------
        user_id : int
            The id of the user to get

        Returns
        -------
        User
            The user
        """

        with self._session as session:
            user = session.query(User).filter(User.id == user_id).first()

            if user:
                return user

            return None

    def get_user_by_uuid(self, user_uuid: str) -> Type[User] | None:
        """Get a user by uuid

        Parameters
        ----------
        user_uuid : str
            The uuid of the user to get

        Returns
        -------
        User
            The user
        """

        with self._session as session:
            user = session.query(User).filter(User.uuid == user_uuid).first()

            if user:
                return user

            return None

    def get_user_by_username(self, username: str) -> Type[User] | None:
        """Get a user by username

        Parameters
        ----------
        username : str
            The username of the user to get

        Returns
        -------
        User
            The user
        """

        with self._session as session:
            user = session.query(User).filter(User.username == username).first()

            if user:
                return user

            return None

    def get_user_by_email(self, email: str) -> Type[User] | None:
        """Get a user by email

        Parameters
        ----------
        email : str
            The email of the user to get

        Returns
        -------
        User
            The user
        """

        with self._session as session:
            user = session.query(User).filter(User.email == email).first()

            if user:
                return user

            return None

    def get_user_count(self) -> int:
        """Get user count

        Returns
        -------
        int
            The number of users
        """

        with self._session as session:
            return session.query(func.count(User.id)).scalar()

    def get_all_users(self) -> list:
        """Get all users

        Returns
        -------
        list
            A list of users
        """

        with self._session as session:
            return session.query(User).all()

    def get_all_users_page(self, page: int, per_page: int) -> list:
        """Get a single page of users from the database

        Parameters
        ----------
        page : int
            The page number
        per_page : int
            The number of rows per page

        Returns
        -------
        list
            A list of users
        """

        with self._session as session:
            offset = (page - 1) * per_page
            return session.query(User).offset(offset).limit(per_page).all()

    def search_users(self, search: str) -> list:
        """Search for users by username or email

        Parameters
        ----------
        search : str
            The search string

        Returns
        -------
        list
            A list of users
        """

        with self._session as session:
            return session.query(User).filter(
                User.username.like(f'%{search}%') | User.email.like(f'%{search}%')
            ).all()
