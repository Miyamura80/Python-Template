"""
Test pydantic-settings type coercion.
This script verifies that pydantic-settings automatically converts values to the correct type.
"""

import os
import sys

print("=" * 80)
print("TESTING PYDANTIC-SETTINGS TYPE COERCION")
print("=" * 80)

# Set environment variables with intentionally "wrong" types (but coercible)
# These should all be automatically converted to the correct types by pydantic-settings

print("\n📝 Setting environment variables with 'wrong' types:")
print("   (pydantic-settings should automatically coerce them)")

# Test 1: Integer field with string value
os.environ['DEFAULT_LLM__DEFAULT_MAX_TOKENS'] = "50000"  # String instead of int
print("✓ DEFAULT_LLM__DEFAULT_MAX_TOKENS = '50000' (string, should become int)")

# Test 2: Float field with string value
os.environ['DEFAULT_LLM__DEFAULT_TEMPERATURE'] = "0.7"  # String instead of float
print("✓ DEFAULT_LLM__DEFAULT_TEMPERATURE = '0.7' (string, should become float)")

# Test 3: Integer field with string value
os.environ['LLM_CONFIG__RETRY__MAX_ATTEMPTS'] = "5"  # String instead of int
print("✓ LLM_CONFIG__RETRY__MAX_ATTEMPTS = '5' (string, should become int)")

# Test 4: Integer field with string value
os.environ['LLM_CONFIG__RETRY__MIN_WAIT_SECONDS'] = "2"  # String instead of int
print("✓ LLM_CONFIG__RETRY__MIN_WAIT_SECONDS = '2' (string, should become int)")

# Test 5: Integer field with string value
os.environ['LLM_CONFIG__RETRY__MAX_WAIT_SECONDS'] = "10"  # String instead of int
print("✓ LLM_CONFIG__RETRY__MAX_WAIT_SECONDS = '10' (string, should become int)")

# Test 6: Boolean field with string value
os.environ['LLM_CONFIG__CACHE_ENABLED'] = "true"  # String instead of bool
print("✓ LLM_CONFIG__CACHE_ENABLED = 'true' (string, should become bool)")

# Test 7: Boolean field with string value
os.environ['LOGGING__VERBOSE'] = "false"  # String instead of bool
print("✓ LOGGING__VERBOSE = 'false' (string, should become bool)")

# Test 8: Boolean field with string value
os.environ['LOGGING__FORMAT__SHOW_TIME'] = "1"  # Number string instead of bool
print("✓ LOGGING__FORMAT__SHOW_TIME = '1' (string '1', should become bool True)")

# Test 9: Boolean field with string value
os.environ['LOGGING__LEVELS__DEBUG'] = "true"  # String instead of bool
print("✓ LOGGING__LEVELS__DEBUG = 'true' (string, should become bool)")

# Test 10: Boolean field with string value
os.environ['LOGGING__LEVELS__INFO'] = "0"  # Number string instead of bool
print("✓ LOGGING__LEVELS__INFO = '0' (string '0', should become bool False)")

# Force reload of the config module to pick up new env vars
if 'common.global_config' in sys.modules:
    del sys.modules['common.global_config']
if 'common.config_models' in sys.modules:
    del sys.modules['common.config_models']

print("\n🔄 Loading configuration with pydantic-settings...")

from common.global_config import Config
test_config = Config()

print("\n✅ VERIFYING TYPE COERCION:\n")

# Verify each value was coerced to the correct type
tests_passed = 0
tests_failed = 0

# Test 1: Check int coercion
value = test_config.default_llm.default_max_tokens
expected_type = int
expected_value = 50000
if isinstance(value, expected_type) and value == expected_value:
    print(f"✅ Test 1: default_max_tokens = {value} (type: {type(value).__name__})")
    tests_passed += 1
else:
    print(f"❌ Test 1 FAILED: Expected {expected_type.__name__} {expected_value}, got {type(value).__name__} {value}")
    tests_failed += 1

# Test 2: Check float coercion
value = test_config.default_llm.default_temperature
expected_type = float
expected_value = 0.7
if isinstance(value, expected_type) and value == expected_value:
    print(f"✅ Test 2: default_temperature = {value} (type: {type(value).__name__})")
    tests_passed += 1
