from typing import Any

class SearchDirection:
    """
    Represents a search direction in the Discovery API.

    This class corresponds to the data structure returned by the Discovery API when search directions are requested.
    Each search direction is represented by an ID, a search field, a count of results, and a preview of the results.
    """

    id: int
    search_field: str
    count: int
    preview: list[str]

    def __init__(self, id: int, search_field: str, count: int, preview: list[str]) -> None:
        """
        Initializes a SearchDirection instance.

        Args:
            id (int): The ID of the search direction.
            search_field (str): The search field indicating the search direction.
            count (int): The number of results that will be returned after the search by this direction.
            preview (list[str]): A preview of the search results (up to 5 items).
        """
        self.id = id
        self.search_field = search_field
        self.count = count
        self.preview = preview

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the SearchDirection instance to a dictionary as returned from the Discovery API.

        Returns:
            dict[str, Any]: A dictionary representation of the SearchDirection instance.
        """
        return {
            "id": self.id,
            "search_field": self.search_field,
            "count": self.count,
            "preview": self.preview,
        }