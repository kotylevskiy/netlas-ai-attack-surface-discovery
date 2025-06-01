from .node_type import NodeType
from .search_direction import SearchDirection
from typing import Callable

class Node(set[str]):
    """
    A group of items of the same type to place on the attack surface.
     
    The class is a representation of the discovery graph group node entity.
    Inherits from `set` to store unique items.

    Attributes:
        label (str): The label of the group.
        isAiProcessed (bool): Indicates if the group was processed by AI.
        type (NodeType): The type of the group.
        searchDirections (list[SearchDirection]): The search directions for the group.
        count_id (str): The ID of the count for the group.
    """

    label: str
    _type: NodeType
    isAiProcessed: bool = False
    _count_id: str
    _search_directions: list[SearchDirection]
    _items_hash: int
    _search_directions_updater: Callable[["Node"], None]
    _is_search_directions_updater_set: bool = False
    
    
    def __init__(self, label: str, type: NodeType, items: list[str]) -> None:
        """Initializes a Node instance.

        Args:
            label (str): The label of the group, usually matching search field name.
            type (NodeType): The type of the group, see `NodeType`.
            items (list[str]): An initial list of items to be added to the group.
        """
        super().__init__(items)
        self.label = label
        self._type = type


    def setSearchDirections(self, search_directions: list[SearchDirection], count_id: str) -> None:
        """
        Sets the search directions for the group.

        This method is typically called by the `AttackSurface` object after the group is added to the surface.
        It also manages the relevance of the search directions if the group is updated.

        Args:
            search_directions (list[SearchDirection]): The search directions to assign to the group.
            count_id (str): The identifier for the group's count.

        Returns:
            None
        """
        self._search_directions = search_directions
        self._count_id = count_id
        self._items_hash = hash(frozenset(self))

    @property
    def searchDirections(self) -> list[SearchDirection]:
        """
        Returns the search directions for this Node instance.
        """
        # Check if the search directions are relevant
        if not self.isSearchDirectionsRelevant():
            if self._is_search_directions_updater_set:
                # If the search directions are not relevant, call the updater to refresh them
                self._search_directions_updater(self)
            else:
                raise ValueError("Search directions are not set or are not relevant.")
        return self._search_directions
    
    @property
    def count_id(self) -> str:
        """
        Returns the count ID for this Node instance.
        """
        # Check if the search directions are relevant
        if not self.isSearchDirectionsRelevant():
            if self._is_search_directions_updater_set:
                # If the search directions are not relevant, call the updater to refresh them
                self._search_directions_updater(self)
            else:
                raise ValueError("Search directions are not set or are not relevant.")
        return self._count_id
    
    def isSearchDirectionsRelevant(self) -> bool:
        """
        Checks if the search directions are relevant for this Node instance.

        Search directions are considered relevant if they were set and the group has not changed since that moment.
        The check is done by comparing the hash of the items in the group with the stored hash.

        Returns:
            bool: True if the search directions are relevant, False otherwise.
        """
        if not self._search_directions or (self._items_hash != hash(frozenset(self))):
            return False
        return True
    
    def setSearchDirectionUpdater(self, callback: Callable[["Node"], None]) -> None:
        """
        Assigns a callback function to update the search directions for this Node instance.

        This method is typically invoked by the `AttackSurface` object after the Node has been added to the surface.

        Args:
            callback (Callable[[Node], None]): A function to be called when the search directions need to be updated.

        Returns:
            None
        """
        self._search_directions_updater = callback
        self._is_search_directions_updater_set = True


    @property
    def type(self) -> NodeType:
        return self._type

    def to_dict(self) -> dict[str, object]:
        """
        Converts the Node instance to a dictionary representation.

        Returns:
            dict[str, object]: A dictionary containing the label, type, and search directions of the Node instance.
        """
        return {
            "label": self.label,
            "type": self.type.value,
            "search_directions": [direction.to_dict() for direction in self._search_directions]
        }
    

    