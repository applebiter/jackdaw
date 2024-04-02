from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, validates
from jackdaw.models import Base


class OllamaModel(Base):
    """OllamaTemplate stores the name of the model, a description of the model, the template, and an example of the
    model's use.
    """

    __tablename__ = "ollama_models"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    model: Mapped[str] = mapped_column(String(75), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    example: Mapped[str] = mapped_column(Text, nullable=True)
    priming: Mapped[str] = mapped_column(Text, nullable=True)
    params: Mapped[str] = mapped_column(Text, nullable=True)
    created: Mapped[str] = mapped_column(DateTime, default=str(datetime.now()))
    modified: Mapped[str] = mapped_column(
        DateTime, default=str(datetime.now()), onupdate=str(datetime.now())
    )

    def __repr__(self) -> str:
        return f"<OllamaModel(title={self.title}, model={self.model})>"

    def __str__(self) -> str:
        return f"{self.title} ({self.model})"

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "model": self.model,
            "description": self.description,
            "template": self.template,
            "example": self.example,
            "priming": self.priming,
            "params": self.params,
            "created": str(self.created),
            "modified": str(self.modified),
        }

    def unserialize(self, data: dict) -> "OllamaModel":
        self.title = data.get("title", self.title)
        self.model = data.get("model", self.model)
        self.description = data.get("description", self.description)
        self.template = data.get("template", self.template)
        self.example = data.get("example", self.example)
        self.priming = data.get("priming", self.priming)
        self.params = data.get("params", self.params)
        self.created = data.get("created", self.created)
        self.modified = data.get("modified", self.modified)

        return self

    @validates("title")
    def validate_title(self, key, title: str) -> str:
        """Validates the title's length.

        Parameters
        ----------
        title: str
            The character's title

        Returns
        -------
        str
            The validated title
        """

        if title and len(title) > 150:
            raise ValueError("The model's title must have no more than 150 characters.")

        return title

    @validates("model")
    def validate_model(self, key, model: str) -> str:
        """Validates the model's length.

        Parameters
        ----------
        model: str
            The character's model

        Returns
        -------
        str
            The validated model
        """

        if model and len(model) > 75:
            raise ValueError("The model's name must have no more than 75 characters.")

        return model

    @validates("description")
    def validate_description(self, key, description: str) -> str:
        """Validates the description's length.

        Parameters
        ----------
        description: str
            The character's description

        Returns
        -------
        str
            The validated description
        """

        if description and len(description) > 65535:
            raise ValueError("The model's description must have no more than 65,535 characters.")

        return description

    @validates("template")
    def validate_template(self, key, template: str) -> str:
        """Validates the template's length.

        Parameters
        ----------
        template: str
            The character's template

        Returns
        -------
        str
            The validated template
        """

        if template and len(template) > 65535:
            raise ValueError("The model's template must have no more than 65,535 characters.")

        return template

    @validates("example")
    def validate_example(self, key, example: str) -> str:
        """Validates the example's length.

        Parameters
        ----------
        example: str
            The character's example

        Returns
        -------
        str
            The validated example
        """

        if example and len(example) > 65535:
            raise ValueError("The model's example must have no more than 65,535 characters.")

        return example

    @validates("priming")
    def validate_priming(self, key, priming: str) -> str:
        """Validates the priming's length.

        Parameters
        ----------
        priming: str
            The character's priming

        Returns
        -------
        str
            The validated priming
        """

        if priming and len(priming) > 65535:
            raise ValueError("The model's priming must have no more than 65,535 characters.")

        return priming

    @validates("params")
    def validate_params(self, key, params: str) -> str:
        """Validates the params' length.

        Parameters
        ----------
        params: str
            The character's params

        Returns
        -------
        str
            The validated params
        """

        if params and len(params) > 65535:
            raise ValueError("The model's params must have no more than 65,535 characters.")

        return params