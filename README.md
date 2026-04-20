# Llimona

Llimona is an open and modular Python framework for building production-ready LLM gateways.
It provides OpenAI-compatible APIs, provider-aware routing, and an extensible plugin model for integrating multiple backends behind a single interface.

By keeping providers as addons, Llimona stays lightweight at its core while enabling deployments to include only the integrations, policies, and observability components they actually need.

## Key Features

- OpenAI-compatible service interfaces (currently Responses and Models).
- Provider routing using the `provider_name/model_name` naming convention.
- Addon-based extensibility through Python entry points (`llimona.addon`).
- Typed YAML configuration with Pydantic validation.
- Request `Context` propagation with actor/origin metadata, constraints, and sub-context trees.
- Sensor support for metrics such as request counters and elapsed time, making request execution observable.

## Architecture

[Architecture documentation](docs/arch.md)

## Requirements

- Python `>= 3.14`
- `uv` (recommended)

## Installation

### Install dependencies for local development

```bash
uv sync
```

### Install the core package

```bash
uv pip install .
```

### Install an addon package

```bash
uv pip install ./addons/llimona_azure_openai
```

## Quick Start

### 1) Create an app config

Example (`test_config/app.yaml`):

```yaml
provider_addons:
  - azure_openai
provider_loaders:
  - type: autodiscovery_dirs
    src: !path .
```

### 2) Create a provider directory with `provider.yaml`

Example (`example_config/azure_1/provider.yaml`):

```yaml
type: azure_openai
name: azure_1
display_name: Azure Example 1
owner_id: 444444-222-333-222 # Not used, just for future purposes
base_url: !envvar AZURE_OPENAI_1_BASE_URL
credentials:
  api_key: !envvar AZURE_OPENAI_1_API_KEY
services:
- type: openai_responses
- type: openai_models
models:
- name: gpt-4o-mini
  allowed_services:
  - openai_responses
```

### 3) Run a request

```bash
uv run llimona app --config-file example_config/app.yaml openai responses create azure_1/gpt-4o-mini "Hello" --stream
```

### 4) Observe sensor metrics

After the request completes, Llimona prints sensor values that make execution observable:

```text
Sensor value: elapsed_time=0.606314 (Elapsed time of the request.)
Sensor value: request_count=1 (Number of requests being processed for the sensor request_count.)
Sensor value: request_per_unit_of_time=1 (Number of requests in the last 0:01:00.)
Sensor value: request_per_window_of_time=1 (Number of requests until the next reset.)
```

## CLI Usage

### Top-level help

```bash
llimona --help
```

### List discovered addons

```bash
llimona addons
```

### Run commands with an app config

```bash
llimona app --config-file <path-to-app.yaml> <command>
```

### Providers

```bash
# list all providers
llimona app --config-file <cfg> providers

# inspect one provider
llimona app --config-file <cfg> providers <provider_name>

# list models in one provider
llimona app --config-file <cfg> providers <provider_name> models
```

### OpenAI-compatible interface commands

```bash
# create a response
llimona app --config-file <cfg> openai responses create <provider>/<model> "Prompt"

# streaming response
llimona app --config-file <cfg> openai responses create <provider>/<model> "Prompt" --stream

# list models (global or filtered by provider)
llimona app --config-file <cfg> openai models list
llimona app --config-file <cfg> openai models list <provider_name>
```

## Configuration Overview

The app configuration supports these top-level fields:

- `provider_addons`: provider addons to register.
- `provider_loader_addons`: provider-loader addons to register.
- `sensor_addons`: sensor addons to register.
- `id_builder`: optional ID builder configuration.
- `provider_loaders`: loader definitions.

Built-in provider loader:

- `autodiscovery_dirs`: scans child directories under `src`, reads `provider.yaml`, and optionally merges definitions from `models/*.yaml`, `services/*.yaml`, and `sensors/*.yaml`.

## Architecture Summary

Llimona receives OpenAI-compatible requests, decomposes model IDs, routes to the appropriate provider, and maps provider-specific responses back to interface models.

Every call flows through a `Context` object, which can carry:

- action metadata (`provider`, `service`, `service_action`, `model`)
- actor and origin information
- conversation metadata
- constraints
- collected sensor values

Routing strategies can create sub-contexts, enabling per-branch observability and post-execution failure inspection.

Sensors make the platform observable by exposing execution metrics across the full request context tree.

For full technical details, see `docs/arch.md`.

## Addons in This Repository

- `addons/llimona_azure_openai`: Azure OpenAI provider addon.
- `addons/llimona_smart_provider`: smart/virtual provider routing addon.

## Development

### Install development tools

```bash
uv sync --group dev
```

### Run tests

```bash
poe test
```

### Lint and format

```bash
poe fix
```

## Branching and Versioning

The repository follows a GitFlow-like model with:

- `main` as the default integration branch
- `feat/*`, `fix/*`, and `chore/*` working branches
- squash-merge pull requests
- SemVer/PEP 440 release semantics

See [branching model document](BRANCHING_MODEL.md) for the complete policy.

## Security Notes

- Do not commit real API keys or secrets in provider files.
- Inject credentials at runtime through your deployment environment.

## License

This project is licensed under the GNU AFFERO GENERAL PUBLIC LICENSE. See `LICENSE` for details.
