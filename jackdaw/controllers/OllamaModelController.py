from datetime import datetime
from typing import Type
from sqlalchemy.orm import Session
from jackdaw.controllers import BaseController
from jackdaw.models import User, OllamaModel


class OllamaModelController(BaseController):
    """Ollama model controller class
    """

    def __init__(self, session: Session, owner: Type[User]):
        """Initialize the class"""

        super().__init__(session, owner)

    def create_model(
        self, title: str, model: str, description: str = None,
        template: str = None, example: str = None, priming: str = None,
        params: str = None
    ) -> OllamaModel:
        """Create a model

        Parameters
        ----------
        title : str
            The title of the model
        model : str
            The model name
        description : str
            The model description
        template : str
            The model template
        example : str
            The model example
        priming : str
            The model priming
        params : str
            The model params

        Returns
        -------
        OllamaModel
            The model object
        """

        with self._session as session:

            try:

                created = datetime.now()
                modified = created

                model = OllamaModel(
                    title=title, model=model, description=description,
                    template=template, example=example, priming=priming,
                    params=params, created=created, modified=modified
                )

                session.add(model)

            except Exception as e:
                session.rollback()
                raise e

            else:
                session.commit()
                return model

    def get_model(self, model: str) -> Type[OllamaModel] | None:
        """Get an activity by id

        Parameters
        ----------

        Returns
        -------
        """

        with self._session as session:

            model = session.query(OllamaModel).filter(
                OllamaModel.model == model
            ).first()

            return model if model else None

    def get_models(self) -> list:
        """Get all models stored in the database

        Returns
        -------
        list
            A list of model objects
        """

        with self._session as session:

            return session.query(OllamaModel).all()

    def __str__(self):
        """Return the class string representation."""
        return f"Jackdaw Application [alpha] Ollama Model Controller"

    def __repr__(self):
        """Return the class representation."""
        return f"{self.__class__.__name__}()"
