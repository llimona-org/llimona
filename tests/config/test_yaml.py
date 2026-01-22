import os
from contextlib import suppress
from datetime import timedelta
from pathlib import Path
from textwrap import dedent
from unittest import TestCase

import pytest
import yaml

from llimona.config.yaml import ConfigLoader


class ConfigLoaderEnvvarTests(TestCase):
    def tearDown(self) -> None:
        with suppress(Exception):
            del os.environ['ENV_VAR_NAME']
        with suppress(Exception):
            del os.environ['ENV_VAR_NAME_WITH_DEFAULT']
        return super().tearDown()

    def test_envvar_constructor_with_default_value(self):
        import os

        config_file = Path(__file__).parent / 'data/envvar.yaml'

        os.environ['ENV_VAR_NAME'] = 'env_var_value'

        config = yaml.load(config_file.open('r'), Loader=ConfigLoader)
        assert config['key1'] == 1
        assert config['key2'] == 'env_var_value'
        assert config['key3'] == 'default_value'

    def test_envvar_constructor_no_scalar_data(self):
        cwd = Path(__file__).parent / 'data'

        with pytest.raises(ValueError, match='Expected a scalar node'):
            yaml.load(
                dedent(
                    """
                    ---
                    var1: !envvar
                      key1: a
                      key2: b
                    """
                ),
                Loader=ConfigLoader.with_cwd(cwd=cwd),
            )


