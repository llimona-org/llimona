from functools import lru_cache
from typing import TYPE_CHECKING, Final

from llimona.addons import AddonMetadata

if TYPE_CHECKING:
    from llimona.sensors import SensorRegistry


class OpentelemetryAddon(AddonMetadata):
    name: Final[str] = 'opentelemetry'  # type: ignore
    display_name: Final[str] = 'OpenTelemetry Addon'  # type: ignore
    description: Final[str] = 'An addon to support OpenTelemetry sensors in Llimona.'  # type: ignore

    def register_sensors(self, registry: SensorRegistry) -> None:
        from llimona_opentelemetry.sensors import OpentelemetrySensor, OpentelemetrySensorDesc

        registry.register_component(OpentelemetrySensorDesc, OpentelemetrySensor)


@lru_cache(maxsize=1)
def addon() -> AddonMetadata:
    return OpentelemetryAddon()
