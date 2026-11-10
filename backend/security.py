"""Resolve before each request; connect to the validated IP while retaining TLS SNI."""
import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit
import httpx


def validate_url(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
        if parts.scheme not in ('http', 'https') or not parts.hostname:
            raise ValueError('Use a complete HTTP or HTTPS URL.')
        if parts.username is not None or parts.password is not None:
            raise ValueError('URLs containing credentials are not allowed.')
        host = parts.hostname.encode('idna').decode('ascii').lower().rstrip('.')
        if host in ('localhost', 'metadata.google.internal') or host.endswith(('.localhost', '.local', '.internal')):
            raise ValueError('Local and metadata destinations are blocked.')
        if parts.port not in (None, 80, 443):
            raise ValueError('Only standard web ports 80 and 443 are allowed.')
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            ip = None
        if ip is not None and not is_public(str(ip)):
            raise ValueError('Private, reserved, and local addresses are blocked.')
        netloc = f'[{host}]' if ':' in host else host
        if parts.port:
            netloc += f':{parts.port}'
        return urlunsplit((parts.scheme, netloc, parts.path or '/', parts.query, ''))
    except (UnicodeError, ValueError) as exc:
        raise ValueError(str(exc)) from None


def is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            return is_public(str(ip.ipv4_mapped))
        # Block transition mechanisms which can encode an unsafe IPv4 destination.
        if ip.sixtofour or ip.teredo or ip in ipaddress.ip_network('64:ff9b::/96'):
            return False
    return ip.is_global and not ip.is_multicast


async def resolve_public(host: str, port: int) -> list[str]:
    records = await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM), 8)
    addresses = sorted({record[4][0] for record in records})
    if not addresses or not all(is_public(address) for address in addresses):
        raise ValueError('DNS resolved to a private or unsafe destination.')
    return addresses


class SafeFetcher:
    async def get(self, url: str, limit: int = 1_500_000, before_redirect=None) -> tuple[str, int, str, str]:
        from urllib.parse import urljoin
        for _ in range(6):
            url = validate_url(url)
            parsed = urlsplit(url)
            host = parsed.hostname
            addresses = await resolve_public(host, parsed.port or (443 if parsed.scheme == 'https' else 80))
            ip = addresses[0]
            authority = f'[{ip}]' if ':' in ip else ip
            if parsed.port:
                authority += f':{parsed.port}'
            pinned = urlunsplit((parsed.scheme, authority, parsed.path, parsed.query, ''))
            # No automatic redirect, proxy, second hostname lookup, or pooled connection reuse.
            async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=12) as client:
                async with client.stream('GET', pinned, headers={'Host': parsed.netloc, 'User-Agent': 'AgentFlowBot/1.0', 'Accept': 'text/html,text/plain'}, extensions={'sni_hostname': host}) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        destination = response.headers.get('location')
                        if not destination:
                            raise ValueError('Redirect has no destination.')
                        url = validate_url(urljoin(url, destination))
                        if before_redirect:
                            await before_redirect(url)
                        continue
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > limit:
                            raise ValueError('Response exceeds safe size limit.')
                    return url, response.status_code, data.decode(response.encoding or 'utf-8', errors='replace'), response.headers.get('content-type', '')
        raise ValueError('Too many redirects.')

