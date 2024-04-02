from typing import Type
from sqlalchemy.orm import Session
from noveler.models import User


class BaseController:
    """Base controller encapsulates common functionality for all controllers

    Attributes
    ----------
    _self : BaseController
        The instance of the base controller
    _owner : User
        The current user of the base controller
    _session : Session
        The database session
    """
    _self = None
    _owner = None
    _session = None

    def __new__(cls, session: Session, owner: Type[User]):
        """Enforce Singleton pattern"""

        if cls._self is None:
            cls._self = super().__new__(cls)

        return cls._self

    def __init__(self, session: Session, owner: Type[User]):
        """Initialize the class"""

        self._session = session
        self._owner = owner