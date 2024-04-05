import base64
import os
import uuid
from configparser import ConfigParser
from datetime import datetime
from typing import Type, Optional, Union, List, Literal, Mapping, Any
from langchain_community.document_loaders.text import TextLoader
from langchain_community.embeddings.ollama import OllamaEmbeddings
from langchain_community.vectorstores.chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ollama import Client, Message
from sqlalchemy.orm import Session
from jackdaw.controllers.BaseController import BaseController
from jackdaw.models import User, Assistance, OllamaModel


class AssistantController(BaseController):
    """Assistant Controller

    Attributes
    ----------
    _session_uuid : str
        The UUID of the session.
    _client : OllamaClient
        The Ollama client to be used when making requests.
    _chat_model : str
        The model to be used when chatting.
    _chat_num_ctx : int
        The number of tokens to use as context for the model.
    _chat_keep_alive : Union[float, str]
        The duration to keep the model in memory.
    _generative_model : str
        The model to be used when generating text.
    _generative_num_ctx : int
        The number of tokens to use as context for the model.
    _generative_keep_alive : Union[float, str]
        The duration to keep the model in memory.
    _multimodal_model : str
        The model to be used when describing images.
    _multimodal_num_ctx : int
        The number of tokens to use as context for the model.
    _multimodal_keep_alive : Union[float, str]
        The duration to keep the model in memory.
    _templates : dict
        The templates to be used when generating text.

    Methods
    -------
    chat(
        prompt: str,
        temperature: Optional[float] = 0.5,
        seed: Optional[int] = None,
        priming: str = None,
        options: Optional[dict] = None,
        session_uuid: str = None,
        keep_alive: Optional[Union[float, str]] = None
    )
    generate(
        prompt: str = None,
        temperature: Optional[float] = 0.5,
        seed: Optional[int] = None,
        priming: Optional[str] = None,
        options: Optional[dict] = None,
        session_uuid: str = None,
        keep_alive: Optional[Union[float, str]] = None
    )
        Generate text based on a prompt.
    describe_image(
        images: List[str],
        prompt: Optional[str] = "Describe the image",
        temperature: Optional[float] = 0.5,
        seed: Optional[int] = None,
        priming: Optional[str] = None,
        options: Optional[dict] = None,
        session_uuid: str = None,
        keep_alive: Optional[Union[float, str]] = None
    )
        Describe the contents of an image using the Ollama API.
    get_by_session_uuid(session_uuid: str)
        Get all Assistance messages by session UUID.
    """

    _templates = {}

    def __init__(self, session: Session, owner: Type[User]):

        super().__init__(session, owner)

        uuid4 = str(uuid.uuid4())
        uuid_exists = session.query(Assistance).filter(
            Assistance.session_uuid == uuid4
        ).first()

        while uuid_exists:
            uuid4 = str(uuid.uuid4())
            uuid_exists = session.query(Assistance).filter(
                Assistance.session_uuid == uuid4
            ).first()

        config = ConfigParser()
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        config.read(f"{project_root}/config.cfg")
        ollama_url = config.read("ollama", "url")
        self._client = Client(host=ollama_url)  # If I make this a string instead of a bytearray, the ollama code breaks
        self._session_uuid = uuid4
        self._chat_model = config.get("ollama", "chat_model")
        self._chat_num_ctx = config.getint("ollama", "chat_context_window")
        self._chat_keep_alive = config.get("ollama", "chat_memory_duration")
        self._generative_model = config.get("ollama", "generative_model")
        self._generative_num_ctx = config.getint("ollama", "generative_context_window")
        self._generative_keep_alive = config.get("ollama", "generative_memory_duration")
        self._multimodal_model = config.get("ollama", "multimodal_model")
        self._multimodal_num_ctx = config.getint("ollama", "multimodal_context_window")
        self._multimodal_keep_alive = config.get("ollama", "multimodal_memory_duration")

        self.update_models()

    def update_models(self) -> bool:
        """Update the database with any new models in the list provided by the Ollama API.
        """

        try:

            olist = self._client.list()

            if olist:

                for model in olist["models"]:
                    model_exists = self._session.query(OllamaModel).filter(
                        OllamaModel.model == model["model"]
                    ).first()

                    if not model_exists:
                        details = self._client.show(model["model"])

                        description = details["modelfile"] if details.get("modelfile") else None
                        parameters = details["parameters"] if details.get("parameters") else None
                        template = details["template"] if details.get("template") else None
                        priming = details["system"] if details.get("system") else None

                        created = datetime.now()
                        modified = created

                        ollama_model = OllamaModel(
                            title=model["model"], model=model["model"],
                            description=description, template=template,
                            example=None, priming=priming, params=parameters,
                            created=created, modified=modified
                        )

                        self._session.add(ollama_model)
                        self._session.commit()

                # delete models from db where existing model does not appear in
                # the olist

                with self._session as session:

                    try:

                        models = session.query(OllamaModel).all()

                        for model in models:
                            model_exists = False

                            for omodel in olist["models"]:
                                if model.model == omodel["model"]:
                                    model_exists = True
                                    break

                            if not model_exists:
                                session.delete(model)

                    except Exception as e:
                        session.rollback()
                        return False

                    else:
                        session.commit()

        except Exception as e:
            self._session.rollback()
            return False

        return True

    def chat(
            self,
            prompt: str,
            temperature: Optional[float] = 0.5,
            seed: Optional[int] = None,
            priming: str = None,
            options: Optional[dict] = None,
            session_uuid: str = None,
            keep_alive: Optional[Union[float, str]] = None
    ):
        """Chat with the Chat Assistant.

        The temperature parameter is a float value between 0 and 1. Anything
        greater than 0 will make the assistant more creative, but also more
        unpredictable. The seed parameter is an integer value that can be used
        to make the assistant's responses more predictable. If the temperature
        is set to 0, then the assistant's response will be reproducible, given
        the same seed value.

        Parameters
        ----------
        prompt : str
            The prompt to be used when chatting with the assistant.
        temperature : Optional[float]
            The temperature to be used when making the request. Defaults to
            0.5.
        seed : Optional[int]
            The seed to be used when making the request. Defaults to None.
        priming : Optional[str]
            The priming to be used when chatting with the assistant. Defaults to
            None.
        options : Optional[dict]
            The options to be used when making the request.
        session_uuid : str
            The UUID of the LM session to be used when making the request.
        keep_alive : Optional[Union[float, str]]
            The keep alive value to be used when making the request.
        """

        with self._session as session:

            model = session.query(OllamaModel).filter(
                OllamaModel.model == self._chat_model
            ).first()

        messages = []

        if model:
            if priming is not None:
                messages.append(Message(role="system", content=priming))

        session_uuid = self._session_uuid if not session_uuid else session_uuid

        with self._session as session:

            assistances = session.query(Assistance).filter_by(
                session_uuid=session_uuid
            ).order_by(Assistance.created).all()

            if assistances:
                for assistance in assistances:
                    messages.append(Message(
                        role="user", content=assistance.prompt
                    ))
                    messages.append(Message(
                        role="assistant", content=assistance.content
                    ))

        messages.append(Message(role="user", content=prompt))

        if not options:
            options = {
                "temperature": temperature,
                "num_ctx": self._chat_num_ctx
            }

        if not options.get("temperature"):
            options["temperature"] = temperature

        if not options.get("num_ctx"):
            options["num_ctx"] = self._chat_num_ctx

        keep_alive = self._chat_keep_alive if not keep_alive else keep_alive

        with self._session as session:

            try:

                response = self._client.chat(
                    model=self._chat_model,
                    messages=messages,
                    format='',
                    options=options,
                    keep_alive=keep_alive
                )

                assistance = Assistance(
                    user_id=self._owner.id,
                    session_uuid=session_uuid,
                    assistant="Chat Assistant",
                    model=self._chat_model,
                    priming=priming,
                    prompt=prompt,
                    temperature=temperature,
                    seed=seed,
                    content=response["message"]["content"] if response.get("message") else None,
                    done=response["done"],
                    total_duration=response["total_duration"] if response.get("total_duration") else None,
                    load_duration=response["load_duration"] if response.get("load_duration") else None,
                    prompt_eval_count=response["prompt_eval_count"] if response.get("prompt_eval_count") else None,
                    prompt_eval_duration=response["prompt_eval_duration"] if response.get(
                        "prompt_eval_duration") else None,
                    eval_count=response["eval_count"] if response.get("eval_count") else None,
                    eval_duration=response["eval_duration"] if response.get("eval_duration") else None,
                    created=datetime.now()
                )

                summary = f"{self._owner.username} used the Chat Assistant"

                session.add(assistance)

            except Exception as e:
                session.rollback()
                raise e

            else:
                session.commit()
                return response

    def rag_chat(
            self,
            prompt: str,
            document: str,
            temperature: Optional[float] = 0.5,
            seed: Optional[int] = None,
            priming: str = None,
            options: Optional[dict] = None,
            session_uuid: str = None,
            keep_alive: Optional[Union[float, str]] = None
    ):
        with self._session as session:

            model = session.query(OllamaModel).filter(
                OllamaModel.model == self._chat_model
            ).first()

        messages = []

        if model:
            if priming is not None:
                messages.append(Message(role="system", content=priming))

        session_uuid = self._session_uuid if not session_uuid else session_uuid

        with self._session as session:

            assistances = session.query(Assistance).filter_by(
                session_uuid=session_uuid
            ).order_by(Assistance.created).all()

            if assistances:
                for assistance in assistances:
                    messages.append(Message(
                        role="user", content=assistance.prompt
                    ))
                    messages.append(Message(
                        role="assistant", content=assistance.content
                    ))

        # RAG chain here
        loader = TextLoader(document)
        input_docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        splits = text_splitter.split_documents(input_docs)
        # Create Ollama embeddings and vector store
        embeddings = OllamaEmbeddings(model="nous-hermes:7b")
        vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
        # Create the retriever
        retriever = vectorstore.as_retriever()
        retrieved_docs = retriever.invoke(prompt)
        formatted_context = "\n\n".join(doc.page_content for doc in retrieved_docs)
        formatted_prompt = f"Question: {prompt}\n\nContext: {formatted_context}"
        messages.append(Message(role="user", content=formatted_prompt))

        if not options:
            options = {
                "temperature": temperature,
                "num_ctx": self._chat_num_ctx
            }

        if not options.get("temperature"):
            options["temperature"] = temperature

        if not options.get("num_ctx"):
            options["num_ctx"] = self._chat_num_ctx

        keep_alive = self._chat_keep_alive if not keep_alive else keep_alive

        with self._session as session:

            try:

                response = self._client.chat(
                    model=self._chat_model,
                    messages=messages,
                    format='',
                    options=options,
                    keep_alive=keep_alive
                )

                assistance = Assistance(
                    user_id=self._owner.id,
                    session_uuid=session_uuid,
                    assistant="RAG Chat Assistant",
                    model=self._chat_model,
                    priming=priming,
                    prompt=prompt,
                    temperature=temperature,
                    seed=seed,
                    content=response["message"]["content"] if response.get("message") else None,
                    done=response["done"],
                    total_duration=response["total_duration"] if response.get("total_duration") else None,
                    load_duration=response["load_duration"] if response.get("load_duration") else None,
                    prompt_eval_count=response["prompt_eval_count"] if response.get("prompt_eval_count") else None,
                    prompt_eval_duration=response["prompt_eval_duration"] if response.get(
                        "prompt_eval_duration") else None,
                    eval_count=response["eval_count"] if response.get("eval_count") else None,
                    eval_duration=response["eval_duration"] if response.get("eval_duration") else None,
                    created=datetime.now()
                )

                summary = f"{self._owner.username} used the Chat Assistant"

                session.add(assistance)

            except Exception as e:
                session.rollback()
                raise e

            else:
                session.commit()
                return response

    def describe_image(
            self,
            images: List[str],
            prompt: Optional[str] = "Describe the image",
            temperature: Optional[float] = 0.5,
            seed: Optional[int] = None,
            priming: Optional[str] = None,
            return_format: Literal['', 'json'] = '',
            options: Optional[dict] = None,
            session_uuid: str = None,
            keep_alive: Optional[Union[float, str]] = None
    ):
        """Describe the contents of an image using the Ollama API.

        Parameters
        ----------
        images : List[str]
            A list of image file paths to be described.
        temperature : Optional[float]
            The temperature to be used when making the request. Defaults to
            0.5.
        seed : Optional[int]
            The seed to be used when making the request. Defaults to None.
        prompt : Optional[str]
            The prompt to be used when requesting the description. Defaults to
            "Describe the contents of the image:".
        priming : Optional[str]
            The priming to be used when describing the image.
        return_format : str
            The format to be used to return the request.
        options : Optional[dict]
            The options to be used when making the request.
        session_uuid : str
            The UUID of the session to be used when making the request.
        keep_alive : Optional[Union[float, str]]
            The keep alive value to be used when making the request.
        """
        encoded_images = []

        for image in images:
            with open(image, "rb") as file:
                encoded_images.append(base64.b64encode(file.read()).decode())

        template = [template for template in self._templates if template.model == self._multimodal_model][0]

        if not priming:
            priming = template.priming

        session_uuid = self._session_uuid if not session_uuid else session_uuid

        if not options:
            options = {
                "temperature": temperature,
                "num_ctx": self._multimodal_num_ctx
            }

        if not options.get("temperature"):
            options["temperature"] = temperature

        if not options.get("num_ctx"):
            options["num_ctx"] = self._multimodal_num_ctx

        keep_alive = self._multimodal_keep_alive if not keep_alive else keep_alive

        with self._session as session:

            try:

                response = self._client.generate(
                    model=self._multimodal_model, prompt=prompt, system=priming,
                    template=template.template, context=None, stream=False,
                    raw=False, format=return_format, images=encoded_images,
                    options=options, keep_alive=keep_alive
                )

                content = response["response"] if response.get("response") else None

                assistance = Assistance(
                    user_id=self._owner.id,
                    session_uuid=session_uuid,
                    assistant="Multimodal Assistant",
                    model=self._multimodal_model,
                    priming=priming,
                    prompt=prompt,
                    temperature=temperature,
                    seed=seed,
                    content=content,
                    done=response["done"],
                    total_duration=response["total_duration"] if response.get("total_duration") else None,
                    load_duration=response["load_duration"] if response.get("load_duration") else None,
                    prompt_eval_count=response["prompt_eval_count"] if response.get("prompt_eval_count") else None,
                    prompt_eval_duration=response["prompt_eval_duration"] if response.get(
                        "prompt_eval_duration") else None,
                    eval_count=response["eval_count"] if response.get("eval_count") else None,
                    eval_duration=response["eval_duration"] if response.get("eval_duration") else None,
                    created=datetime.now()
                )

                summary = f"{self._owner.username} used the Multimodal Assistant"

                session.add(assistance)

            except Exception as e:
                session.rollback()
                raise e

            else:
                session.commit()
                return response

    def generate(
            self,
            prompt: str = None,
            temperature: Optional[float] = 0.5,
            seed: Optional[int] = None,
            priming: Optional[str] = None,
            return_format: Literal['', 'json'] = '',
            options: Optional[dict] = None,
            session_uuid: str = None,
            keep_alive: Optional[Union[float, str]] = None
    ):
        """Describe the contents of an image using the Ollama API.

        Parameters
        ----------
        prompt : str
            The prompt to be used when requesting the description.
        temperature : Optional[float]
            The temperature to be used when making the request. Defaults to
            0.5.
        seed : Optional[int]
            The seed to be used when making the request. Defaults to None.
        priming : Optional[str]
            The priming to be used prior to the prompt.
        return_format : str
            The format to be used to return the request.
        options : Optional[dict]
            The options to be used when making the request.
        session_uuid : str
            The UUID of the session to be used when making the request.
        keep_alive : Optional[Union[float, str]]
            The keep alive value to be used when making the request.
        """
        template = [template for template in self._templates if template.model == self._generative_model][0]

        if not priming:
            priming = """Generative Assistant is ready to perform a task."""

        session_uuid = self._session_uuid if not session_uuid else session_uuid

        if not options:
            options = {
                "temperature": temperature,
                "num_ctx": self._generative_num_ctx
            }

        if not options.get("temperature"):
            options["temperature"] = temperature

        if not options.get("num_ctx"):
            options["num_ctx"] = self._generative_num_ctx

        keep_alive = self._generative_keep_alive if not keep_alive else keep_alive

        with self._session as session:

            try:

                response = self._client.generate(
                    model=self._generative_model, prompt=prompt, system=priming,
                    template=template.template, context=None, stream=False,
                    raw=False, format=return_format, images=None,
                    options=options, keep_alive=keep_alive
                )

                assistance = Assistance(
                    user_id=self._owner.id,
                    session_uuid=session_uuid,
                    assistant="Generative Assistant",
                    model=self._generative_model,
                    priming=priming,
                    prompt=prompt,
                    temperature=temperature,
                    seed=seed,
                    content=response["response"] if response.get("response") else None,
                    done=response["done"],
                    total_duration=response["total_duration"] if response.get("total_duration") else None,
                    load_duration=response["load_duration"] if response.get("load_duration") else None,
                    prompt_eval_count=response["prompt_eval_count"] if response.get("prompt_eval_count") else None,
                    prompt_eval_duration=response["prompt_eval_duration"] if response.get(
                        "prompt_eval_duration") else None,
                    eval_count=response["eval_count"] if response.get("eval_count") else None,
                    eval_duration=response["eval_duration"] if response.get("eval_duration") else None,
                    created=datetime.now()
                )

                session.add(assistance)

            except Exception as e:
                session.rollback()
                raise e

            else:
                session.commit()
                return response

    def list_models(self) -> Mapping[str, Any]:
        """List all available models."""
        return self._client.list()

    def show_model(self, model: str) -> Mapping[str, Any]:
        """Show the details of a specific model."""
        return self._client.show(model)

    def __str__(self):
        """Return the class string representation."""
        return f"Jackdaw Application [alpha] Assistant Controller"

    def __repr__(self):
        """Return the class representation."""
        return f"{self.__class__.__name__}()"

    @property
    def session_uuid(self):
        """Return the UUID of the session."""
        return self._session_uuid
