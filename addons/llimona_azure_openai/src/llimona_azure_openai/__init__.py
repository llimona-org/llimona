from functools import lru_cache
from typing import TYPE_CHECKING, Final

from llimona.addons import AddonMetadata

if TYPE_CHECKING:
    from llimona.providers import ProviderRegistry


class AzureOpenAIAddon(AddonMetadata):
    name: Final[str] = 'azure_openai'  # type: ignore
    display_name: Final[str] = 'Azure OpenAI Addon'  # type: ignore
    description: Final[str] = 'An addon to support Azure OpenAI as a provider in Llimona.'  # type: ignore

    def register_providers(self, registry: ProviderRegistry) -> None:
        from llimona_azure_openai.providers import Provider, ProviderDesc

        registry.register_component(ProviderDesc, Provider)


@lru_cache(maxsize=1)
def addon() -> AddonMetadata:
    return AzureOpenAIAddon()
