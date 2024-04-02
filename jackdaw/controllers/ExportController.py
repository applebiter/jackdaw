import os
from configparser import ConfigParser
from typing import Type
from sqlalchemy.orm import Session
from jackdaw.controllers import BaseController
from jackdaw.models import User


class ExportController(BaseController):
    """Export controller encapsulates export functionality"""

    _export_root: str

    def __init__(self, session: Session, owner: Type[User]):
        """Initialize the class"""

        super().__init__(session, owner)

        try:

            config = ConfigParser()
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(__file__))
            )
            config.read(f"{project_root}/config.cfg")

            export_root = config.get("export", "root")
            self._export_root = export_root
            user_folder = f"{export_root}/{self._owner.uuid}"

            if not os.path.exists(user_folder):
                os.makedirs(user_folder)

        except Exception as e:
            raise e

    def __str__(self):
        """Return the class string representation."""
        return f"Jackdaw Application [alpha] Export Controller"

    def __repr__(self):
        """Return the class representation."""
        return f"{self.__class__.__name__}()"
