"""
Temporary script to test all global_config values are accessible.
This ensures the pydantic-settings migration is working correctly.
"""

from common.global_config import global_config

print("=" * 80)
print("TESTING GLOBAL_CONFIG - ALL VALUES")
print("=" * 80)

# Top-level fields
print("\n📋 TOP-LEVEL FIELDS:")
print(f"  model_name: {global_config.model_name}")
print(f"  dot_global_config_health_check: {global_config.dot_global_config_health_check}")

# Example parent
print("\n📦 EXAMPLE_PARENT:")
print(f"  example_parent.example_child: {global_config.example_parent.example_child}")

# Default LLM
print("\n🤖 DEFAULT_LLM:")
print(f"  default_llm.default_model: {global_config.default_llm.default_model}")
print(f"  default_llm.default_temperature: {global_config.default_llm.default_temperature}")
print(f"  default_llm.default_max_tokens: {global_config.default_llm.default_max_tokens}")

# LLM Config
print("\n⚙️  LLM_CONFIG:")
print(f"  llm_config.cache_enabled: {global_config.llm_config.cache_enabled}")
print(f"  llm_config.retry.max_attempts: {global_config.llm_config.retry.max_attempts}")
print(f"  llm_config.retry.min_wait_seconds: {global_config.llm_config.retry.min_wait_seconds}")
print(f"  llm_config.retry.max_wait_seconds: {global_config.llm_config.retry.max_wait_seconds}")

# Logging Config
print("\n📝 LOGGING:")
print(f"  logging.verbose: {global_config.logging.verbose}")

print("\n  📐 LOGGING.FORMAT:")
print(f"    logging.format.show_time: {global_config.logging.format.show_time}")
print(f"    logging.format.show_session_id: {global_config.logging.format.show_session_id}")

print("\n    📍 LOGGING.FORMAT.LOCATION:")
print(f"      logging.format.location.enabled: {global_config.logging.format.location.enabled}")
print(f"      logging.format.location.show_file: {global_config.logging.format.location.show_file}")
print(f"      logging.format.location.show_function: {global_config.logging.format.location.show_function}")
print(f"      logging.format.location.show_line: {global_config.logging.format.location.show_line}")
print(f"      logging.format.location.show_for_info: {global_config.logging.format.location.show_for_info}")
print(f"      logging.format.location.show_for_debug: {global_config.logging.format.location.show_for_debug}")
print(f"      logging.format.location.show_for_warning: {global_config.logging.format.location.show_for_warning}")
print(f"      logging.format.location.show_for_error: {global_config.logging.format.location.show_for_error}")

print("\n  🎚️  LOGGING.LEVELS:")
print(f"    logging.levels.debug: {global_config.logging.levels.debug}")
print(f"    logging.levels.info: {global_config.logging.levels.info}")
print(f"    logging.levels.warning: {global_config.logging.levels.warning}")
print(f"    logging.levels.error: {global_config.logging.levels.error}")
print(f"    logging.levels.critical: {global_config.logging.levels.critical}")

# Environment Variables
print("\n🔐 ENVIRONMENT VARIABLES:")
print(f"  DEV_ENV: {global_config.DEV_ENV}")
print(f"  OPENAI_API_KEY: {global_config.OPENAI_API_KEY[:20]}... (truncated)")
print(f"  ANTHROPIC_API_KEY: {global_config.ANTHROPIC_API_KEY[:20]}... (truncated)")
print(f"  GROQ_API_KEY: {global_config.GROQ_API_KEY[:20]}... (truncated)")
print(f"  PERPLEXITY_API_KEY: {global_config.PERPLEXITY_API_KEY[:20]}... (truncated)")
print(f"  GEMINI_API_KEY: {global_config.GEMINI_API_KEY[:20]}... (truncated)")

# Runtime environment
print("\n🏃 RUNTIME ENVIRONMENT:")
print(f"  is_local: {global_config.is_local}")
print(f"  running_on: {global_config.running_on}")

# Test methods
print("\n🧪 TESTING METHODS:")
print(f"  llm_api_key('gpt-4'): {global_config.llm_api_key('gpt-4')[:20]}... (truncated)")
print(f"  llm_api_key('claude-3'): {global_config.llm_api_key('claude-3')[:20]}... (truncated)")
print(f"  llm_api_key('gemini-pro'): {global_config.llm_api_key('gemini-pro')[:20]}... (truncated)")
print(f"  llm_api_key('groq-llama'): {global_config.llm_api_key('groq-llama')[:20]}... (truncated)")
print(f"  llm_api_key('perplexity-sonar'): {global_config.llm_api_key('perplexity-sonar')[:20]}... (truncated)")

print(f"\n  api_base('gpt-4'): {global_config.api_base('gpt-4')}")
print(f"  api_base('groq-llama'): {global_config.api_base('groq-llama')}")
print(f"  api_base('perplexity-sonar'): {global_config.api_base('perplexity-sonar')}")
print(f"  api_base('gemini-pro'): {global_config.api_base('gemini-pro')}")

# Test to_dict
print("\n📄 TESTING to_dict():")
config_dict = global_config.to_dict()
print(f"  Returns dict: {isinstance(config_dict, dict)}")
print(f"  Number of keys: {len(config_dict)}")
print(f"  Top-level keys: {list(config_dict.keys())}")

print("\n" + "=" * 80)
print("✅ ALL CONFIGURATION VALUES ACCESSIBLE - PYDANTIC-SETTINGS MIGRATION SUCCESS!")
print("=" * 80)
