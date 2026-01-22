from functools import lru_cache
from typing import TYPE_CHECKING, Final

from llimona.addons import AddonMetadata

if TYPE_CHECKING:
    from llimona.providers import ProviderRegistry


class MockAddon(AddonMetadata):
    name: Final[str] = 'mock'  # type: ignore
    display_name: Final[str] = 'Mock Addon'  # type: ignore
    description: Final[str] = 'An addon to support Mock as a provider in Llimona.'  # type: ignore

    def register_providers(self, registry: ProviderRegistry) -> None:
        from llimona_mock_provider.providers import Provider, ProviderDesc

        registry.register_component(ProviderDesc, Provider)


@lru_cache(maxsize=1)
def addon() -> AddonMetadata:
    return MockAddon()
