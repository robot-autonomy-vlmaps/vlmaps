# LLM usage and configuration

The LLM integration now centers around a lightweight provider interface so we can swap backends (OpenAI, DeepSeek, local models, etc.) without changing call sites.

## How it works

- Helper entrypoints live in `vlmaps/utils/llm_utils.py` (instruction parsing) and `vlmaps/utils/index_utils.py` (category matching).
- Both call a cached provider instance returned by `vlmaps.llm.factory.get_llm_provider()`.
- Providers must implement the `LLMProvider` interface (`vlmaps/llm/base.py`) with project-specific operations:
  - `parse_instruction(messages) -> str` - Unified method that generates robot code for any navigation instruction (used by both object and spatial goal navigation)
  - `find_similar_category(messages) -> str` - Category matching for map indexing
- Provider selection and per-operation model settings come from `config/llm.yaml`. The active provider is chosen by the top-level `provider` key.
- API keys are read from `VLMAPS_LLM_KEY_<PROVIDER>` (provider uppercased, e.g., `VLMAPS_LLM_KEY_OPENAI`).

## Configuration (`config/llm.yaml`)

- `provider`: active backend to use (e.g., `openai`).
- `<provider>:` block: provider-specific settings.
- For OpenAI:
  - Per-operation settings: `parse_instruction`, `find_similar_category`
    - Each supports `model`, `max_tokens`, `temperature` (passed to `chat.completions.create`)
  - `base_url`, `timeout`
  - `extra`: reserved for provider-specific knobs

Example:

```yaml
provider: openai
openai:
  base_url: null
  timeout: 30
  parse_instruction:
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

1. Implement `LLMProvider` in a new file under `vlmaps/llm/providers/` with the required methods (`parse_instruction` and `find_similar_category`).
2. Register it in `vlmaps/llm/factory.py` by branching on `config.provider` and wiring the correct API key (from `VLMAPS_LLM_KEY_<PROVIDER>`).
3. Add a matching section in `config/llm.yaml` (e.g., `deepseek:`) with models/base_url/operation overrides; set `provider` to that name.

## Testing

- Smoke script: `scripts/test_llm_client.py`
  - `--mode instruction` exercises `parse_instruction`
  - `--mode category` exercises `find_similar_category`
  - `--mode all` runs both (default)
- Requires `config/llm.yaml` and the corresponding `VLMAPS_LLM_KEY_<PROVIDER>` to be set; the provider used is the one in the config.
- The unified `parse_instruction` method is used by evaluation scripts (`evaluate_object_goal_navigation.py` and `evaluate_spatial_goal_navigation.py`).

## Hydra usage notes

- `config/llm.yaml` is loaded directly by `get_llm_provider`, so you usually do not need a Hydra override for LLM settings.
- To switch providers, set `provider` in `config/llm.yaml`, ensure the matching section exists, and export `VLMAPS_LLM_KEY_<PROVIDER>`.

