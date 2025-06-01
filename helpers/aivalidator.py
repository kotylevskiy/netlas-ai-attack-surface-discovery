from typing import Any
import yaml

class DiscoveryAiValidator:
    """
    Validates AI responses for the discovery process.

    Attributes:
        _directions (list[dict[str, Any]]): List of search directions to validate against.
        _max_partly_count (int): Maximum size of item list to be requested as "partly" for additional AI review.
    """

    _directions: list[dict[str, Any]]  # see SearchDirection class
    _max_partly_count: int

    def __init__(self, directions: list[dict[str, Any]], max_partly_count: int) -> None:
        """
        Initializes the DiscoveryAiValidator instance.

        Args:
            directions (list[dict[str, Any]]): A list of search directions to validate against.
            max_partly_count (int): The maximum size of item list to be requested as "partly" for additional AI review.
        """
        self._directions = directions
        self._max_partly_count = max_partly_count

    def validate(self, answer: str) -> bool:
        """
        Validates the AI response.

        Args:
            answer (str): The AI response to validate.

        Returns:
            bool: True if the response is valid, False otherwise.
        """
        try:
            response_dict = yaml.safe_load(answer)
            required_keys = ["add", "skip", "partly"]
            received_directions: list[int] = []
            for key in required_keys:
                if key not in response_dict or not isinstance(response_dict[key], list) or not all(isinstance(v, int) for v in response_dict[key]):
                    return False
                received_directions.extend(response_dict[key])
            direction_ids = [d["id"] for d in self._directions]
            if not all(v in direction_ids for v in received_directions):
                return False
            for id in response_dict["partly"]:
                count = next(d["count"] for d in self._directions if d["id"] == id)
                if count > self._max_partly_count:
                    return False
            return True
        except Exception:
            return False