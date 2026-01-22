from unittest import TestCase, mock

import pytest

from llimona.addons import Addons


class _FakeAddon:
    def __init__(self, name: str) -> None:
        self.name = name
        self.register_providers = mock.Mock()
        self.register_provider_loaders = mock.Mock()
        self.register_id_builders = mock.Mock()
        self.register_sensors = mock.Mock()


class AddonsListAvailableTests(TestCase):
    def test_list_available_loads_addons_from_entry_points(self):
        addon_a = _FakeAddon('a')
        addon_b = _FakeAddon('b')

        entry_point_a = mock.Mock()
        entry_point_a.load.return_value = lambda: addon_a
        entry_point_b = mock.Mock()
        entry_point_b.load.return_value = lambda: addon_b

        with mock.patch(
            'importlib.metadata.entry_points',
            return_value=[entry_point_a, entry_point_b],
        ):
            addons = Addons()
            loaded = list(addons.list_available())

        assert loaded == [addon_a, addon_b]


class AddonsRegisterProviderTests(TestCase):
    def test_register_addon_provider_registers_matching_addon(self):
        addons = Addons()
        addon_a = _FakeAddon('addon-a')
        addon_b = _FakeAddon('addon-b')

        with mock.patch.object(addons, 'list_available', return_value=[addon_a, addon_b]):
            addons.register_addon_provider('addon-b')

        addon_a.register_providers.assert_not_called()
        addon_b.register_providers.assert_called_once()

    def test_register_addon_provider_raises_when_not_found(self):
        addons = Addons()
        addon = _FakeAddon('addon-a')

        with mock.patch.object(addons, 'list_available', return_value=[addon]):
            with pytest.raises(ValueError, match='Addon "missing" not found'):
                addons.register_addon_provider('missing')

    def test_register_all_providers_registers_all_once(self):
        addons = Addons()
        addon_a = _FakeAddon('addon-a')
        addon_b = _FakeAddon('addon-b')

        with mock.patch.object(addons, 'list_available', return_value=[addon_a, addon_b]):
            addons.register_all_providers()

        addon_a.register_providers.assert_called_once()
        addon_b.register_providers.assert_called_once()

    def test_register_all_providers_skips_already_registered_addon(self):
        addons = Addons()
        addon = _FakeAddon('addon-a')

        with mock.patch.object(addons, 'list_available', return_value=[addon]):
            addons.register_all_providers()
            addons.register_all_providers()

        addon.register_providers.assert_called_once()


class AddonsRegisterProviderLoaderTests(TestCase):
    def test_register_addon_provider_loader_registers_matching_addon(self):
        addons = Addons()
        addon_a = _FakeAddon('addon-a')
        addon_b = _FakeAddon('addon-b')

        with mock.patch.object(addons, 'list_available', return_value=[addon_a, addon_b]):
            addons.register_addon_provider_loader('addon-b')

        addon_a.register_provider_loaders.assert_not_called()
        addon_b.register_provider_loaders.assert_called_once()

    def test_register_addon_provider_loader_raises_when_not_found(self):
        addons = Addons()

        with mock.patch.object(addons, 'list_available', return_value=[]):
            with pytest.raises(ValueError, match='Addon "missing" not found'):
                addons.register_addon_provider_loader('missing')

    def test_register_all_provider_loaders_skips_already_registered_addon(self):
        addons = Addons()
        addon = _FakeAddon('addon-a')

        with mock.patch.object(addons, 'list_available', return_value=[addon]):
            addons.register_all_provider_loaders()
            addons.register_all_provider_loaders()

        addon.register_provider_loaders.assert_called_once()


class AddonsRegisterIdBuilderTests(TestCase):
    def test_register_addon_id_builder_registers_matching_addon(self):
        addons = Addons()
        addon_a = _FakeAddon('addon-a')
        addon_b = _FakeAddon('addon-b')

        with mock.patch.object(addons, 'list_available', return_value=[addon_a, addon_b]):
            addons.register_addon_id_builder('addon-b')

        addon_a.register_id_builders.assert_not_called()
        addon_b.register_id_builders.assert_called_once()

    def test_register_addon_id_builder_raises_when_not_found(self):
        addons = Addons()

        with mock.patch.object(addons, 'list_available', return_value=[]):
            with pytest.raises(ValueError, match='Addon "missing" not found'):
                addons.register_addon_id_builder('missing')

    def test_register_all_id_builders_skips_already_registered_addon(self):
        addons = Addons()
        addon = _FakeAddon('addon-a')

        with mock.patch.object(addons, 'list_available', return_value=[addon]):
            addons.register_all_id_builders()
            addons.register_all_id_builders()

        addon.register_id_builders.assert_called_once()


class AddonsRegisterSensorTests(TestCase):
    def test_register_addon_sensor_registers_matching_addon(self):
        addons = Addons()
        addon_a = _FakeAddon('addon-a')
        addon_b = _FakeAddon('addon-b')

        with mock.patch.object(addons, 'list_available', return_value=[addon_a, addon_b]):
            addons.register_addon_sensor('addon-b')

        addon_a.register_sensors.assert_not_called()
        addon_b.register_sensors.assert_called_once()

    def test_register_addon_sensor_raises_when_not_found(self):
        addons = Addons()

        with mock.patch.object(addons, 'list_available', return_value=[]):
            with pytest.raises(ValueError, match='Addon "missing" not found'):
                addons.register_addon_sensor('missing')

    def test_register_all_sensors_skips_already_registered_addon(self):
        addons = Addons()
        addon = _FakeAddon('addon-a')

        with mock.patch.object(addons, 'list_available', return_value=[addon]):
            addons.register_all_sensors()
            addons.register_all_sensors()

        addon.register_sensors.assert_called_once()
