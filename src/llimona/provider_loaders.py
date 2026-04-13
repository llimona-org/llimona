from abc import ABC, abstractmethod
from collections.abc import Iterable
from logging import Logger, getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal

import yaml
from pydantic_settings import BaseSettings

from llimona.component import BaseComponent, ComponentDescription
from llimona.config.yaml import ConfigLoader
from llimona.registries import ComponentDescriptionTypeMixin, ComponentRegistry
from llimona.utils import LoggerMixin, log_exceptions

if TYPE_CHECKING:
    from llimona.providers import BaseProviderDesc, ProviderModelDesc, ProviderServiceDesc
    from llimona.sensors import BaseSensorDesc


class BaseProviderLoaderDesc(ComponentDescription, BaseSettings):
    """Configuration for the provider auto-loader component."""

    pass


class BaseProviderLoader[TDesc: BaseProviderLoaderDesc](BaseComponent[TDesc], ABC):
    @log_exceptions
    def __init__(self, desc: TDesc, *, logger: Logger | None = None) -> None:
        super().__init__(desc=desc, logger=logger or getLogger('llimona.provider.autoloader'))

    @abstractmethod
    def load_providers(self) -> Iterable[BaseProviderDesc]:
        """Discover and load provider descriptions based on the configuration."""
        raise NotImplementedError()


class AutodiscoveryProvidersDirsLoaderDesc(BaseProviderLoaderDesc):
    """Configuration for the autodiscovery providers loader component."""

    type: Literal['autodiscovery_dirs'] = 'autodiscovery_dirs'  # type: ignore

    src: Path
    """The directory path to search for provider descriptions."""


class AutodiscoveryProvidersDirsLoader(BaseProviderLoader[AutodiscoveryProvidersDirsLoaderDesc]):
    @log_exceptions
    def __init__(self, desc: AutodiscoveryProvidersDirsLoaderDesc, *, logger: Logger | None = None) -> None:
        super().__init__(desc=desc, logger=logger or getLogger('llimona.provider.autodiscovery'))

        if not desc.src.exists():
            raise ValueError(f'Directory {desc.src} does not exist')
        if not desc.src.is_dir():
            raise ValueError(f'Path {desc.src} is not a directory')

    @log_exceptions
    def load_providers(self) -> Iterable[BaseProviderDesc]:
        for provider_dir in self._desc.src.iterdir():
            if not provider_dir.is_dir():
                self._logger.warning(f'Skipping {provider_dir} as it is not a directory')
                continue
            prov_file = provider_dir / 'provider.yaml'
            if not prov_file.exists() or not prov_file.is_file():
                self._logger.warning(f'Skipping {provider_dir} as it does not contain a valid provider.yaml file')
                continue

            try:
                loader = ProviderDescDirectoryLoader(provider_dir, logger=self._logger)
                yield loader.load_provider_desc()
            except ValueError as e:
                self._logger.error(f'Error loading provider from {provider_dir}: {e}')


class ProviderDescDirectoryLoader(LoggerMixin):
    @log_exceptions
    def __init__(self, src: Path, *, logger: Logger | None = None) -> None:
        super().__init__(logger=logger or getLogger('llimona.provider.config_loader'))

        if not src.exists():
            raise ValueError(f'Directory {src} does not exist')
        if not src.is_dir():
            raise ValueError(f'Path {src} is not a directory')

        self._src = src

    @log_exceptions
    def load_provider_desc(self) -> BaseProviderDesc:
        provider_desc_file = self._src / 'provider.yaml'

        if not provider_desc_file.exists():
            raise ValueError(
                f'Provider description file {provider_desc_file} does not exist',
            )

        if not provider_desc_file.is_file():
            raise ValueError(
                f'Provider description file {provider_desc_file} is not a file',
            )

        self._logger.info(f'Loading provider description from {provider_desc_file}...')

        params: dict[str, list[ProviderServiceDesc] | list[ProviderModelDesc]] = {}
        try:
            params['models'] = self.load_models(silence=True)  # type: ignore
        except ValueError:
            # No models found, continue without them
            pass

        try:
            params['services'] = self.load_services(silence=True)  # type: ignore
        except ValueError:
            # No services found, continue without them
            pass

        try:
            params['sensors'] = self.load_sensors(silence=True)  # type: ignore
        except ValueError:
            # No sensors found, continue without them
            pass

        try:
            return self._build_provider_desc(
                yaml.load(provider_desc_file.read_text(), Loader=ConfigLoader.with_cwd(provider_desc_file.parent)),
                **params,
            )
        except yaml.YAMLError as e:
            raise ValueError(
                f'Error parsing YAML file {provider_desc_file}: {e}',
            ) from e

    def _load_yamls_from_dir(
        self,
        dir_path: Path,
        entity_type: str,
    ) -> Iterable[dict[str, Any]]:
        if not dir_path.is_dir():
            raise ValueError(
                f'{entity_type.capitalize()} directory {dir_path} does not exist or is not a directory',
            )

        for f in dir_path.iterdir():
            if f.suffix not in ['.yaml', '.yml']:
                continue
            try:
                yield yaml.load(f.read_text(), Loader=ConfigLoader.with_cwd(f.parent))
            except yaml.YAMLError as e:
                raise ValueError(f'Error parsing YAML file {f}: {e}') from e

    @log_exceptions
    def load_models(self) -> Iterable[ProviderModelDesc]:
        from llimona.providers import ProviderModelDesc

        models_path = self._src / 'models'

        return [ProviderModelDesc.model_validate(m) for m in self._load_yamls_from_dir(models_path, 'models')]

    def _build_provider_desc(self, data: dict[str, Any], **kwargs) -> BaseProviderDesc:
        from llimona.providers import provider_registry

        return provider_registry.get_description_type_adapter().validate_python(data | kwargs)

    @log_exceptions
    def load_services(self) -> Iterable[ProviderServiceDesc]:
        from llimona.providers import ProviderServiceDesc

        services_path = self._src / 'services'

        return [ProviderServiceDesc.model_validate(s) for s in self._load_yamls_from_dir(services_path, 'services')]

    @log_exceptions
    def load_sensors(self) -> Iterable[BaseSensorDesc]:
        from llimona.sensors import sensor_registry

        sensors_path = self._src / 'sensors'

        return [
            sensor_registry.get_description_type_adapter().validate_python(s)
            for s in self._load_yamls_from_dir(sensors_path, 'sensors')
        ]


type ProviderLoaderRegistry = ComponentRegistry[BaseProviderLoaderDesc, BaseProviderLoader]

provider_loader_registry: ProviderLoaderRegistry = ComponentRegistry[BaseProviderLoaderDesc, BaseProviderLoader](
    name='provider_loaders'
)

# Register some provider loaders by default
provider_loader_registry.register_component(
    component_desc_cls=AutodiscoveryProvidersDirsLoaderDesc,
    component_cls=AutodiscoveryProvidersDirsLoader,
)


class ProviderLoaderType(ComponentDescriptionTypeMixin, BaseProviderLoaderDesc):
    registry: ClassVar[ProviderLoaderRegistry] = provider_loader_registry
