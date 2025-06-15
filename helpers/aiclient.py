from time import sleep
from openai import OpenAI, RateLimitError, APITimeoutError, APIResponseValidationError
from openai.types.responses import ResponseInputItemParam
from typing import Callable, Type, Any
from pydantic import BaseModel


OPENAI_TIMEOUT = 30  # seconds
OPENAI_MESSAGES_HISTORY = 10


class AISearchDirectionsResponse(BaseModel):
    add: list[int] = []
    partly: list[int] = []
    skip: list[int] = []
    def __str__(self) -> str:
        return f"add: {self.add}\npartly: {self.partly}\nskip: {self.skip}"

class AIPartlyAddAnswer(BaseModel):
    nodes: list[str] = []
    def __str__(self) -> str:
        return "\n".join(self.nodes)

class DiscoveryAIClient:
    """
    A class to interact with OpenAI's API for generating AI responses.
    It handles the conversation history and manages the AI model's responses.
    """

    _client: OpenAI
    _requested_model: str
    respondedModel: str
    _messages: list[ResponseInputItemParam]
    _system_prompt: ResponseInputItemParam
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
        self._client = OpenAI(api_key=openai_api_key, timeout=OPENAI_TIMEOUT)
        self._requested_model = openai_model
        self._system_prompt = {"role": "developer", "content": system_prompt}
        self._messages = [ self._system_prompt ]
        self._repeat_msg = repeat_prompt
        self.respondedModel = "Ai-model-unknown"


    def __query__(self, input: str, model: Type[BaseModel], validator: Callable[[Any], bool], retries: int) -> BaseModel:
        self._messages.append({"role": "user", "content": input})
        self._messages = self._messages[-OPENAI_MESSAGES_HISTORY:]
        self._messages[0] = self._system_prompt
        for _ in range(retries):
            try:
                # Send the request to the AI model
                response = self._client.responses.parse(
                    model=self._requested_model,
                    input=self._messages,
                    text_format=model
                )
                self.respondedModel = response.model
                responseParsed = response.output_parsed

                # Base checks for the response and append it to the messages
                if not self.respondedModel.startswith(self._requested_model):
                    raise RuntimeError(f"Unexpected model: {response.model}. Expected: {self._requested_model}")
                if responseParsed is None:
                     if getattr(responseParsed, 'refusal', None):
                        self._messages.append({"role": "assistant", "content": responseParsed.refusal}) # type: ignore
                     raise ValueError(f"AI Search Directions Response is None")
                self._messages.append({"role": "assistant", "content": str(responseParsed)})
                
                # Validate the response
                if not validator(responseParsed):
                    raise ValueError("AI Search Directions Response validation failed")
                
                # If the response is valid, return it
                return responseParsed

            except (APIResponseValidationError, ValueError) as e:
                # If the response is not valid, retry with the repeat prompt
                self._messages.append({"role": "user", "content": self._repeat_msg})
                continue
            except RateLimitError:
                sleep(10)  # Wait before retrying on rate limit error
                continue
            except APITimeoutError:
                continue
        
        # If we reach here, it means we failed to get a valid response after retries
        # Prepare the history of messages for debugging and raise an exception
        history = f""
        for message in self._messages[-(retries*2 + 1):]:
            history += f"> {str(message.get('role')).capitalize()}:\n{message.get('content', '')}\n\n"
        raise Exception(f"Failed to get a valid response after {retries} attempts.\n\n{history}")
    



    def searchDirectionsQuery(self, input: str, validator: Callable[[AISearchDirectionsResponse], bool], retries: int = 3) -> dict[str, list[int]]:
        """
        Queries the AI for search directions based on the input string.
        Args:
            input (str): The input string to query the AI.
            validator (Callable[[AISearchDirectionsResponse], bool]): A function to validate the AI response.
            retries (int): The number of retries in case of failure.
        Returns:
            dict[str, list[int]]: A dictionary containing the search directions with keys "add", "partly", and "skip".
        Raises:
            ValueError: If the response is not of the expected type or does not match the validation criteria.
            Exception: If the AI fails to provide a valid response after the specified number of retries, an Exception is raised with the message history for debugging.
        """
        directions = self.__query__(input, AISearchDirectionsResponse, validator, retries)
        if isinstance(directions, AISearchDirectionsResponse):
            return {
                "add": directions.add,
                "partly": directions.partly,
                "skip": directions.skip
            }
        else:
            raise ValueError(f"Unexpected response type: {type(directions)}. Expected AISearchDirectionsResponse.")
    

    def partlyAddQuery(self, input: str, validator: Callable[[AIPartlyAddAnswer], bool], retries: int = 3) -> list[str]:
        """
        Queries the AI for a list of nodes to be added partly based on the input string.
        Args:
            input (str): The input string to query the AI.
            validator (Callable[[AIPartlyAddAnswer], bool]): A function to validate the AI response.
            retries (int): The number of retries in case of failure.
        Returns:
            list[str]: A list of nodes to be added partly.
        Raises:
            ValueError: If the response is not of the expected type or does not match the validation criteria.
            Exception: If the AI fails to provide a valid response after the specified number of retries, an Exception is raised with the message history for debugging.
        """
        answer = self.__query__(input, AIPartlyAddAnswer, validator, retries)
        if isinstance(answer, AIPartlyAddAnswer):
            return answer.nodes
        else:
            raise ValueError(f"Unexpected response type: {type(answer)}. Expected AIPartlyAddAnswer.")