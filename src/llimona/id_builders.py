from abc import ABC, abstractmethod
from logging import Logger, getLogger
from typing import Annotated, ClassVar, Literal, cast

from annotated_types import MaxLen, MinLen
from pydantic import ConfigDict, EncodedBytes, Field, Secret
from pydantic.types import Base64UrlEncoder

from llimona.component import BaseComponent, ComponentDescription
from llimona.registries import ComponentDescriptionTypeMixin, ComponentRegistry


class BaseIdBuilderDesc(ComponentDescription):
    """Configuration for the ID builder component."""

    pass


class BaseIdBuilder[TDesc: BaseIdBuilderDesc](BaseComponent[TDesc], ABC):
    """Base class for ID builder components."""

    def __init__(self, desc: TDesc, *, logger: Logger | None = None) -> None:
        super().__init__(desc=desc, logger=logger or getLogger('llimona.id_builder'))

    @abstractmethod
    async def build_response_id(self, provider_id: str, actor_id: str, response_id: str) -> str:
        """Build a unique ID for a given provider and model."""
        raise NotImplementedError()

    @abstractmethod
    async def debuild_response_id(self, response_id: str) -> tuple[str, str, str]:
        """Revert a unique ID back to its original components."""
        raise NotImplementedError()


class PlainIdBuilderDesc(BaseIdBuilderDesc):
    """Configuration for the PlainIdBuilder component."""

    model_config = ConfigDict(extra='ignore')

    type: Literal['plain'] = 'plain'  # type: ignore

    separator: str = ':'
    """The separator to use between the components of the ID."""


class BasePlainIdBuilder[TDesc: PlainIdBuilderDesc](BaseIdBuilder[TDesc], ABC):
    """A simple ID builder that returns the response ID as is."""

    async def build_response_id(self, provider_id: str, actor_id: str, response_id: str) -> str:
        return self._desc.separator.join([provider_id, actor_id, response_id])

    async def debuild_response_id(self, response_id: str) -> tuple[str, str, str]:
        parts = response_id.split(self._desc.separator, 2)
        if len(parts) != 3:
            raise ValueError(f'Invalid response ID format: {response_id}')
        return cast(tuple[str, str, str], tuple(parts))


class PlainIdBuilder(BasePlainIdBuilder[PlainIdBuilderDesc]):
    """A simple ID builder that returns the response ID as is."""

    pass


class Base64IdBuilderDesc(PlainIdBuilderDesc):
    """Configuration for the Base64IdBuilder component."""

    type: Literal['base64'] = 'base64'  # type: ignore


class Base64IdBuilder(BasePlainIdBuilder[Base64IdBuilderDesc]):
    """An ID builder that encodes the response ID using URL-safe Base64 encoding."""

    async def build_response_id(self, provider_id: str, actor_id: str, response_id: str) -> str:
        from base64 import urlsafe_b64encode

        return (
            urlsafe_b64encode((await super().build_response_id(provider_id, actor_id, response_id)).encode())
            .rstrip(b'=')
            .decode()  # type: ignore
        )

    async def debuild_response_id(self, response_id: str) -> tuple[str, str, str]:
        from base64 import urlsafe_b64decode

        raw_id = urlsafe_b64decode(response_id.encode() + b'==').decode()

        return await super().debuild_response_id(raw_id)  # type: ignore


class AES256IdBuilderDesc(PlainIdBuilderDesc):
    """Configuration for the AES256IdBuilder component."""

    type: Literal['aes256'] = 'aes256'  # type: ignore

    key: Secret[Annotated[bytes, EncodedBytes(encoder=Base64UrlEncoder), MinLen(32), MaxLen(32)]] = Field(
        description='The 32-byte encryption key to use for the ID builder.',
    )
    """The encryption key to use for the ID builder."""

    fallback_keys: list[Secret[Annotated[bytes, EncodedBytes(encoder=Base64UrlEncoder), MinLen(32), MaxLen(32)]]] = (
        Field(
            default_factory=list,
            description='A list of fallback encryption keys to use for debuilding IDs'
            ' that were built with previous keys.',
        )
    )


class AES256IdBuilder(BasePlainIdBuilder[AES256IdBuilderDesc]):
    """An ID builder that encodes the response ID using AES-256 encryption."""

    def __init__(self, desc: AES256IdBuilderDesc, *, logger: Logger | None = None) -> None:
        super().__init__(desc, logger=logger)
        try:
            from Crypto.Cipher import AES  # noqa: F401
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                'PyCryptodome is required for AES256IdBuilder. Please install it with "pip install llimona[crypt]"'
            ) from e

    def get_main_key(self) -> bytes:
        return self._desc.key.get_secret_value()

    def get_fallback_keys(self) -> list[bytes]:
        return [key.get_secret_value() for key in self._desc.fallback_keys]

    async def build_response_id(self, provider_id: str, actor_id: str, response_id: str) -> str:
        from base64 import urlsafe_b64encode

        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad

        raw_id = await super().build_response_id(provider_id, actor_id, response_id)
        cipher = AES.new(self.get_main_key(), AES.MODE_CBC)
        encrypted_id = cast(bytes, cipher.iv) + cast(bytes, cipher.encrypt(pad(raw_id.encode(), AES.block_size)))

        return urlsafe_b64encode(encrypted_id).rstrip(b'=').decode()

    async def debuild_response_id(self, response_id: str) -> tuple[str, str, str]:
        from base64 import urlsafe_b64decode

        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad

        padded_response_id = response_id + '=' * (-len(response_id) % 4)
        encrypted_payload = urlsafe_b64decode(padded_response_id.encode())
        if len(encrypted_payload) <= AES.block_size:
            raise ValueError('Invalid response ID.')

        iv = encrypted_payload[: AES.block_size]
        encrypted_id = encrypted_payload[AES.block_size :]

        for key in [self.get_main_key(), *self.get_fallback_keys()]:
            try:
                cipher = AES.new(key, AES.MODE_CBC, iv=iv)
                decrypted_id = unpad(cipher.decrypt(encrypted_id), AES.block_size).decode()
                return await super().debuild_response_id(decrypted_id)
            except Exception:
                continue

        raise ValueError('Invalid response ID or all keys are incorrect.')


type IdBuilderRegistry = ComponentRegistry[BaseIdBuilderDesc, BaseIdBuilder]

id_builder_registry: IdBuilderRegistry = ComponentRegistry[BaseIdBuilderDesc, BaseIdBuilder](name='id_builders')


class IdBuilderType(ComponentDescriptionTypeMixin, BaseIdBuilderDesc):
    registry: ClassVar[IdBuilderRegistry] = id_builder_registry
