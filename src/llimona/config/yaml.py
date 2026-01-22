import os
import re
from collections.abc import Callable, Mapping, MutableMapping
from datetime import timedelta
from functools import partial
from pathlib import Path
from typing import Any, Self, cast

import yaml

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:  # pragma: no cover
    from yaml import SafeLoader  # type: ignore[assignment]

type ConstructorType = Callable[[ConfigLoader, yaml.Node], Any]
type MultiConstructorType = Callable[[ConfigLoader, str, yaml.Node], Any]


class ConfigLoader(SafeLoader):  # pyright: ignore[reportGeneralTypeIssues]
    def __init__(self, stream: Any, cwd: Path | None = None) -> None:
        super().__init__(stream)
        self._cwd = cwd or Path.cwd()

    @property
    def cwd(self) -> Path:
        return self._cwd

    @classmethod
    def with_cwd(cls, cwd: Path) -> type[Self]:
        return cast(type[Self], partial(cls, cwd=cwd))

    @classmethod
    def register_constructor(cls, tag_suffix: str) -> Callable[[ConstructorType], ConstructorType]:
        def decorator(func: ConstructorType) -> ConstructorType:
            cls.add_constructor(tag_suffix, func)
            return func

        return decorator

    @classmethod
    def register_multi_constructor(cls, tag_suffix: str) -> Callable[[MultiConstructorType], MultiConstructorType]:
        def decorator(func: MultiConstructorType) -> MultiConstructorType:
            cls.add_multi_constructor(tag_suffix, func)
            return func

        return decorator


@ConfigLoader.register_constructor('!envvar')
def construct_envvar(loader: ConfigLoader, node: yaml.Node) -> Any:
    if not isinstance(node, yaml.ScalarNode):
        raise ValueError(f'Expected a scalar node for !envvar, got {type(node)}')

    value = loader.construct_scalar(node)
    if ':' in value:
        envvar_name, default = value.split(':', 1)
        return os.getenv(envvar_name.strip(), default.strip())
    else:
        return os.getenv(value.strip())


@ConfigLoader.register_constructor('!path')
def construct_path(loader: ConfigLoader, node: yaml.Node) -> Any:
    if not isinstance(node, yaml.ScalarNode):
        raise ValueError(f'Expected a scalar node for !path, got {type(node)}')

    value = Path(loader.construct_scalar(node))

    if not value.is_absolute():
        value = (loader.cwd / value).resolve()

    return value


TIMEDELTA_PART_REGEX = re.compile(r'^(?P<value>\d+)(?P<unit>us|ms|[smhdw])$')
TIMEDELTA_UNIT_MAP = {
    'us': 'microseconds',
    'ms': 'milliseconds',
    's': 'seconds',
    'm': 'minutes',
    'h': 'hours',
    'd': 'days',
    'w': 'weeks',
}


def _parse_td_part(part: str) -> tuple[str, int]:
    match = TIMEDELTA_PART_REGEX.match(part)
    if not match:
        raise ValueError(f'Invalid timedelta part: {part}')

    num_str = match.group('value')
    unit_str = match.group('unit')

    num = int(num_str)
    unit = unit_str.lower()

    return TIMEDELTA_UNIT_MAP[unit], num


@ConfigLoader.register_constructor('!timedelta')
def construct_timedelta(loader: ConfigLoader, node: yaml.Node) -> Any:
    if not isinstance(node, yaml.ScalarNode):
        raise ValueError(f'Expected a scalar node for !timedelta, got {type(node)}')

    value = loader.construct_scalar(node).strip()
    if not value:
        raise ValueError('Empty timedelta value')

    kwargs = dict(_parse_td_part(v_stripped) for v in value.split(' ') if (v_stripped := v.strip()))

    return timedelta(**kwargs)


@ConfigLoader.register_multi_constructor('!include:')
def construct_include(loader: ConfigLoader, tag_suffix: str, node: yaml.Node) -> Any:
    tag_suffix = tag_suffix.strip()

    if not tag_suffix:
        raise ValueError('Tag suffix for !include cannot be empty')

    value = Path(tag_suffix)

    if not value.is_absolute():
        value = (loader.cwd / value).resolve()

    if not value.exists():
        raise ValueError(f'Included file {value} does not exist')

    if not value.is_file():
        raise ValueError(f'Included path {value} is not a file')

    inner_data: dict | list | str | int | float | None = None
    match node:
        case yaml.MappingNode():
            inner_data = loader.construct_mapping(node, deep=True)
        case yaml.SequenceNode():
            inner_data = loader.construct_sequence(node, deep=True)
        case yaml.ScalarNode():
            inner_data = loader.__class__(node.value, cwd=value.parent).get_single_data()
        case _:  # pragma: no cover
            raise ValueError(f'Unsupported node type {type(node)} for !include')

    with value.open('r') as fd:
        new_loader = loader.__class__(fd, cwd=value.parent)
        try:
            included_data = new_loader.get_single_data()
        finally:
            new_loader.dispose()

    if included_data is None:
        return inner_data

    if inner_data is None or inner_data == '':
        return included_data

    if isinstance(inner_data, Mapping):
        if not isinstance(included_data, Mapping):
            raise ValueError(f'Expected a mapping in included file {value}, got {type(included_data)}')
        return _mapping_merge(included_data, inner_data)
    elif isinstance(inner_data, list):
        if not isinstance(included_data, list):
            raise ValueError(f'Expected a sequence in included file {value}, got {type(included_data)}')
        included_data.extend(inner_data)
        return included_data
    elif isinstance(inner_data, str):
        if not isinstance(included_data, str):
            raise ValueError(f'Expected a string in included file {value}, got {type(included_data)}')
        return included_data + inner_data
    elif isinstance(inner_data, (int, float, complex)):
        if not isinstance(included_data, (int, float, complex)):
            raise ValueError(f'Expected a numeric value in included file {value}, got {type(included_data)}')
        return included_data + inner_data

    raise ValueError(
        f'Unsupported data type {type(inner_data)} for merging included data from file {value}'
    )  # pragma: no cover


def _mapping_merge(base: Mapping[Any, Any], new: Mapping[Any, Any]) -> Mapping[Any, Any]:
    result = dict(base)
    for key, value in new.items():
        if key in result and isinstance(result[key], MutableMapping) and isinstance(value, Mapping):
            result[key] = _mapping_merge(result[key], value)
        else:
            result[key] = value

    return result
