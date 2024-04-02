from datetime import datetime
from sqlalchemy import Integer, ForeignKey, String, Text, Float, Boolean, BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from jackdaw.models import Base, User


class Assistance(Base):
    """The Assistance class represents an assistance request.

    Attributes
    ----------
    id: int
        The assistance's id
    user_id: int
        The id of the current user
    session_uuid: str
        The UUID of the session to be used when making the request. If other
        messages in the database have the same session_uuid value, they will be
        loaded in order of their creation date, and the assistant will continue
        from the last message in the session.
    assistant: str
        The assistant to be used when making the request.
    model: str
        The model to be used when making the request.
    priming: str
        The priming to be used when making the request.
    prompt: str
        The prompt to be used when making the request.
    temperature: float
        The temperature to be used when making the request.
    seed: int
        The seed to be used when making the request.
    content: str
        The message to be used when making the request.
    done: bool
        Whether the assistance is done or not
    total_duration: int
        The total duration of the assistance (ns)
    load_duration: int
        The duration of the loading of the assistance (ns)
    prompt_eval_count: int
        The number of prompt evaluations
    prompt_eval_duration: int
        The duration of the prompt evaluations (ns)
    eval_count: int
        The number of evaluations
    eval_duration: int
        The duration of the evaluations (ns)
    created: str
        The assistance's creation date in datetime form: yyy-mm-dd hh:mm:ss.f
    """

    __tablename__ = 'assistances'
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    session_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    assistant: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    priming: Mapped[str] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=True)
    temperature: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5
    )
    seed: Mapped[int] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    total_duration: Mapped[int] = mapped_column(
        BigInteger, nullable=True, default=0
    )
    load_duration: Mapped[int] = mapped_column(
        BigInteger, nullable=True, default=0
    )
    prompt_eval_count: Mapped[int] = mapped_column(
        BigInteger, nullable=True, default=0,
    )
    prompt_eval_duration: Mapped[int] = mapped_column(
        BigInteger, nullable=True, default=0
    )
    eval_count: Mapped[int] = mapped_column(
        BigInteger, nullable=True, default=0
    )
    eval_duration: Mapped[int] = mapped_column(
        BigInteger, nullable=True, default=0
    )
    created: Mapped[str] = mapped_column(DateTime, default=str(datetime.now()))
    user: Mapped["User"] = relationship(
        "User", back_populates="assistances"
    )

    def __repr__(self):
        """Returns a string representation of the assistance.

        Returns
        -------
        str
            A string representation of the assistance
        """

        return f'<Assistant {self.assistant!r}>'

    def __str__(self):
        """Returns a string representation of the assistance.

        Returns
        -------
        str
            A string representation of the assistance
        """

        return f'Assistant: {self.assistant}'

    def serialize(self) -> dict:
        """Returns a dictionary representation of the assistance.

        Returns
        -------
        dict
            A dictionary representation of the assistance
        """

        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_uuid': self.session_uuid,
            'assistant': self.assistant,
            'model': self.model,
            'priming': self.priming,
            'prompt': self.prompt,
            'temperature': self.temperature,
            'seed': self.seed,
            'content': self.content,
            'done': self.done,
            'total_duration': self.total_duration,
            'load_duration': self.load_duration,
            'prompt_eval_count': self.prompt_eval_count,
            'prompt_eval_duration': self.prompt_eval_duration,
            'eval_count': self.eval_count,
            'eval_duration': self.eval_duration,
            'created': str(self.created),
        }

    def unserialize(self, data: dict) -> "Assistance":
        """Updates the assistance's attributes with the values from the dictionary.

        Returns
        -------
        Assistance
            The updated assistance
        """

        self.id = data.get('id', self.id)
        self.user_id = data.get('user_id', self.user_id)
        self.session_uuid = data.get('session_uuid', self.session_uuid)
        self.assistant = data.get('assistant', self.assistant)
        self.model = data.get('model', self.model)
        self.priming = data.get('priming', self.priming)
        self.prompt = data.get('prompt', self.prompt)
        self.temperature = data.get('temperature', self.temperature)
        self.seed = data.get('seed', self.seed)
        self.content = data.get('content', self.content)
        self.done = data.get('done', self.done)
        self.total_duration = data.get('total_duration', self.total_duration)
        self.load_duration = data.get('load_duration', self.load_duration)
        self.prompt_eval_count = data.get('prompt_eval_count', self.prompt_eval_count)
        self.prompt_eval_duration = data.get('prompt_eval_duration', self.prompt_eval_duration)
        self.eval_count = data.get('eval_count', self.eval_count)
        self.eval_duration = data.get('eval_duration', self.eval_duration)
        self.created = data.get('created', self.created)

        return self