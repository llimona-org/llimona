import base64
from unittest import IsolatedAsyncioTestCase

import pytest
from pydantic import Secret

from llimona.id_builders import (
    AES256IdBuilder,
    AES256IdBuilderDesc,
    Base64IdBuilder,
    Base64IdBuilderDesc,
    PlainIdBuilder,
    PlainIdBuilderDesc,
)


class PlainIdBuilderTests(IsolatedAsyncioTestCase):
    async def test_build_response_id_with_default_separator(self):
        builder = PlainIdBuilder(PlainIdBuilderDesc())

        result = await builder.build_response_id('provider-a', 'actor-b', 'response-c')

        assert result == 'provider-a:actor-b:response-c'

    async def test_debuild_response_id_with_default_separator(self):
        builder = PlainIdBuilder(PlainIdBuilderDesc())

        result = await builder.debuild_response_id('provider-a:actor-b:response-c')

        assert result == ('provider-a', 'actor-b', 'response-c')

    async def test_roundtrip_with_custom_separator_and_separator_inside_response(self):
        builder = PlainIdBuilder(PlainIdBuilderDesc(separator='|'))

        built_id = await builder.build_response_id('provider-a', 'actor-b', 'response|with|pipes')
        result = await builder.debuild_response_id(built_id)

        assert built_id == 'provider-a|actor-b|response|with|pipes'
        assert result == ('provider-a', 'actor-b', 'response|with|pipes')

    async def test_debuild_response_id_with_invalid_format_raises_value_error(self):
        builder = PlainIdBuilder(PlainIdBuilderDesc())

        with pytest.raises(ValueError, match='Invalid response ID format'):
            await builder.debuild_response_id('provider-a:actor-b')


class Base64IdBuilderTests(IsolatedAsyncioTestCase):
    async def test_build_response_id_with_default_separator(self):
        builder = Base64IdBuilder(Base64IdBuilderDesc())

        result = await builder.build_response_id('provider-a', 'actor-b', 'response-c')

        expected = base64.urlsafe_b64encode(b'provider-a:actor-b:response-c').rstrip(b'=').decode()
        assert result == expected

    async def test_debuild_response_id_with_default_separator(self):
        builder = Base64IdBuilder(Base64IdBuilderDesc())
        encoded_id = base64.urlsafe_b64encode(b'provider-a:actor-b:response-c').rstrip(b'=').decode()

        result = await builder.debuild_response_id(encoded_id)

        assert result == ('provider-a', 'actor-b', 'response-c')

    async def test_roundtrip_with_custom_separator_and_separator_inside_response(self):
        builder = Base64IdBuilder(Base64IdBuilderDesc(separator='|'))

        built_id = await builder.build_response_id('provider-a', 'actor-b', 'response|with|pipes')
        result = await builder.debuild_response_id(built_id)

        assert '=' not in built_id
        assert result == ('provider-a', 'actor-b', 'response|with|pipes')

    async def test_debuild_response_id_with_invalid_decoded_format_raises_value_error(self):
        builder = Base64IdBuilder(Base64IdBuilderDesc())
        encoded_id = base64.urlsafe_b64encode(b'provider-a:actor-b').rstrip(b'=').decode()

        with pytest.raises(ValueError, match='Invalid response ID format'):
            await builder.debuild_response_id(encoded_id)


class AES256IdBuilderTests(IsolatedAsyncioTestCase):
    @staticmethod
    def _encode_key(raw_key: bytes) -> bytes:
        return base64.urlsafe_b64encode(raw_key)

    async def test_build_response_id_and_debuild_roundtrip(self):
        key = self._encode_key(b'0123456789abcdef0123456789abcdef')
        builder = AES256IdBuilder(AES256IdBuilderDesc(key=Secret(key)))

        built_id = await builder.build_response_id('provider-a', 'actor-b', 'response-c')
        result = await builder.debuild_response_id(built_id)

        assert '=' not in built_id
        assert result == ('provider-a', 'actor-b', 'response-c')

    async def test_roundtrip_with_custom_separator_and_separator_inside_response(self):
        key = self._encode_key(b'abcdefghijklmnopqrstuvwx12345678')
        builder = AES256IdBuilder(AES256IdBuilderDesc(key=Secret(key), separator='|'))

        built_id = await builder.build_response_id('provider-a', 'actor-b', 'response|with|pipes')
        result = await builder.debuild_response_id(built_id)

        assert result == ('provider-a', 'actor-b', 'response|with|pipes')

    async def test_debuild_response_id_uses_fallback_keys(self):
        old_key = self._encode_key(b'11111111111111111111111111111111')
        new_key = self._encode_key(b'22222222222222222222222222222222')

        old_builder = AES256IdBuilder(AES256IdBuilderDesc(key=Secret(old_key)))
        new_builder = AES256IdBuilder(AES256IdBuilderDesc(key=Secret(new_key), fallback_keys=[Secret(old_key)]))

        built_id = await old_builder.build_response_id('provider-a', 'actor-b', 'response-c')
        result = await new_builder.debuild_response_id(built_id)

        assert result == ('provider-a', 'actor-b', 'response-c')

    async def test_debuild_response_id_with_invalid_payload_raises_value_error(self):
        key = self._encode_key(b'0123456789abcdef0123456789abcdef')
        builder = AES256IdBuilder(AES256IdBuilderDesc(key=Secret(key)))

        with pytest.raises(ValueError, match=r'Invalid response ID\.'):
            await builder.debuild_response_id('invalid-payload')

    async def test_debuild_response_id_raises_value_error_when_no_key_can_decrypt(self):
        encrypt_key = self._encode_key(b'33333333333333333333333333333333')
        decrypt_key = self._encode_key(b'44444444444444444444444444444444')

        encrypt_builder = AES256IdBuilder(AES256IdBuilderDesc(key=Secret(encrypt_key)))
        decrypt_builder = AES256IdBuilder(AES256IdBuilderDesc(key=Secret(decrypt_key)))

        built_id = await encrypt_builder.build_response_id('provider-a', 'actor-b', 'response-c')

        with pytest.raises(ValueError, match='Invalid response ID or all keys are incorrect'):
            await decrypt_builder.debuild_response_id(built_id)
