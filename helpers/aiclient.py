from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam
from typing import Callable

OPENAI_TIMEOUT = 30  # seconds
OPENAI_TEMPERATURE = 0.2
OPENAI_MESSAGES_HISTORY = 10


class AIClient:
    """
    A class to interact with OpenAI's API for generating AI responses.
    It handles the conversation history and manages the AI model's responses.
    """

    _client: OpenAI
    _requested_model: str
    respondedModel: str
    _messages: list[ChatCompletionMessageParam]
    _system_prompt: ChatCompletionSystemMessageParam
    _repeat_msg: str

    def __init__(self, openai_api_key: str, openai_model: str, system_prompt: str, repeat_prompt: str) -> None:
        """
        Initializes the AIClient instance.

        Args:
            openai_api_key (str): The API key for OpenAI.
            openai_model (str): The model to be used for generating responses.
            system_prompt (str): The system prompt to be used for the AI model - a general instruction.
            repeat_prompt (str): The prompt to be used when the AI model fails to provide a valid response.
        """
        self._client = OpenAI(api_key=openai_api_key)
        self._requested_model = openai_model
        self._system_prompt = {"role": "system", "content": system_prompt}
        self._messages = [ self._system_prompt ]
        self._repeat_msg = repeat_prompt
        self.respondedModel = "Ai-model-unknown"


    def __query__(self, input: str) -> str:
        """
        Sends a message to the AI model and returns the response.

        Args:
            input (str): The input string to be sent to the AI model.

        Returns:
            str: The AI model's response.

        Raises:
            RuntimeError: If the model returned does not match the requested model.
        """
        self._messages.append({"role": "user", "content": input})
        self._messages = self._messages[-OPENAI_MESSAGES_HISTORY:]
        self._messages[0] = self._system_prompt
        response = self._client.chat.completions.create(
            model=self._requested_model,
            messages=self._messages,
            temperature=OPENAI_TEMPERATURE,
            timeout=OPENAI_TIMEOUT, 
        )
        self.respondedModel = response.model
        if not self.respondedModel.startswith(self._requested_model):
            raise RuntimeError(f"Unexpected model: {response.model}. Expected: {self._requested_model}")
        content = response.choices[0].message.content
        message = content.strip() if content is not None else ""
        self._messages.append({"role": "assistant", "content": message})
        return message
    
    def query(self, input: str, retries: int = 3, validator: Callable[[str], bool] = None) -> str: # type: ignore
        """
        Queries the AI model with the given input and retries if necessary.

        Args:
            input (str): The input string to be sent to the AI model.
            retries (int, optional): The number of retries if the response validation fails. Defaults to 3.
            validator (Callable[[str], bool], optional): A function to validate the response. If None, no validation is performed.

        Returns:
            str: The AI model's response.

        Raises:
            Exception: If a valid response is not received after the specified number of retries.
        """
        for _ in range(retries):
            try:
                message = self.__query__(input)
                if validator is None:
                    return message
                else:
                    if validator(message):
                        return message
                    else:
                        input = self._repeat_msg
            except Exception:
                continue
        history = f""
        for message in self._messages[-7:]:
            history += f"> {str(message['role']).capitalize()}:\n{message.get('content', '')}\n\n"
        raise Exception(f"Failed to get a valid response after {retries} attempts.\n\n{history}")
