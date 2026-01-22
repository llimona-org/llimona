from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

import pytest
from pydantic import ValidationError

from llimona.provider_loaders import (
    AutodiscoveryProvidersDirsLoader,
    AutodiscoveryProvidersDirsLoaderDesc,
    ProviderDescDirectoryLoader,
)


class AutodiscoveryProvidersDirsLoaderTests(TestCase):
    def test_init_raises_value_error_when_src_does_not_exist(self):
        missing_path = Path('/tmp/llimona-provider-loader-missing-dir')
        desc = AutodiscoveryProvidersDirsLoaderDesc(src=missing_path)

        with pytest.raises(ValueError, match='does not exist'):
            AutodiscoveryProvidersDirsLoader(desc)

    def test_init_raises_value_error_when_src_is_not_directory(self):
        with TemporaryDirectory() as tmp_dir:
            src_file = Path(tmp_dir) / 'not-a-dir.txt'
            src_file.write_text('content')
            desc = AutodiscoveryProvidersDirsLoaderDesc(src=src_file)

            with pytest.raises(ValueError, match='is not a directory'):
                AutodiscoveryProvidersDirsLoader(desc)

    def test_load_providers_skips_non_directories_and_missing_provider_yaml(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / 'single-file.txt').write_text('content')

            missing_yaml_dir = root / 'missing-yaml'
            missing_yaml_dir.mkdir()

            valid_dir = root / 'provider-ok'
            valid_dir.mkdir()
            (valid_dir / 'provider.yaml').write_text('type: dummy')

            logger = mock.Mock()
            desc = AutodiscoveryProvidersDirsLoaderDesc(src=root)
            loader = AutodiscoveryProvidersDirsLoader(desc, logger=logger)

            with mock.patch('llimona.provider_loaders.ProviderDescDirectoryLoader') as loader_cls:
                loaded_provider = mock.sentinel.provider_desc
                loader_cls.return_value.load_provider_desc.return_value = loaded_provider

                result = list(loader.load_providers())

            assert result == [loaded_provider]
            assert loader_cls.call_count == 1
            assert loader_cls.call_args.args[0] == valid_dir
            assert loader_cls.call_args.kwargs['logger'] is logger
            assert logger.warning.call_count == 2

    def test_load_providers_continues_when_provider_loader_raises_value_error(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            first_dir = root / 'provider-a'
            first_dir.mkdir()
            (first_dir / 'provider.yaml').write_text('type: dummy')

            second_dir = root / 'provider-b'
            second_dir.mkdir()
            (second_dir / 'provider.yaml').write_text('type: dummy')

            logger = mock.Mock()
            desc = AutodiscoveryProvidersDirsLoaderDesc(src=root)
            loader = AutodiscoveryProvidersDirsLoader(desc, logger=logger)

            with mock.patch('llimona.provider_loaders.ProviderDescDirectoryLoader') as loader_cls:
                expected_provider = mock.sentinel.provider_desc
                loader_cls.return_value.load_provider_desc.side_effect = [
                    ValueError('broken provider'),
                    expected_provider,
                ]

                result = list(loader.load_providers())

            assert result == [expected_provider]
            assert loader_cls.call_count == 2
            loaded_dirs = {call.args[0] for call in loader_cls.call_args_list}
            assert loaded_dirs == {first_dir, second_dir}
            logger.error.assert_called_once()


class ProviderDescDirectoryLoaderTests(TestCase):
    def test_init_raises_value_error_when_src_does_not_exist(self):
        missing_path = Path('/tmp/llimona-provider-desc-loader-missing-dir')

        with pytest.raises(ValueError, match='does not exist'):
            ProviderDescDirectoryLoader(src=missing_path)

    def test_init_raises_value_error_when_src_is_not_directory(self):
        with TemporaryDirectory() as tmp_dir:
            src_file = Path(tmp_dir) / 'not-a-dir.txt'
            src_file.write_text('content')

            with pytest.raises(ValueError, match='is not a directory'):
                ProviderDescDirectoryLoader(src=src_file)

    def test_load_provider_desc_raises_when_provider_yaml_missing(self):
        with TemporaryDirectory() as tmp_dir:
            loader = ProviderDescDirectoryLoader(src=Path(tmp_dir))

            with pytest.raises(ValueError, match='does not exist'):
                loader.load_provider_desc()

    def test_load_provider_desc_raises_when_provider_yaml_is_not_a_file(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / 'provider.yaml').mkdir()
            loader = ProviderDescDirectoryLoader(src=root)

            with pytest.raises(ValueError, match='is not a file'):
                loader.load_provider_desc()

    def test_load_provider_desc_builds_desc_and_ignores_optional_dirs_when_missing(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / 'provider.yaml').write_text('type: mock\nname: provider-a\nowner: acme\n')
            logger = mock.Mock()
            loader = ProviderDescDirectoryLoader(src=root, logger=logger)
            adapter = mock.Mock()
            adapter.validate_python.return_value = mock.sentinel.provider_desc

            with (
                mock.patch.object(loader, 'load_models', side_effect=ValueError('no models')) as load_models,
                mock.patch.object(loader, 'load_services', return_value=['svc-a']) as load_services,
                mock.patch.object(loader, 'load_sensors', side_effect=ValueError('no sensors')) as load_sensors,
                mock.patch('llimona.providers.provider_registry.get_description_type_adapter', return_value=adapter),
            ):
                result = loader.load_provider_desc()

            assert result is mock.sentinel.provider_desc
            load_models.assert_called_once_with(silence=True)
            load_services.assert_called_once_with(silence=True)
            load_sensors.assert_called_once_with(silence=True)
            adapter.validate_python.assert_called_once_with(
                {'type': 'mock', 'name': 'provider-a', 'owner': 'acme', 'services': ['svc-a']}
            )
            logger.info.assert_called_once()

    def test_load_provider_desc_raises_value_error_on_invalid_provider_yaml(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / 'provider.yaml').write_text('type: [broken')
            loader = ProviderDescDirectoryLoader(src=root)

            with pytest.raises(ValueError, match='Error parsing YAML file'):
                loader.load_provider_desc()

    def test_load_yamls_from_dir_raises_value_error_when_path_is_not_directory(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            not_dir = root / 'models.yaml'
            not_dir.write_text('type: x')
            loader = ProviderDescDirectoryLoader(src=root)

            with pytest.raises(ValueError, match='does not exist or is not a directory'):
                list(loader._load_yamls_from_dir(not_dir, 'models'))

    def test_load_yamls_from_dir_returns_only_yaml_files(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            models_dir = root / 'models'
            models_dir.mkdir()
            (models_dir / 'a.yaml').write_text('name: a')
            (models_dir / 'b.yml').write_text('name: b')
            (models_dir / 'ignore.txt').write_text('name: ignored')
            loader = ProviderDescDirectoryLoader(src=root)

            result = list(loader._load_yamls_from_dir(models_dir, 'models'))

            assert len(result) == 2
            names = {item['name'] for item in result}
            assert names == {'a', 'b'}

    def test_load_yamls_from_dir_raises_value_error_on_invalid_yaml_file(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            models_dir = root / 'models'
            models_dir.mkdir()
            (models_dir / 'broken.yaml').write_text('name: [broken')
            loader = ProviderDescDirectoryLoader(src=root)

            with pytest.raises(ValueError, match='Error parsing YAML file'):
                list(loader._load_yamls_from_dir(models_dir, 'models'))

    def test_load_services_returns_validated_services(self):
        with TemporaryDirectory() as tmp_dir:
            loader = ProviderDescDirectoryLoader(src=Path(tmp_dir))

            with mock.patch.object(loader, '_load_yamls_from_dir', return_value=[{'type': 'openai_responses'}]):
                services = list(loader.load_services())

            assert len(services) == 1
            assert services[0].type == 'openai_responses'

    def test_load_services_raises_validation_error_for_invalid_service_payload(self):
        with TemporaryDirectory() as tmp_dir:
            loader = ProviderDescDirectoryLoader(src=Path(tmp_dir))

            with mock.patch.object(loader, '_load_yamls_from_dir', return_value=[{}]):
                with pytest.raises(ValidationError):
                    list(loader.load_services())
