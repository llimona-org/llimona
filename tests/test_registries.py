from typing import Literal
from unittest import TestCase

import pytest
from pydantic import BaseModel, ValidationError

from llimona.component import BaseComponent, ComponentDescription
from llimona.registries import ComponentRegistry


class DummyDescA(ComponentDescription):
    type: Literal['a'] = 'a'  # type: ignore
    value: int = 1


class DummyDescB(ComponentDescription):
    type: Literal['b'] = 'b'  # type: ignore
    name: str = 'demo'


class DummyComponentA(BaseComponent[DummyDescA]):
    pass


class DummyComponentB(BaseComponent[DummyDescB]):
    pass


class ComponentRegistryTests(TestCase):
    def test_get_description_type_without_components(self):
        registry = ComponentRegistry(name='tests')

        assert registry.get_description_type() is None

    def test_register_component_and_lookup_classes(self):
        registry = ComponentRegistry(name='tests')

        registry.register_component(DummyDescA, DummyComponentA)

        assert registry.get_description_class('a') is DummyDescA
        assert registry.get_component_class('a') is DummyComponentA

    def test_build_component_instance(self):
        registry = ComponentRegistry(name='tests')
        registry.register_component(DummyDescA, DummyComponentA)

        desc = DummyDescA(value=10)
        component = registry.build(desc)

        assert isinstance(component, DummyComponentA)
        assert component.desc == desc

    def test_description_type_adapter_validates_registered_type(self):
        registry = ComponentRegistry(name='tests')
        registry.register_component(DummyDescA, DummyComponentA)

        adapter = registry.get_description_type_adapter()
        parsed = adapter.validate_python({'type': 'a', 'value': 7})

        assert isinstance(parsed, DummyDescA)
        assert parsed.value == 7

    def test_description_type_adapter_rejects_unknown_type(self):
        registry = ComponentRegistry(name='tests')
        registry.register_component(DummyDescA, DummyComponentA)

        adapter = registry.get_description_type_adapter()

        with pytest.raises(ValidationError):
            adapter.validate_python({'type': 'unknown'})

    def test_register_component_clears_adapter_cache(self):
        registry = ComponentRegistry(name='tests')
        registry.register_component(DummyDescA, DummyComponentA)

        first_adapter = registry.get_description_type_adapter()
        with pytest.raises(ValidationError):
            first_adapter.validate_python({'type': 'b'})

        registry.register_component(DummyDescB, DummyComponentB)

        second_adapter = registry.get_description_type_adapter()
        parsed = second_adapter.validate_python({'type': 'b', 'name': 'ok'})

        assert isinstance(parsed, DummyDescB)
        assert parsed.name == 'ok'

    def test_register_component_without_type_field_raises_value_error(self):
        class BadDesc(BaseModel):
            code: str = 'bad'

        registry = ComponentRegistry(name='tests')

        with pytest.raises(ValueError, match='must have a "type" field'):
            registry.register_component(BadDesc, DummyComponentA)  # type: ignore[arg-type]
