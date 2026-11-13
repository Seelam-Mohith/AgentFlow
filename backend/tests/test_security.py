import socket
import httpx
import pytest
from backend.security import validate_url, is_public, resolve_public, SafeFetcher


@pytest.mark.parametrize('url', ['http://localhost', 'http://127.0.0.1', 'http://10.0.0.1', 'http://169.254.169.254', 'http://[::1]', 'http://[::ffff:127.0.0.1]', 'http://192.168.1.1', 'http://100.64.0.1', 'file:///etc/passwd', 'ftp://example.com', 'https://user:pass@example.com', 'https://example.com:8080', 'http://metadata.google.internal', 'javascript:alert(1)', 'http://[64:ff9b::7f00:1]'])
def test_unsafe_urls(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_normalize_and_public():
    assert validate_url('https://EXAMPLE.com/path#fragment') == 'https://example.com/path'
    assert is_public('93.184.216.34')
    assert not is_public('224.0.0.1')


async def test_mixed_dns_rejected(monkeypatch):
    import asyncio
    async def dns(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443)), (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]
    monkeypatch.setattr(asyncio.get_running_loop(), 'getaddrinfo', dns)
    with pytest.raises(ValueError, match='DNS'):
        await resolve_public('example.com', 443)


async def test_pinned_ip_and_redirect_revalidation(monkeypatch):
    import backend.security as security
    calls = []
    async def resolve(host, port):
        assert host == 'example.com'
        return ['93.184.216.34']
    real_client = httpx.AsyncClient
    def handle(request):
        calls.append(request)
        return httpx.Response(302, headers={'location': 'http://127.0.0.1/private'})
    def client(**kwargs):
        assert kwargs['trust_env'] is False
        assert kwargs['follow_redirects'] is False
        return real_client(transport=httpx.MockTransport(handle), **kwargs)
    monkeypatch.setattr(security, 'resolve_public', resolve)
    monkeypatch.setattr(security.httpx, 'AsyncClient', client)
    with pytest.raises(ValueError):
        await SafeFetcher().get('https://example.com')
    assert len(calls) == 1
    assert calls[0].url.host == '93.184.216.34'
    assert calls[0].headers['host'] == 'example.com'
    assert calls[0].extensions['sni_hostname'] == 'example.com'


async def test_response_size_limit(monkeypatch):
    import backend.security as security
    async def resolve(*args): return ['93.184.216.34']
    real_client = httpx.AsyncClient
    monkeypatch.setattr(security, 'resolve_public', resolve)
    monkeypatch.setattr(security.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(lambda req: httpx.Response(200, text='x'*100)), **kw))
    with pytest.raises(ValueError, match='size'):
        await SafeFetcher().get('https://example.com', limit=10)
