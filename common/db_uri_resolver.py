from urllib.parse import urlparse, urlunparse


def resolve_db_uri(base_uri: str, private_domain: str | None) -> str:
    """
    Build a database URI that prefers the Railway private domain when available.

    Args:
        base_uri: The original database connection URI.
        private_domain: The Railway private domain host (with optional port).

    Returns:
        A database URI that uses the private domain if it is valid; otherwise
        returns the original base URI.
    """
    if not base_uri:
        return base_uri

    if not private_domain or not private_domain.strip():
        return base_uri

    try:
        parsed_db_uri = urlparse(base_uri)
        if not parsed_db_uri.scheme or not parsed_db_uri.netloc:
            return base_uri

        base_host = parsed_db_uri.hostname or ""

        # If the URI already points to a Railway internal host, keep it as-is.
        if base_host.endswith("railway.internal"):
            return base_uri

        parsed_private = urlparse(f"//{private_domain}")
        private_host = parsed_private.hostname
        private_port = parsed_private.port or parsed_db_uri.port

        if not private_host:
            return base_uri

        user_info = ""
        if parsed_db_uri.username:
            user_info = parsed_db_uri.username
            if parsed_db_uri.password:
                user_info += f":{parsed_db_uri.password}"
            user_info += "@"

        netloc = f"{user_info}{private_host}"
        if private_port:
            netloc += f":{private_port}"

        rebuilt_uri = parsed_db_uri._replace(netloc=netloc)
        return urlunparse(rebuilt_uri)
    except Exception:
        # If anything goes wrong, fall back to the original URI.
        return base_uri
