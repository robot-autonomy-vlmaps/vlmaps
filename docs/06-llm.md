# LLM usage and configuration

The LLM integration now centers around a lightweight provider interface so we can swap backends (OpenAI, DeepSeek, local models, etc.) without changing call sites.

## How it works

- Helper entrypoints live in `vlmaps/utils/llm_utils.py` (object/spatial parsing) and `vlmaps/utils/index_utils.py` (category matching).
- Both call a cached provider instance returned by `vlmaps.llm.factory.get_llm_provider()`.
- Providers must implement the `LLMProvider` interface (`vlmaps/llm/base.py`) with three project-specific operations:
  - `parse_object_goal_instruction(messages) -> str`
  - `parse_spatial_instruction(messages) -> str`
  - `find_similar_category(messages) -> str`
- Provider selection and per-operation model settings come from `config/llm.yaml`. The active provider is chosen by the top-level `provider` key.
- API keys are read from `VLMAPS_LLM_KEY_<PROVIDER>` (provider uppercased, e.g., `VLMAPS_LLM_KEY_OPENAI`).

## Configuration (`config/llm.yaml`)

- `provider`: active backend to use (e.g., `openai`).
- `<provider>:` block: provider-specific settings.
- For OpenAI:
  - Per-operation settings: `parse_object_goal_instruction`, `parse_spatial_instruction`, `find_similar_category`
    - Each supports `model`, `max_tokens`, `temperature` (passed to `chat.completions.create`)
  - `base_url`, `timeout`
  - `extra`: reserved for provider-specific knobs

Example:

```yaml
provider: openai
openai:
  base_url: null
  timeout: 30
  parse_object_goal_instruction:
    model: gpt-4-turbo
    max_tokens: 300
    temperature: 0.0
  parse_spatial_instruction:
    model: gpt-4-turbo
    max_tokens: 300
    temperature: 0.2
  find_similar_category:
    model: gpt-4-turbo
    max_tokens: 64
    temperature: 0.0
  extra: {}
```

## Environment

- API key: `VLMAPS_LLM_KEY_<PROVIDER>` must be set (example: `export VLMAPS_LLM_KEY_OPENAI=sk-...`).
- No other env vars are required for the OpenAI implementation; other providers may need their own extras.

## Adding a new provider

1. Implement `LLMProvider` in a new file under `vlmaps/llm/providers/` with the three required methods.
2. Register it in `vlmaps/llm/factory.py` by branching on `config.provider` and wiring the correct API key (from `VLMAPS_LLM_KEY_<PROVIDER>`).
3. Add a matching section in `config/llm.yaml` (e.g., `deepseek:`) with models/base_url/operation overrides; set `provider` to that name.

## Testing

- Smoke script: `scripts/test_llm_client.py`
  - `--mode object` exercises `parse_object_goal_instruction`
  - `--mode spatial` exercises `parse_spatial_instruction`
  - `--mode category` exercises `find_similar_category`
  - `--mode all` runs all three (default)
- Requires `config/llm.yaml` and the corresponding `VLMAPS_LLM_KEY_<PROVIDER>` to be set; the provider used is the one in the config.

## Hydra usage notes

- `config/llm.yaml` is loaded directly by `get_llm_provider`, so you usually do not need a Hydra override for LLM settings.
- To switch providers, set `provider` in `config/llm.yaml`, ensure the matching section exists, and export `VLMAPS_LLM_KEY_<PROVIDER>`.

