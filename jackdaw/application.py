import uuid as uniqueid
from datetime import datetime
import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from jackdaw.controllers import AssistantController, UserController, \
    OllamaModelController, ExportController, RecordingController
from jackdaw.models import Base, User


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


class Jackdaw:

    assistants: dict = {}

    def __init__(self, engine: str, echo: bool = False):

        self._engine = create_engine(engine, echo=echo)
        Base.metadata.create_all(self._engine)
        self._session = Session(bind=self._engine, expire_on_commit=False)

        self._owner = self._session.query(User).filter(
            User.username == "jackdaw"
        ).first()

        if self._owner is None:
            new_uuid = str(uniqueid.uuid4())
            username = "jackdaw"
            password = hash_password("password")
            email = "jackdaw@example.com"
            is_active = True
            is_banned = False
            created = datetime.now()
            modified = created
            user = User(
                uuid=new_uuid, username=username, password=password,
                email=email, is_active=is_active, is_banned=is_banned,
                created=created, modified=modified
            )
            self._session.add(user)
            self._session.commit()

        self._controllers = {
            "assistant": AssistantController(self._session, self._owner),
            "export": ExportController(self._session, self._owner),
            "ollama-model": OllamaModelController(self._session, self._owner),
            "recording": RecordingController(),
            "user": UserController(self._session, self._owner)
        }

    def __call__(self, *args, **kwargs):
        return self._controllers[args[0]]

    def __str__(self):
        return "Jackdaw Application [alpha]"

    def __repr__(self):
        return f"{self.__class__.__name__}()"