class ConfigLoaderIncludeTests(TestCase):
    def tearDown(self) -> None:
        with suppress(Exception):
            del os.environ['ENV_VAR_NAME']
        with suppress(Exception):
            del os.environ['ENV_VAR_NAME_WITH_DEFAULT']
        return super().tearDown()

    def test_include_constructor_no_ref_fail(self):
        cwd = Path(__file__).parent / 'data'

        with pytest.raises(ValueError, match='Tag suffix for !include cannot be empty'):
            yaml.load(
                dedent(
                    """
                    --- !include:
                    key1: a
                    key2: b
                    """
                ),
                Loader=ConfigLoader.with_cwd(cwd=cwd),
            )

    def test_envvar_constructor_no_default_value(self):
        config_file = Path(__file__).parent / 'data/envvar.yaml'

        os.environ['ENV_VAR_NAME'] = 'env_var_value'
        os.environ['ENV_VAR_NAME_WITH_DEFAULT'] = 'env_var_value_2'

        config = yaml.load(config_file.open('r'), Loader=ConfigLoader)
        assert config['key1'] == 1
        assert config['key2'] == 'env_var_value'
        assert config['key3'] == 'env_var_value_2'

    def test_envvar_constructor_no_set_value(self):
        config_file = Path(__file__).parent / 'data/envvar.yaml'

        config = yaml.load(config_file.open('r'), Loader=ConfigLoader)
        assert config['key1'] == 1
        assert config['key2'] is None
        assert config['key3'] == 'default_value'

    def test_include_constructor(self):
        config_file = Path(__file__).parent / 'data/compose_1.yaml'

        os.environ['ENV_VAR_NAME'] = 'env_var_value'
        os.environ['ENV_VAR_NAME_WITH_DEFAULT'] = 'env_var_value_2'

        config = yaml.load(config_file.open('r'), Loader=ConfigLoader.with_cwd(config_file.parent))
        assert config['included_key']['key1'] == 1
        assert config['included_key']['key2'] == 'env_var_value'
        assert config['included_key']['key3'] == 'env_var_value_2'
        assert config['key1'] == 1
        assert config['key2'] == 2

    def test_include_constructor_mapping(self):
        config_file = Path(__file__).parent / 'data/compose_mapping.yaml'

        os.environ['ENV_VAR_NAME'] = 'env_var_value'
        os.environ['ENV_VAR_NAME_WITH_DEFAULT'] = 'env_var_value_2'

        config = yaml.load(config_file.open('r'), Loader=ConfigLoader.with_cwd(config_file.parent))
        assert config['included_key']['key1'] == 1
        assert config['included_key']['key2'] == 'env_var_value'
        assert config['included_key']['key3'] == 'env_var_value_2'
        assert config['included_key']['key4'] == 1
        assert config['included_key']['key5'] == 2

    def test_include_constructor_mapping_override(self):
        config_file = Path(__file__).parent / 'data/compose_mapping_override.yaml'

        os.environ['ENV_VAR_NAME'] = 'env_var_value'
        os.environ['ENV_VAR_NAME_WITH_DEFAULT'] = 'env_var_value_2'
        os.environ['ENV_VAR_NAME_INNER_DATA'] = 'env_var_inner_value_1'

        config = yaml.load(config_file.open('r'), Loader=ConfigLoader.with_cwd(config_file.parent))
        assert config['included_key']['key1'] == 1
        assert config['included_key']['key2'] == 1
        assert config['included_key']['key3'] == 2
        assert config['included_key']['key4'] == 'env_var_inner_value_1'

    def test_include_constructor_mapping_root(self):
        cwd = Path(__file__).parent / 'data'

        config = yaml.load("""--- !include:compose_1.yaml""", Loader=ConfigLoader.with_cwd(cwd=cwd))
        assert config == {'included_key': {'key1': 1, 'key2': None, 'key3': 'default_value'}, 'key1': 1, 'key2': 2}

    def test_include_constructor_mapping_multi_level(self):
        cwd = Path(__file__).parent / 'data'

        config = yaml.load(
            dedent(
                """
                --- !include:extra/mapping.yaml
                key1: 10
                submap1:
                  submap2:
                    subkey4: value44
                    subkey5: value5
                """
            ),
            Loader=ConfigLoader.with_cwd(cwd=cwd),
        )
        assert config == {
            'key1': 10,
            'key2': 2,
            'submap1': {
                'subkey1': 'value1',
                'subkey2': 'value2',
                'submap2': {
                    'subkey3': 'value3',
                    'subkey4': 'value44',
                    'subkey5': 'value5',
                },
            },
        }

    def test_include_constructor_mapping_include_a_list_fail(self):
        cwd = Path(__file__).parent / 'data'

        with pytest.raises(ValueError, match='Expected a mapping'):
            yaml.load(
                dedent(
                    """
                    --- !include:extra/list_1.yaml
                    key1: a
                    key2: b
                    """
                ),
                Loader=ConfigLoader.with_cwd(cwd=cwd),
            )

    def test_include_constructor_mapping_include_a_scalar_fail(self):
        cwd = Path(__file__).parent / 'data'

        with pytest.raises(ValueError, match='Expected a mapping'):
            yaml.load(
                dedent(
                    """
                    --- !include:extra/scalar.yaml
                    key1: a
                    key2: b
                    """
                ),
                Loader=ConfigLoader.with_cwd(cwd=cwd),
            )

    def test_include_constructor_mapping_empty(self):
        cwd = Path(__file__).parent / 'data'

        result = yaml.load(
            dedent(
                """
                    --- !include:extra/empty.yaml
                    key1: a
                    key2: b
                    """
            ),
            Loader=ConfigLoader.with_cwd(cwd=cwd),
        )
        assert result == {'key1': 'a', 'key2': 'b'}

    def test_include_constructor_sequence(self):
        config_file = Path(__file__).parent / 'data/compose_list.yaml'

        config = yaml.load(config_file.open('r'), Loader=ConfigLoader.with_cwd(config_file.parent))
        assert config['included_key'] == ['a', 'b', 'c']

    def test_include_constructor_sequence_extended(self):
        config_file = Path(__file__).parent / 'data/compose_list_extended.yaml'

        config = yaml.load(config_file.open('r'), Loader=ConfigLoader.with_cwd(config_file.parent))
        assert config['included_key'] == ['a', 'b', 'c', 'd', 'e']

    def test_include_constructor_sequence_extended_root(self):
        cwd = Path(__file__).parent / 'data'

        config = yaml.load("""--- !include:extra/list_2.yaml""", Loader=ConfigLoader.with_cwd(cwd=cwd))
        assert config == ['a', 'b', 'c', 'd', 'e', 'f']

    def test_include_constructor_sequence_extended_no_file_fail(self):
        cwd = Path(__file__).parent / 'data'

        with pytest.raises(ValueError, match='Included file'):
            yaml.load(
                dedent(
                    """
                    --- !include:extra/list_no_exists.yaml
                    - g
                    """
                ),
                Loader=ConfigLoader.with_cwd(cwd=cwd),
            )

    def test_include_constructor_sequence_extended_dir_fail(self):
        cwd = Path(__file__).parent / 'data'

        with pytest.raises(ValueError, match='is not a file'):
            yaml.load(
                dedent(
                    """
                    --- !include:extra/
                    - g
                    """
                ),
                Loader=ConfigLoader.with_cwd(cwd=cwd),
            )

    def test_include_constructor_sequence_extended_no_sequence_fail(self):
        cwd = Path(__file__).parent / 'data'

        with pytest.raises(ValueError, match='Expected a sequence'):
            yaml.load(
                dedent(
                    """
                    --- !include:compose_mapping.yaml
                    - a
                    - b
                    """
                ),
                Loader=ConfigLoader.with_cwd(cwd=cwd),
            )

    def test_include_constructor_sequence_extended_no_sequence_scalar_fail(self):
        cwd = Path(__file__).parent / 'data'

        with pytest.raises(ValueError, match='Expected a sequence'):
            yaml.load(
                dedent(
                    """
                    --- !include:extra/scalar.yaml
                    - a
                    - b
                    """
                ),
                Loader=ConfigLoader.with_cwd(cwd=cwd),
            )

    def test_include_constructor_sequence_extended_empty(self):
        cwd = Path(__file__).parent / 'data'

        result = yaml.load(
            dedent(
                """
                    --- !include:extra/empty.yaml
                    - a
                    - b
                    """
            ),
            Loader=ConfigLoader.with_cwd(cwd=cwd),
        )
        assert result == ['a', 'b']

    def test_include_constructor_string(self):
        cwd = Path(__file__).parent / 'data'

        result = yaml.load(
            dedent(
                """
                ---
                included_key: !include:extra/scalar.yaml
                """
            ),
            Loader=ConfigLoader.with_cwd(cwd=cwd),
        )
        assert result['included_key'] == 'text'

    def test_include_constructor_string_suffix(self):
        cwd = Path(__file__).parent / 'data'

        result = yaml.load(
            dedent(
                """
                ---
                included_key: !include:extra/scalar.yaml _suffix
                """
            ),
            Loader=ConfigLoader.with_cwd(cwd=cwd),
        )
        assert result['included_key'] == 'text_suffix'

    def test_include_constructor_string_suffix_root(self):
        cwd = Path(__file__).parent / 'data'

        result = yaml.load(
            dedent(
                """
                --- !include:extra/scalar.yaml _suffix
                """
            ),
            Loader=ConfigLoader.with_cwd(cwd=cwd),
        )
        assert result == 'text_suffix'

    def test_include_constructor_string_include_no_string_fail(self):
        cwd = Path(__file__).parent / 'data'

        for f in ['compose_mapping.yaml', 'extra/integer.yaml', 'extra/float.yaml', 'extra/list_1.yaml']:
            with pytest.raises(ValueError, match='Expected a string'):
                yaml.load(
                    dedent(
                        f"""
                        --- !include:{f} _suffix
                        """
                    ),
                    Loader=ConfigLoader.with_cwd(cwd=cwd),
                )

    def test_include_constructor_integer(self):
        cwd = Path(__file__).parent / 'data'

        result = yaml.load(
            dedent(
                """
                ---
                included_key: !include:extra/integer.yaml
                """
            ),
            Loader=ConfigLoader.with_cwd(cwd=cwd),
        )
        assert result['included_key'] == 23

    def test_include_constructor_integer_plus(self):
        cwd = Path(__file__).parent / 'data'

        result = yaml.load(
            dedent(
                """
                ---
                included_key: !include:extra/integer.yaml 11
                """
            ),
            Loader=ConfigLoader.with_cwd(cwd=cwd),
        )
        assert result['included_key'] == 34

    def test_include_constructor_integer_plus_root(self):
        cwd = Path(__file__).parent / 'data'

        result = yaml.load(
            dedent(
                """
                --- !include:extra/integer.yaml 11
                """
            ),
            Loader=ConfigLoader.with_cwd(cwd=cwd),
        )
        assert result == 34

    def test_include_constructor_integer_include_no_numeric_fail(self):
        cwd = Path(__file__).parent / 'data'

        for f in ['compose_mapping.yaml', 'extra/scalar.yaml', 'extra/list_1.yaml']:
            with pytest.raises(ValueError, match='Expected a numeric value'):
                yaml.load(
                    dedent(
                        f"""
                        --- !include:{f} 13
                        """
                    ),
                    Loader=ConfigLoader.with_cwd(cwd=cwd),
                )


