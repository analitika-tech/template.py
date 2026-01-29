class AssertionErrorMessage:
    INVALID_TOKEN_LIFETIME = "Access Token Lifetime is null or incorrect"
    INVALID_TOKEN_SECRET = "Token Secret is null or incorrect"
    INVALID_TOKEN_LIFESPAN = "Token iat can't be greater than exp"
    INVALID_EXTERNAL_ACCESS_TOKEN = (
        "Access Token provided by client is not valid"
    )
    INVALID_DISCOVERY_DOCUMENT = "Discovery document is empty or corrupted"
    INVALID_TOKEN_HADER = "Invalid Token Header"
    INVALID_ALGORITHM = "Algorithm is empty or it is not a valid algorithm"
    INVALID_TOKEN = "Token provided by the client is expired or malformed"
    INVALID_USER = "User does not exist or is not valid"
    INVALID_REQUEST = "Request not valid or malformed"
    INVALID_ACCESS_RIGHTS = "Nemata prava da podešavate budžet"

    BUDGET_ARCHIVED = "Budget has been archived, no actions outside deletion can be performed"

    @staticmethod
    def invalid_property(property: str) -> str:
        """Provide property name in the method argument and get invalid property message string"""
        return f"{property} is not valid"

    @staticmethod
    def entity_not_found(entity: str) -> str:
        return f"{entity} couldn't be found"


class ErrorCode:
    INVALID_TOKEN = "InvalidToken"
    INVALID_DISCOVERY_DOCUMENT_ENDPOINT = "InvalidDiscoveryDocument"
    INVALID_REQUEST = "InvalidRequest"
    INVALID_USER = "InvalidUser"

    INTERNAL_SERVER_ERROR = "InternalServerError"


class ErrorMessage:
    INVALID_TOKEN = "Token provided by the client is expired or malformed"
    INVALID_DISCOVERY_DOCUMENT_ENDPOINT = "You provided a malformed or not existing url to Idenitity Provider .well-known/openid-configuration"
    INVALID_REQUEST = "There might be a problem with the request object (authorization params, request body etc.)"
    INVALID_USER = "User does not exist or is not valid"
    INVALID_REFRESH_TOKEN_REQUEST = "Token has not expired"

    INTERNAL_SERVER_ERROR = "Something went wrong"
