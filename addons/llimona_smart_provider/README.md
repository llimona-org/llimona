# llimona-smart-provider

`llimona-smart-provider` is an addon for Llimona that introduces smart virtual providers.

A smart provider exposes a model name to clients and internally routes the request across one or more target models/providers, with ordered fallback when a target fails.

## What this addon provides

- A provider addon discoverable through the `llimona.addon` entry-point group (`smart_provider`).
- A smart model definition with a `targets` list.
- Sequential fallback strategy: targets are tried in order until one succeeds.
- OpenAI Responses integration (`create`, `retrieve`, and `cancel`) through Llimona’s interface layer.

## Routing behavior

For `create` requests, the smart provider:

1. Resolves the requested smart model.
2. Iterates over the configured targets in order.
3. Tries each target model through `app.openai_responses.create(...)`.
4. Returns the first successful result.
5. Raises an error only if all targets fail.

This makes failover policies explicit and keeps client integrations stable, since clients continue calling a single smart model ID.

## Target model concept

Each smart model includes one or more targets.

A target contains:

- `model`: the downstream model identifier to call.
- `constraints`: optional constraints to influence routing/governance.
- `system_prompts`: optional prompt injections associated with that target.

With constraints, you can also enforce budget-aware routing. For example, if your deployment includes a cost sensor, constraints can be used to prevent selecting targets that would exceed a spending limit.

## Typical use cases

- Multi-region fallback (for availability and resilience).
- Cross-provider failover under quota or outage conditions.
- Policy-based routing behind a stable external model contract.
- Progressive migration between providers without changing client code.

## Installation

From this workspace:

```bash
uv pip install ./addons/llimona_smart_provider
```

## Notes

- This addon is designed to be used from a Llimona app configuration, together with provider addon loading.
- Keep target ordering intentional: the first target has highest priority.
- Observability is inherited from Llimona contexts and sensors, so routing/fallback paths remain inspectable.

## License

This addon uses the same license as the `llimona` package: GNU AFFERO GENERAL PUBLIC LICENSE. See the repository `LICENSE` file for details.

