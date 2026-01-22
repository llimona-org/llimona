# llimona-azure-openai

`llimona-azure-openai` is the Azure provider addon for Llimona.

It integrates Azure OpenAI as a pluggable backend provider so Llimona can expose OpenAI-compatible interfaces while forwarding requests to Azure OpenAI endpoints.

## What this addon provides

- A provider addon discoverable through the `llimona.addon` entry-point group (`azure_openai`).
- A provider type: `azure_openai`.
- OpenAI Responses integration (`create`, `retrieve`, and `cancel`).
- OpenAI Models integration (`list`, `retrieve`, and `delete`).
- Streaming and non-streaming response mapping into Llimona interface models.

## Provider behavior

The addon builds an `AsyncAzureOpenAI` client from provider configuration:

- `base_url`: Azure OpenAI endpoint base URL.
- `credentials.api_key`: API key used for authentication.
- `api_version`: `v1`.

For response creation, the provider:

1. Validates whether the target model allows the requested service.
2. Translates Llimona request fields into Azure OpenAI Responses API parameters.
3. Calls Azure OpenAI.
4. Maps the returned payload (including stream events) into Llimona response/event types.

## Typical use cases

- Expose Azure OpenAI through a unified Llimona gateway.
- Combine Azure regions/providers behind a single routing layer.
- Reuse Llimona contexts, constraints, and sensors with Azure-backed workloads.
- Keep provider logic modular and independent from core application code.

## Minimal provider example

```yaml
type: azure_openai
name: azure_example
display_name: Azure Example
base_url: https://<your-resource>.openai.azure.com/openai/v1/
credentials:
  api_key: <your-api-key>
services:
  - type: openai_responses
  - type: openai_models
models:
  - name: gpt-4o-mini
    allowed_services:
      - openai_responses
```

## Installation

From PyPI:

```bash
pip install llimona-azure-openai
# or
uv pip install llimona-azure-openai
```

From this workspace:

```bash
uv pip install ./addons/llimona_azure_openai
```

## Notes

- This addon is designed to be loaded by a Llimona app configuration via `provider_addons`.
- Service-level access can be constrained per model using `allowed_services`.
- Observability is inherited from Llimona contexts and sensors, so Azure-backed requests remain traceable and measurable.

## License

This addon uses the same license as the `llimona` package: GNU AFFERO GENERAL PUBLIC LICENSE. See the repository `LICENSE` file for details.
