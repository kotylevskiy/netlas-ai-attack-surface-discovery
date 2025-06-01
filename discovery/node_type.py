from enum import Enum


class NodeType(Enum):
        """
        NodeType is a simple enumeration that defines the different types of nodes
        that can be used in the discovery module.
        Enumeeration corresponds to the types accepted by the discovery API.
        Each node type is represented by a string value.
        """
        ADDRESS = "address"
        AS_NAME = "as_name"
        ASN = "asn"
        DNS_TXT = "dns_txt"
        DOMAIN = "domain"
        EMAIL = "email"
        FAVICON = "favicon"
        HTTP_TRACKER = "http_tracker"
        IP = "ip"
        IP_RANGE = "ip-range"
        JARM = "jarm"
        NETWORK_NAME = "network_name"
        ORGANIZATION = "organization"
        PERSON = "person"
        PHONE = "phone"
        TEXT = "text"        