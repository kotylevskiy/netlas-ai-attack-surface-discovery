import json
import requests
import urllib3

from .search_direction import SearchDirection
from .node_type import NodeType
from .node import Node
import time



class ApiClient:
    """
    A client for interacting with the Netlas Discovery API.
    This class handles API request execution with retry logic, and provides methods
    for searching and retrieving discovery directions and results.
    """

    # Maximum number of retry attempts for API calls.
    MAX_RETIRES: int = 100
    # Default wait time (in seconds) between retries.
    DEFAULT_RETRY_WAIT_TIME: int = 10

    api_key: str
    apibase: str
    _headers: dict[str, str]
    _verify_ssl: bool


    def __init__(self, api_key: str, apibase: str = "https://app.netlas.io") -> None:
        """
        Initializes the ApiClient with the provided API key and base URL.

        Args:
            api_key (str): The API key for authentication.
            apibase (str, optional): The base URL for the API. Defaults to "https://app.netlas.io".

        Returns:
            None
        """
        self.api_key: str = api_key
        self.apibase: str = apibase.rstrip("/")
        self._verify_ssl: bool = True
        if self.apibase != "https://app.netlas.io":
            self._verify_ssl = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self._headers = {
            "Content-Type": "application/json", 
            # "Accept": "application/x-ndjson",
            "X-Api-Key": self.api_key
            }

    def _execute_api_call(self, url: str, headers: dict[str,str], payload: dict[str, object]):
        """
        Executes an API call with retry logic.

        Handles HTTP errors, including rate limiting (HTTP 429) and server errors (HTTP 504).
        Retries the request based on the response headers and status codes.

        Args:
            url (str): The API endpoint URL.
            headers (dict[str, str]): The HTTP headers for the request.
            payload (dict[str, object]): The JSON payload for the request.

        Returns:
            requests.Response: The HTTP response object.

        Raises:
            Exception: If all retry attempts fail or an unrecoverable error occurs.
        """
        for _ in range(1, self.MAX_RETIRES + 1):
            try:
                response = requests.post(url, headers=headers, json=payload, verify=self._verify_ssl)
                response.raise_for_status()
                return response
            
            except requests.exceptions.HTTPError as http_err:
                r = getattr(http_err, 'response', None)
                
                # Handle rate limiting (HTTP 429)
                if r is not None and r.status_code == 429 and "Retry-After" in r.headers:
                    wait_time = int(r.headers.get("Retry-After", "60"))
                    if wait_time > self.DEFAULT_RETRY_WAIT_TIME:
                        wait_time -= self.DEFAULT_RETRY_WAIT_TIME
                    time.sleep(wait_time)

                # Handle HTTP 504 timeout - just retry
                elif r is not None and r.status_code == 504:
                    pass

                # Handle other HTTP errors - raise an exception with details
                elif r is not None:
                    if r.headers.get("Content-Type") == "application/json":
                        error_json: dict[str,str] = r.json() if r is not None else {}
                        raise Exception(f"HTTP error {r.status_code}: Response JSON: {error_json.get("detail", "Details not found")}") from http_err
                    else:
                        error_text = r.text if r is not None else ""
                        raise Exception(f"HTTP error {r.status_code}: Response text: \n{error_text}\nURL: {url}\nPayload:\n{json.dumps(payload, indent=4)}") from http_err
                else:
                    raise Exception(f"HTTP error {http_err} (no additional data available)") from http_err
                
            # Handle other types of exceptions that needs to be retried
            except (
                requests.exceptions.Timeout, 
                requests.exceptions.ConnectionError, 
                requests.exceptions.ChunkedEncodingError
                ):
                pass

            # Unexpected exceptions that should not be retried - raise an exception with details
            except Exception as err:
                raise Exception(f"Unhandled error occurred: {str(err)}") from err
            
            # Sleep for the default retry wait time before retrying
            time.sleep(self.DEFAULT_RETRY_WAIT_TIME)

        # If we reach here, it means all retries failed
        raise Exception(f"Failed to execute API call after {self.MAX_RETIRES} attempts")
        


    def getSearchDirections(self, node: Node) -> tuple[list[SearchDirection], str]:
        """
        Gets search directions for a given node and the value of the `X-Count-Id` header.

        Search directions are available search fields and count of results for each search for the given node.
        The `X-Count-Id` header is used on the backend to identify the search results list for the given node.

        Usage:
            directions, count_id = client.getSearchDirections(node)

        Args:
            node (Node): The `Node` object (group of items of the same type), for which search directions are requested.

        Returns:
            tuple (tuple[list[SearchDirection], str]): A tuple containing a list of SearchDirection objects and the value of the `X-Count-Id` header.
        """
        # Return empty list of search directions and empty value of X-Cound-Id if the node is empty
        if len(node) == 0:
            return [], ""
        
        # Prepare the API call
        url = f"{self.apibase}/api/discovery/group_of_nodes_count/"
        payload: dict[str, object] = {
            "node_type": node.type.value,
            "node_value": list(node)
        }
        response = self._execute_api_call(url, self._headers, payload)

        # Parse the response
        # The response is a stream of JSON objects, one per line (ndjson format).
        # Each JSON object contains the search field ID, count of results, and preview - search direction.
        ret: list[SearchDirection] = []
        for line in response.iter_lines():
            if line:
                ldict = json.loads(line)
                key = int(ldict.get("search_field_id"))
                count = int(ldict.get("count", 0))
                sd = SearchDirection(
                    id=key,
                    search_field=ldict.get("search_field"),
                    count=count,
                    preview=ldict.get("preview")
                )
                # Add the search direction to the list if a search will bring at least one result 
                if count > 0:
                    ret.append(sd)
        return ret, response.headers.get("X-Count-ID", "")
    


    def search(self, direction: SearchDirection, node: Node) -> list[Node]:
        """
        Searches based on the provided `SearchDirection` for the given `Node`.

        Args:
            direction (SearchDirection): The `SearchDirection` object that specifies the search field and ID.
            node (Node): The `Node` object (group of items of the same type) to search for.

        Returns:
            list[Node]: A list of found items, grouped into `Node` objects by type.
        """
        # If node doen't contain any items, return empty list - nothing to search by
        if len(node) == 0:
            return []
        
        # Prepare the API call
        url = f"{self.apibase}/api/discovery/group_of_nodes_result/"
        payload: dict[str, object] = {
            "node_type": node.type.value,
            "node_value": list(node),
            "search_field_id": direction.id,
        }
        headers = self._headers.copy()
        # Add the X-Count-ID header to the request
        # The value of the X-Count-ID header is used on the backend to identify the search directions list for the given node.
        headers["X-Count-ID"] = node.count_id 
        response = self._execute_api_call(url, headers=headers, payload=payload)

        # Parse the response
        # The response is a stream of JSON objects, one per line (ndjson format).
        # Each JSON object represents a group of items of the same type - a search result for one of node items.
        # Search can return results of different types.
        # A new node will be created for each type of the search result.
        search_results: dict[str, list[str]] = {}
        for line in response.iter_lines():
            if line:
                ldict = json.loads(line)
                if ldict.get("is_valid", False) and len(ldict.get("node_value", [])) > 0:
                    key = ldict.get("node_type")
                    if key in search_results.keys():
                        search_results[key].extend(ldict.get("node_value"))
                    else:
                        search_results[key] = ldict.get("node_value")
        ret: list[Node] = []
        for type, values in search_results.items():
            ret.append(Node(direction.search_field, NodeType(type), values))
        return ret