class ConfigLoaderPathTests(TestCase):
    def test_path_constructor_relative_path_with_cwd(self):
        cwd = Path(__file__).parent / 'data'

        result = yaml.load(
            dedent(
                """
                ---
                path_ref: !path extra/scalar.yaml
                """
            ),
            Loader=ConfigLoader.with_cwd(cwd=cwd),
        )

        assert result['path_ref'] == (cwd / 'extra/scalar.yaml').resolve()

    def test_path_constructor_absolute_path(self):
        absolute_path = (Path(__file__).parent / 'data/extra/scalar.yaml').resolve()

        result = yaml.load(
            dedent(
                f"""
                ---
                path_ref: !path {absolute_path}
                """
            ),
            Loader=ConfigLoader,
        )

        assert result['path_ref'] == absolute_path

    def test_path_constructor_no_scalar_data(self):
        cwd = Path(__file__).parent / 'data'

        with pytest.raises(ValueError, match='Expected a scalar node'):
            yaml.load(
                dedent(
                    """
                    ---
                    path_ref: !path
                      key1: a
                    """
                ),
                Loader=ConfigLoader.with_cwd(cwd=cwd),
            )


class ConfigLoaderTimedeltaTests(TestCase):
    def test_timedelta_constructor_single_part(self):
        result = yaml.load(
            dedent(
                """
                ---
                timeout: !timedelta 90s
                """
            ),
            Loader=ConfigLoader,
        )

        assert result['timeout'] == timedelta(seconds=90)

    def test_timedelta_constructor_multiple_parts(self):
        result = yaml.load(
            dedent(
                """
                ---
                timeout: !timedelta 1w 2d 3h 4m 5s 6ms 7us
                """
            ),
            Loader=ConfigLoader,
        )

        assert result['timeout'] == timedelta(
            weeks=1,
            days=2,
            hours=3,
            minutes=4,
            seconds=5,
            milliseconds=6,
            microseconds=7,
        )

    def test_timedelta_constructor_invalid_part(self):
        with pytest.raises(ValueError, match='Invalid timedelta part'):
            yaml.load(
                dedent(
                    """
                    ---
                    timeout: !timedelta 10x
                    """
                ),
                Loader=ConfigLoader,
            )

    def test_timedelta_constructor_empty_value(self):
        with pytest.raises(ValueError, match='Empty timedelta value'):
            yaml.load(
                dedent(
                    """
                    ---
                    timeout: !timedelta ""
                    """
                ),
                Loader=ConfigLoader,
            )

    def test_timedelta_constructor_no_scalar_data(self):
        with pytest.raises(ValueError, match='Expected a scalar node'):
            yaml.load(
                dedent(
                    """
                    ---
                    timeout: !timedelta
                      value: 5m
                    """
                ),
                Loader=ConfigLoader,
            )
