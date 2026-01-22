from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from pydantic import Field
from pydantic_settings import BaseSettings

from llimona.addons import Addons
from llimona.app import Llimona

if TYPE_CHECKING:
    from llimona.providers import BaseProvider, BaseProviderDesc


class ComponentConfig(BaseSettings):
    """Configuration for a generic component."""

    model_config = BaseSettings.model_config | {'extra': 'allow'}
    type: str = Field(..., description='The type of the component.')


class IdBuilderConfig(ComponentConfig):
    """Configuration for an ID builder component."""

    required_addon: str | None = Field(default=None, description='The name of the addon required for this component.')


class AppConfig(BaseSettings):
    """Application configuration settings."""

    # -----------------------------------------------------------------------
    # General Settings
    # -----------------------------------------------------------------------

    provider_addons: set[str] = Field(default_factory=set, description='List of addons to load at startup.')
    provider_loader_addons: set[str] = Field(
        default_factory=set, description='List of addons to load at startup for provider loaders.'
    )
    sensor_addons: set[str] = Field(default_factory=set, description='List of addons to load at startup for sensors.')

    id_builder: IdBuilderConfig | None = None
    """Configuration for the ID builder component."""

    provider_loaders: list[ComponentConfig] = Field(
        default_factory=list, description='List of provider loader configurations.'
    )


class AppBuilder:
    """Builder for constructing the application based on the provided configuration."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    async def build(self) -> Llimona:
        """Build and return the application instance."""

        addons_manager = Addons()

        [addons_manager.register_addon_sensor(addon_name) for addon_name in self.config.sensor_addons or []]

        [
            addons_manager.register_addon_provider_loader(addon_name)
            for addon_name in self.config.provider_loader_addons or []
        ]

        [addons_manager.register_addon_provider(addon_name) for addon_name in self.config.provider_addons or []]

        self._register_id_builder(addons_manager)

        return Llimona(providers=self._build_providers(), id_builder=self._load_id_builder())

    def _register_id_builder(self, addons_manager: Addons):
        from llimona.id_builders import id_builder_registry

        if self.config.id_builder is None or self.config.id_builder.required_addon is None:
            return

        required_addon = self.config.id_builder.required_addon

        addon = next((a for a in addons_manager.list_available() if a.name == required_addon), None)
        if addon is None:
            raise ValueError(
                f'ID builder "{self.config.id_builder.type}" requires addon "{required_addon}"'
                f' which is not available. Available addons: {[a.name for a in addons_manager.list_available()]}'
            )
        addon.register_id_builders(id_builder_registry)

    def _build_providers(self) -> Iterable[BaseProvider]:
        from llimona.provider_loaders import provider_loader_registry
        from llimona.providers import provider_registry

        for provider_loader_config in self.config.provider_loaders:
            provider_loader_desc = provider_loader_registry.get_description_type_adapter().validate_python(
                provider_loader_config.model_dump(),
                extra='ignore',
            )

            provider_loader = provider_loader_registry.build(provider_loader_desc)
            for provider_desc in provider_loader.load_providers():
                yield self._prepare_provider(provider_registry.build(provider_desc))

    def _prepare_provider(self, provider: BaseProvider[BaseProviderDesc]) -> BaseProvider[BaseProviderDesc]:
        from llimona.sensors import sensor_registry

        if not provider.provider.sensors:
            return provider

        for sensor_desc in provider.provider.sensors:
            sensor = sensor_registry.build(sensor_desc)
            provider.sensors.append(sensor)

        return provider

    def _load_id_builder(self) -> Any:
        from llimona.id_builders import id_builder_registry

        if self.config.id_builder is None:
            return None

        id_builder_desc = id_builder_registry.get_description_type_adapter().validate_python(
            self.config.id_builder.model_dump(exclude={'required_addon'}), extra='ignore'
        )
        return id_builder_registry.build(id_builder_desc)
