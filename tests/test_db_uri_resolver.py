from common.db_uri_resolver import resolve_db_uri
from tests.test_template import TestTemplate


class TestDbUriResolver(TestTemplate):
    def test_private_domain_replaces_host(self):
        base_uri = "postgresql://user:pass@public.example.com:5432/app"
        private_domain = "private.internal"

        resolved_uri = resolve_db_uri(base_uri, private_domain)

        assert resolved_uri == "postgresql://user:pass@private.internal:5432/app"

    def test_private_domain_with_port_overrides(self):
        base_uri = "postgresql://user@public.example.com:5432/app"
        private_domain = "private.internal:6000"

        resolved_uri = resolve_db_uri(base_uri, private_domain)

        assert resolved_uri == "postgresql://user@private.internal:6000/app"

    def test_empty_private_domain_falls_back(self):
        base_uri = "postgresql://user@public.example.com:5432/app"

        resolved_uri = resolve_db_uri(base_uri, None)

        assert resolved_uri == base_uri
