from typing import Any
from .aiclient import AISearchDirectionsResponse, AIPartlyAddAnswer

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

    def validate(self, answer: AISearchDirectionsResponse) -> bool:
        """
        Validates the AI response.

        Args:
            answer (AISearchDirectionsResponse): The AI response to validate.

        Returns:
            bool: True if the response is valid, False otherwise.
        """
        try:
            received_directions: list[int] = []
            for key in ["add", "skip", "partly"]:
                if not all(isinstance(v, int) for v in getattr(answer, key, [])):
                    return False
                received_directions.extend(getattr(answer, key, []))
            direction_ids = [d["id"] for d in self._directions]
            if not all(v in direction_ids for v in received_directions):
                return False
            for id in getattr(answer, "partly", []):
                count = next(d["count"] for d in self._directions if d["id"] == id)
                if count > self._max_partly_count:
                    return False
            return True
        except Exception:
            return False
        

class DiscoveryAiValidatorPartly:
    """
    Validates AI responses for the discovery process when adding nodes partly.

    Attributes:
        _nodes (list[str]): List of nodes to validate against.
    """

    _nodes: list[str]

    def __init__(self, nodes: list[str]) -> None:
        """
        Initializes the DiscoveryAiValidatorPartly instance.
        Args:
            nodes (list[str]): A list of nodes to validate against.
        """
        self._nodes = nodes

    def validate(self, answer: AIPartlyAddAnswer) -> bool:
        """
        Validates the AI response for partly added nodes.
        Args:
            answer (AIPartlyAddAnswer): The AI response to validate.
        Returns:
            bool: True if the response is valid, False otherwise.
        """
        if not all(node in self._nodes for node in answer.nodes):
            return False
        return True