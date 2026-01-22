from functools import lru_cache
from typing import TYPE_CHECKING, Final

from llimona.addons import AddonMetadata

if TYPE_CHECKING:
    from llimona.providers import ProviderRegistry


class SmartProviderAddon(AddonMetadata):
    name: Final[str] = 'smart_provider'  # type: ignore
    display_name: Final[str] = 'Smart Provider Addon'  # type: ignore
    description: Final[str] = 'An addon to support Smart Providers in Llimona.'  # type: ignore

    def register_providers(self, registry: ProviderRegistry) -> None:
        from llimona_smart_provider.providers import Provider, ProviderDesc

        registry.register_component(ProviderDesc, Provider)


@lru_cache(maxsize=1)
def addon() -> AddonMetadata:
    return SmartProviderAddon()
