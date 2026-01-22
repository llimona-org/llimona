from abc import ABC
from collections.abc import Iterable
from logging import Logger, getLogger
from typing import TYPE_CHECKING

from llimona.utils import LoggerMixin

if TYPE_CHECKING:
    from llimona.id_builders import IdBuilderRegistry
    from llimona.provider_loaders import ProviderLoaderRegistry
    from llimona.providers import ProviderRegistry
    from llimona.sensors import SensorRegistry


class AddonMetadata(ABC):
    name: str
    display_name: str
    description: str

    def register_providers(self, registry: ProviderRegistry) -> None:  # noqa: B027 # pragma: no cover
        pass

    def register_provider_loaders(self, registry: ProviderLoaderRegistry) -> None:  # noqa: B027 # pragma: no cover
        pass

    def register_id_builders(self, registry: IdBuilderRegistry) -> None:  # noqa: B027 # pragma: no cover
        pass

    def register_sensors(self, registry: SensorRegistry) -> None:  # noqa: B027 # pragma: no cover
        pass


class Addons(LoggerMixin):
    def __init__(self, *, logger: Logger | None = None) -> None:
        super().__init__(logger=logger or getLogger('llimona.addons'))

        self._provider_addons_registered: set[str] = set()
        self._provider_loader_addons_registered: set[str] = set()
        self._id_builder_addons_registered: set[str] = set()
        self._sensor_addons_registered: set[str] = set()

    def list_available(self) -> Iterable[AddonMetadata]:
        from importlib.metadata import entry_points

        for entry_point in entry_points(group='llimona.addon'):
            yield entry_point.load()()

    def _register_addon_provider(self, addon: AddonMetadata, registry: ProviderRegistry):
        if addon.name in self._provider_addons_registered:
            self._logger.debug(f'Addon "{addon.name}" already registered, skipping.')
            return

        self._logger.info(f'Registering providers from addon: {addon.name}')
        addon.register_providers(registry)
        self._provider_addons_registered.add(addon.name)

    def register_all_providers(self):
        from llimona.providers import provider_registry

        for addon in self.list_available():
            self._register_addon_provider(addon, provider_registry)

    def register_addon_provider(self, addon_name: str):
        from llimona.providers import provider_registry

        for addon in self.list_available():
            if addon.name != addon_name:
                continue
            self._register_addon_provider(addon, provider_registry)
            return

        raise ValueError(f'Addon "{addon_name}" not found.')

    def _register_addon_provider_loader(self, addon: AddonMetadata, registry: ProviderLoaderRegistry):
        if addon.name in self._provider_loader_addons_registered:
            self._logger.debug(f'Addon "{addon.name}" already registered, skipping.')
            return

        self._logger.info(f'Registering provider loaders from addon: {addon.name}')
        addon.register_provider_loaders(registry)
        self._provider_loader_addons_registered.add(addon.name)

    def register_all_provider_loaders(self):
        from llimona.provider_loaders import provider_loader_registry

        for addon in self.list_available():
            self._register_addon_provider_loader(addon, provider_loader_registry)

    def register_addon_provider_loader(self, addon_name: str):
        from llimona.provider_loaders import provider_loader_registry

        for addon in self.list_available():
            if addon.name != addon_name:
                continue
            self._register_addon_provider_loader(addon, provider_loader_registry)
            return

        raise ValueError(f'Addon "{addon_name}" not found.')

    def _register_addon_id_builder(self, addon: AddonMetadata, registry: IdBuilderRegistry):
        if addon.name in self._id_builder_addons_registered:
            self._logger.debug(f'Addon "{addon.name}" already registered, skipping.')
            return

        self._logger.info(f'Registering ID builders from addon: {addon.name}')
        addon.register_id_builders(registry)
        self._id_builder_addons_registered.add(addon.name)

    def register_all_id_builders(self):
        from llimona.id_builders import id_builder_registry

        for addon in self.list_available():
            self._register_addon_id_builder(addon, id_builder_registry)

    def register_addon_id_builder(self, addon_name: str):
        from llimona.id_builders import id_builder_registry

        for addon in self.list_available():
            if addon.name != addon_name:
                continue
            self._register_addon_id_builder(addon, id_builder_registry)
            return

        raise ValueError(f'Addon "{addon_name}" not found.')

    def _register_addon_sensor(self, addon: AddonMetadata, registry: SensorRegistry):
        if addon.name in self._sensor_addons_registered:
            self._logger.debug(f'Addon "{addon.name}" already registered, skipping.')
            return

        self._logger.info(f'Registering sensors from addon: {addon.name}')
        addon.register_sensors(registry)
        self._sensor_addons_registered.add(addon.name)

    def register_all_sensors(self):
        from llimona.sensors import sensor_registry

        for addon in self.list_available():
            self._register_addon_sensor(addon, sensor_registry)

    def register_addon_sensor(self, addon_name: str):
        from llimona.sensors import sensor_registry

        for addon in self.list_available():
            if addon.name != addon_name:
                continue
            self._register_addon_sensor(addon, sensor_registry)
            return

        raise ValueError(f'Addon "{addon_name}" not found.')
