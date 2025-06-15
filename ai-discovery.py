import dotenv
import os
import argparse
import yaml
from rich.console import Console
from rich.color import Color

from discovery import AttackSurface, Node, NodeType
from helpers import DiscoveryAIClient, DiscoveryAiValidator, DiscoveryAiValidatorPartly


def main():
    dotenv.load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
    NETLAS_API_KEY = os.getenv("NETLAS_API_KEY")
    NETLAS_BASE_URL = os.getenv("NETLAS_BASE_URL", "https://app.netlas.io")

    # Set the maximum number of iterations of the discovery process
    MAX_NODES_TO_PROCESS = int(os.getenv("MAX_NODES_TO_PROCESS", 30))

    if not OPENAI_API_KEY:
        raise ValueError("The OPENAI_API_KEY environment variable is not set.")    
    if not NETLAS_API_KEY:
        raise ValueError("The NETLAS_API_KEY environment variable is not set.")

    
    parser = argparse.ArgumentParser(description="Netlas AI Attack Surface Finder")
    parser.add_argument("DOMAIN", help="Root domain, where to start the attack surface discovery process")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output, including detail error messages")
    parser.add_argument("-s", "--silent", action="store_true", help="Suppress all output, except results")
    parser.add_argument("-d", "--debug", action="store_true", help="Output only error messages")
    parser.add_argument("--no-results", action="store_true", help="Suppress printing of final results")
    args = parser.parse_args()
    root_domain = args.DOMAIN
    

    # Rich console used for colored output and progress indication
    console = Console()
    if args.silent:
        console.quiet = True
    colors = {
        "discovery": "#64b5f6",
        "ai": "dark_orange",
        "error": "bold red",
    }
    def output_progress(title: str, message: str = "", actor: str = ""):
        if args.debug and actor != "error":
            return
        color = colors.get(actor, Color.default().name)
        msg = f"[{color}]{title}[/{color}]"
        if args.verbose or args.debug:
            msg += f"\n"
            for line in message.splitlines():
                msg += f"  {line}\n"
            msg += f"\n"
        console.print(msg)
        

    # Load system and repeat prompts from files.
    # The system prompt is a general instruction for the AI model.
    # The repeat prompt is used when the AI model fails to provide a valid response.
    with open("prompt_system.md", "r") as file:
        system_prompt = file.read()
    with open("prompt_repeat.md", "r") as file:
        repeat_prompt = file.read()
    
    # Initialize the AI client. Target domain is passed with the system prompt to bound the scope.
    ai = DiscoveryAIClient(OPENAI_API_KEY, OPENAI_MODEL, f"{system_prompt} **{root_domain}**", repeat_prompt)

    # Initialize the attack surface with the root domain.
    surface = AttackSurface(api_key=NETLAS_API_KEY, apibase=NETLAS_BASE_URL)
    surface.append(Node(root_domain, NodeType.DOMAIN, [root_domain]))


    # Here is the main discovery loop.
    # The loop continues until all unprocessed by AI nodes will be processed
    # or the maximum number of nodes to process is reached.
    try:
        with console.status("") as status:
            
            processed_counter = 0
            while len(surface.unprocessedByAiNodes) > 0 and processed_counter < MAX_NODES_TO_PROCESS:
                node = selectNodeToProcess(surface.unprocessedByAiNodes)
                status.update(f"Queue: {len(surface.unprocessedByAiNodes)}, Processed: {processed_counter}, Processing '{node.label}'...")
                
                # Skip nodes that have no search directions available, nowhere to search
                if len(node.searchDirections) == 0:
                    node.isAiProcessed = True
                    output_progress(f"Discovery: No search directions for '{node.label}'", actor="discovery")
                    continue

                # Initialize validator and query the AI model to choose search directions
                output_progress(f"Discovery: Searches for '{node.label}'", yaml.dump(node.to_dict(), sort_keys=False), actor="discovery")
                validator = DiscoveryAiValidator([d.to_dict() for d in node.searchDirections], 20)
                answer = ai.searchDirectionsQuery(f"DIRECTION REQUEST:\n\n {yaml.dump(node.to_dict(), sort_keys=False)}", validator=validator.validate)
                formatted_answer = "\n".join(f"{key}: {value}" for key, value in answer.items())
                output_progress(f"{ai.respondedModel}: Decision for {node.label}", formatted_answer, actor="ai")

                # Make searches for directions selected by AI to add to the attack surface
                for direction in answer["add"]:
                    new_nodes = surface.search(int(direction), node)
                    # Length can be 0 because the surface searches and adds nodes. 
                    # Items that are already on the surface are filtered out.
                    # So as a result node can contain zero items after addition.
                    # Surface does not store such empty nodes, but they are returned by the search method.
                    if len(new_nodes) == 0:
                        output_progress(f"Discovery: Search {direction} filtered out (all items are already on the surface)", actor="discovery")
                        continue
                    for new_node in new_nodes:
                        output_progress(f"Discovery: Search {direction} - {new_node.label} added", f"{"\n".join(new_node)}", actor="discovery")
                
                # Make searches for directions selected by AI to review and add to the attack surface
                for direction in answer["partly"]:
                    new_nodes = surface.search(int(direction), node)
                    # Another empty node check
                    if len(new_nodes) == 0:
                        output_progress(f"Discovery: Search {direction} filtered out (all items are already on the surface)", actor="discovery")
                        continue
                    # Make revew query to AI
                    for i, new_node in enumerate(new_nodes):
                        ai_query = f"PARTLY REQUEST for `{direction}`, part {i}:\n\n"
                        ai_query += "\n".join([f"{item}" for item in new_node])
                        partly_answer = ai.partlyAddQuery(ai_query, validator=DiscoveryAiValidatorPartly(list(new_node)).validate)
                        new_node.intersection_update(partly_answer)
                        if len(new_node) == 0:
                            surface.remove(new_node)
                            output_progress(f"Discovery: Search {direction} - {new_node.label} filtered out by Ai", actor="discovery")
                            continue
                        output_progress(f"Discovery: Search {direction} - {new_node.label} partly added", f"{"\n".join(new_node)}", actor="discovery")

                node.isAiProcessed = True
                processed_counter += 1
    except Exception as e:
        output_progress("An error occurred", f"{str(e)}", actor="error")

    # Print the final results
    if not args.no_results:
        unique_items: dict[str, list[str]] = surface.unique_items_to_dict()
        for l in unique_items.values():
            l.sort()
        print(yaml.dump(unique_items, sort_keys=True))