else:
    print(f"❌ Test 2 FAILED: Expected {expected_type.__name__} {expected_value}, got {type(value).__name__} {value}")
    tests_failed += 1

# Test 3: Check int coercion
value = test_config.llm_config.retry.max_attempts
expected_type = int
expected_value = 5
if isinstance(value, expected_type) and value == expected_value:
    print(f"✅ Test 3: retry.max_attempts = {value} (type: {type(value).__name__})")
    tests_passed += 1
else:
    print(f"❌ Test 3 FAILED: Expected {expected_type.__name__} {expected_value}, got {type(value).__name__} {value}")
    tests_failed += 1

# Test 4: Check int coercion
value = test_config.llm_config.retry.min_wait_seconds
expected_type = int
expected_value = 2
if isinstance(value, expected_type) and value == expected_value:
    print(f"✅ Test 4: retry.min_wait_seconds = {value} (type: {type(value).__name__})")
    tests_passed += 1
else:
    print(f"❌ Test 4 FAILED: Expected {expected_type.__name__} {expected_value}, got {type(value).__name__} {value}")
    tests_failed += 1

# Test 5: Check int coercion
value = test_config.llm_config.retry.max_wait_seconds
expected_type = int
expected_value = 10
if isinstance(value, expected_type) and value == expected_value:
    print(f"✅ Test 5: retry.max_wait_seconds = {value} (type: {type(value).__name__})")
    tests_passed += 1
else:
    print(f"❌ Test 5 FAILED: Expected {expected_type.__name__} {expected_value}, got {type(value).__name__} {value}")
    tests_failed += 1

# Test 6: Check bool coercion
value = test_config.llm_config.cache_enabled
expected_type = bool
expected_value = True
if isinstance(value, expected_type) and value == expected_value:
    print(f"✅ Test 6: cache_enabled = {value} (type: {type(value).__name__})")
    tests_passed += 1
else:
    print(f"❌ Test 6 FAILED: Expected {expected_type.__name__} {expected_value}, got {type(value).__name__} {value}")
    tests_failed += 1

# Test 7: Check bool coercion
value = test_config.logging.verbose
expected_type = bool
expected_value = False
if isinstance(value, expected_type) and value == expected_value:
    print(f"✅ Test 7: logging.verbose = {value} (type: {type(value).__name__})")
    tests_passed += 1
else:
    print(f"❌ Test 7 FAILED: Expected {expected_type.__name__} {expected_value}, got {type(value).__name__} {value}")
    tests_failed += 1

# Test 8: Check bool coercion from "1"
value = test_config.logging.format.show_time
expected_type = bool
expected_value = True
if isinstance(value, expected_type) and value == expected_value:
    print(f"✅ Test 8: format.show_time = {value} (type: {type(value).__name__})")
    tests_passed += 1
else:
    print(f"❌ Test 8 FAILED: Expected {expected_type.__name__} {expected_value}, got {type(value).__name__} {value}")
    tests_failed += 1

# Test 9: Check bool coercion
value = test_config.logging.levels.debug
expected_type = bool
expected_value = True
if isinstance(value, expected_type) and value == expected_value:
    print(f"✅ Test 9: levels.debug = {value} (type: {type(value).__name__})")
    tests_passed += 1
else:
    print(f"❌ Test 9 FAILED: Expected {expected_type.__name__} {expected_value}, got {type(value).__name__} {value}")
    tests_failed += 1

# Test 10: Check bool coercion from "0"
value = test_config.logging.levels.info
expected_type = bool
expected_value = False
if isinstance(value, expected_type) and value == expected_value:
    print(f"✅ Test 10: levels.info = {value} (type: {type(value).__name__})")
    tests_passed += 1
else:
    print(f"❌ Test 10 FAILED: Expected {expected_type.__name__} {expected_value}, got {type(value).__name__} {value}")
    tests_failed += 1

print("\n" + "=" * 80)
print(f"TEST RESULTS: {tests_passed}/10 passed, {tests_failed}/10 failed")
if tests_failed == 0:
    print("✅ ALL TESTS PASSED - PYDANTIC-SETTINGS TYPE COERCION WORKS PERFECTLY!")
else:
    print("❌ SOME TESTS FAILED - CHECK PYDANTIC-SETTINGS CONFIGURATION")
print("=" * 80)

# Exit with error code if tests failed
sys.exit(0 if tests_failed == 0 else 1)
