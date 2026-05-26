import socket
import unittest
from unittest.mock import patch

from mini_agent.url_safety import is_public_http_url


class UrlSafetyTests(unittest.TestCase):
    def test_allows_plain_public_http_urls_without_dns_resolution(self):
        self.assertTrue(is_public_http_url("https://example.com/docs"))
        self.assertTrue(is_public_http_url("http://93.184.216.34/index.html"))

    def test_rejects_non_http_local_and_private_urls(self):
        rejected = [
            "file:///etc/passwd",
            "http://localhost:8000",
            "http://service.localhost",
            "http://127.0.0.1:8000",
            "http://10.0.0.1",
            "http://172.16.0.1",
            "http://192.168.1.1",
            "http://169.254.169.254/latest/meta-data",
            "http://[::1]:8000",
        ]

        for url in rejected:
            self.assertFalse(is_public_http_url(url), url)

    def test_dns_resolution_rejects_hostnames_that_resolve_to_private_addresses(self):
        def fake_getaddrinfo(host, port, type=0):
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("127.0.0.1", 0),
                )
            ]

        with patch("socket.getaddrinfo", fake_getaddrinfo):
            self.assertFalse(is_public_http_url("https://internal.example.com", resolve_host=True))

    def test_dns_resolution_allows_hostnames_that_resolve_to_public_addresses(self):
        def fake_getaddrinfo(host, port, type=0):
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("93.184.216.34", 0),
                )
            ]

        with patch("socket.getaddrinfo", fake_getaddrinfo):
            self.assertTrue(is_public_http_url("https://example.com", resolve_host=True))


if __name__ == "__main__":
    unittest.main()