# An optimization of processing order.
# The order is based on the type of node and the label of the domain node.
# Type of nodes and directions that are most likely yield strong connections, processed first.
def selectNodeToProcess(nodes: list[Node]) -> Node:
    if len(nodes) == 0:
        raise RuntimeError("No unprocessed node found")

    custom_order = {
        NodeType.HTTP_TRACKER: 0,
        NodeType.FAVICON: 1,
        NodeType.ORGANIZATION: 2,
        NodeType.PERSON: 3,
        NodeType.EMAIL: 4,
        NodeType.PHONE: 5,
        NodeType.ADDRESS: 6,
        NodeType.NETWORK_NAME: 7,
        NodeType.AS_NAME: 8,
        NodeType.DOMAIN: 9,
        NodeType.DNS_TXT: 10,
        NodeType.IP: 11,
        NodeType.TEXT: 12,
        NodeType.IP_RANGE: 13,
        NodeType.ASN: 14,
        NodeType.JARM: 15
    }
    sorted_nodes = sorted(nodes, key=lambda node: custom_order.get(node.type, 99))
    if sorted_nodes[0].type is NodeType.DOMAIN:
        domains = [node for node in sorted_nodes if node.type is NodeType.DOMAIN]
        for domain in domains:
            if domain.label == "Mailservers for domain":
                return domain
            if domain.label == "NS servers for domain":
                return domain
    return sorted_nodes[0]
    


if __name__ == "__main__":
    main()