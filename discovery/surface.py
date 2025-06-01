from typing import Any, Iterable, SupportsIndex

from .node import Node
from .node_type import NodeType
from .client import ApiClient
from .search_direction import SearchDirection



class AttackSurface(list[Node]):
    """
    Represents the attack surface as a collection of nodes.

    This class is a subclass of the built-in list class and provides additional functionality
    for managing nodes in the attack surface. It is designed to work with the `Node` class,
    which represents a group of items of the same type. The class also provides methods for
    searching nodes, filtering unique items, and updating search directions.

    Attributes:
        unprocessedByAiNodes (list[Node]): List of nodes that have not been processed by AI,
            formed using the `Node.isAiProcessed` property.
    """

    _provider: ApiClient
    _last_search_results: list[Node]
    

    def __init__(self, api_key: str, apibase: str) -> None:
        """
        Initializes an AttackSurface instance.

        Args:
            api_key (str): The API key for authentication.
            apibase (str): The base URL for the API.
        """
        super().__init__()
        self._provider = ApiClient(api_key, apibase)
        self._last_search_results = []
    

    # Override base List methods to ensure that the AttackSurface class behaves like a list

    def _filter_and_register_node(self, node: Node) -> None:
        """
        Filters out duplicate items from the node and registers search direction updaters.

        Args:
            node (Node): The node to filter and register.
        """
        _unique_items = self._unique_items()
        if node.type in _unique_items.keys():
            node.difference_update(_unique_items[node.type])
        if len(node) > 0:
            self._update_search_directions(node)
            node.setSearchDirectionUpdater(self._update_search_directions)
        
    def append(self, node: Node) -> None:
        """
        Appends a node to the attack surface.

        Args:
            node (Node): The node to be appended.
        """
        self._filter_and_register_node(node)
        if len(node) > 0:
            super().append(node)
        
    def extend(self, iterable: Iterable[Node]) -> None:
        """
        Extends the attack surface with a list of nodes.

        Args:
            iterable (Iterable[Node]): An iterable of nodes to be added.
        """
        for node in iterable:
            self.append(node)

    def insert(self, index: SupportsIndex, item: Node) -> None:
        """
        Inserts a node at a specified index in the attack surface.

        Args:
            index (SupportsIndex): The index at which to insert the node.
            item (Node): The node to be inserted.
        """
        self._filter_and_register_node(item)
        if len(item) > 0:
            super().insert(index, item)

    def __setitem__(self, key: SupportsIndex | slice, value: Any) -> None:
        """
        Sets the value of a node at a specified index in the attack surface.

        Args:
            key (SupportsIndex | slice): The index or slice at which to set the value.
            value (Any): The value to be set.

        Raises:
            TypeError: If the value is not a Node instance.
            NotImplementedError: If slice assignment is attempted.
        """
        if isinstance(key, slice):
            raise NotImplementedError("Slice assignment is not supported.")
        else:
            if not isinstance(value, Node):
                raise TypeError("Value must be a Node instance.")
            self._filter_and_register_node(value)
            super().__setitem__(key, value)
        
    def __iadd__(self, iterable: Iterable[Node]):
        """
        Extends the attack surface with a list of nodes using the `+=` operator.

        Args:
            iterable (Iterable[Node]): An iterable of nodes to be added.

        Returns:
            AttackSurface: The updated attack surface.
        """
        self.extend(iterable)
        return self
    

    # Additional AttackSurface specific methods

    def _unique_items(self) -> dict[NodeType, set[str]]:
        """
        Returns a dictionary of unique items in the attack surface to filter elements during addition.

        Returns:
            dict[NodeType, set[str]]: A dictionary mapping node types to sets of unique items.
        """
        _unique_items: dict[NodeType, set[str]] = {}
        for node in self:
            if node.type not in _unique_items.keys():
                _unique_items[node.type] = set()
            _unique_items[node.type].update(node)
        return _unique_items
    

    def _update_search_directions(self, node: Node) -> None:
        """
        Callback function to update search directions for a node.

        Args:
            node (Node): The node for which to update search directions.
        """
        directions, count_id = self._provider.getSearchDirections(node)
        node.setSearchDirections(directions, count_id)
    

    @property
    def unprocessedByAiNodes(self) -> list[Node]:
        """
        Returns a list of nodes that have not been processed by AI.

        Returns:
            list[Node]: List of unprocessed nodes.
        """
        return [node for node in self if not node.isAiProcessed]


    def search(self, direction: SearchDirection | int, node: Node) -> list[Node]:
        """
        Requests Discovery API to search for nodes associated with the given `node`.
        Returned nodes are filtered and registered in the attack surface.

        Args:
            direction (SearchDirection | int): The search direction to be used for the search.
            node (Node): The group of elements to search by.

        Returns:
            list[Node]: A list of nodes found during the search.
        """
        if isinstance(direction, int):
            direction = next(d for d in node.searchDirections if d.id == direction)
        last_search_results: list[Node] = []
        new_nodes = self._provider.search(direction, node)
        for node in new_nodes:
            self._filter_and_register_node(node)
            if len(node) > 0:
                last_search_results.append(node)
                super().append(node)
        return last_search_results
    
    
    def unique_items_to_dict(self) -> dict[str, list[str]]:
        """
        Returns a dictionary of unique items in the attack surface, where the keys are the node types
        and the values are lists of unique items.

        Returns:
            dict[str, list[str]]: A dictionary of unique items in the attack surface.
        """
        ret: dict[str, list[str]] = {}
        _unique_items = self._unique_items()
        for type, items in _unique_items.items():
            ret[type.value] = list(items)
        return ret
