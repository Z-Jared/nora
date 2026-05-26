import ipaddress
import socket
import urllib.parse


def is_public_http_url(url: str, resolve_host: bool = False) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    host = parsed.hostname
    if not host:
        return False

    normalized_host = host.rstrip(".").lower()
    if normalized_host == "localhost" or normalized_host.endswith(".localhost"):
        return False

    try:
        address = ipaddress.ip_address(normalized_host)
    except ValueError:
        if not resolve_host:
            return True
        return _hostname_resolves_to_public_addresses(normalized_host)

    return _is_public_address(address)


def _hostname_resolves_to_public_addresses(host: str) -> bool:
    try:
        resolved = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False

    addresses = []
    for item in resolved:
        address = item[4][0]
        try:
            addresses.append(ipaddress.ip_address(address))
        except ValueError:
            return False

    return bool(addresses) and all(_is_public_address(address) for address in addresses)


def _is_public_address(address) -> bool:
    return not (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )
