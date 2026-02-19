"""CLI integration tests using subprocess."""

import ast
import json
import subprocess
from pathlib import Path

import pytest


def run_cli(*args):
    """Helper to run bitschema CLI and capture output.

    Args:
        *args: Command line arguments to pass to bitschema

    Returns:
        subprocess.CompletedProcess with returncode, stdout, stderr
    """
    result = subprocess.run(
        ["python", "-m", "bitschema", *args],
        capture_output=True,
        text=True,
    )
    return result


class TestGenerateCommand:
    """Tests for 'bitschema generate' command."""

    def test_generate_to_stdout(self):
        """Test generating dataclass code to stdout."""
        result = run_cli("generate", "tests/fixtures/valid_schema.yaml")

        assert result.returncode == 0
        assert "class UserFlags:" in result.stdout
        assert "def encode(self) -> int:" in result.stdout
        assert "def decode(cls, encoded: int)" in result.stdout
        assert "@dataclass" in result.stdout

        # Verify generated code is valid Python
        ast.parse(result.stdout)

    def test_generate_to_file(self, tmp_path):
        """Test generating dataclass code to file."""
        output_file = tmp_path / "output.py"
        result = run_cli(
            "generate",
            "tests/fixtures/valid_schema.yaml",
            "--output",
            str(output_file),
        )

        assert result.returncode == 0
        assert output_file.exists()

        # Verify file contains expected content
        code = output_file.read_text()
        assert "class UserFlags:" in code
        assert "def encode(self) -> int:" in code
        assert "def decode(cls, encoded: int)" in code

        # Verify generated code is valid Python
        ast.parse(code)

        # Verify stderr message
        assert f"Generated dataclass written to: {output_file}" in result.stderr

    def test_generate_with_custom_class_name(self, tmp_path):
        """Test generating with custom class name."""
        output_file = tmp_path / "custom.py"
        result = run_cli(
            "generate",
            "tests/fixtures/valid_schema.yaml",
            "--output",
            str(output_file),
            "--class-name",
            "CustomPerson",
        )

        assert result.returncode == 0
        code = output_file.read_text()
        assert "class CustomPerson:" in code
        assert "class UserFlags:" not in code

    def test_generate_nonexistent_file(self):
        """Test error handling for nonexistent schema file."""
        result = run_cli("generate", "nonexistent.yaml")

        assert result.returncode == 1
        assert "Error: Schema file not found: nonexistent.yaml" in result.stderr

    def test_generate_with_short_output_flag(self, tmp_path):
        """Test -o shorthand for --output."""
        output_file = tmp_path / "short.py"
        result = run_cli(
            "generate",
            "tests/fixtures/valid_schema.yaml",
            "-o",
            str(output_file),
        )

        assert result.returncode == 0
        assert output_file.exists()


class TestJsonSchemaCommand:
    """Tests for 'bitschema jsonschema' command."""

    def test_jsonschema_to_stdout(self):
        """Test exporting JSON Schema to stdout."""
        result = run_cli("jsonschema", "tests/fixtures/valid_schema.yaml")

        assert result.returncode == 0

        # Verify output is valid JSON
        json_output = json.loads(result.stdout)

        # Verify JSON Schema structure
        assert json_output["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert json_output["type"] == "object"
        assert "properties" in json_output
        assert "required" in json_output

    def test_jsonschema_with_indent(self):
        """Test JSON Schema with custom indent."""
        result_2 = run_cli("jsonschema", "tests/fixtures/valid_schema.yaml", "--indent", "2")
        result_4 = run_cli("jsonschema", "tests/fixtures/valid_schema.yaml", "--indent", "4")

        assert result_2.returncode == 0
        assert result_4.returncode == 0

        # Verify different indentation (4-space should be longer)
        assert len(result_4.stdout) > len(result_2.stdout)

    def test_jsonschema_to_file(self, tmp_path):
        """Test exporting JSON Schema to file."""
        output_file = tmp_path / "schema.json"
        result = run_cli(
            "jsonschema",
            "tests/fixtures/valid_schema.yaml",
            "--output",
            str(output_file),
        )

        assert result.returncode == 0
        assert output_file.exists()

        # Verify file contains valid JSON Schema
        json_data = json.loads(output_file.read_text())
        assert json_data["$schema"] == "https://json-schema.org/draft/2020-12/schema"

        # Verify stderr message
        assert f"JSON Schema written to: {output_file}" in result.stderr

    def test_jsonschema_with_short_output_flag(self, tmp_path):
        """Test -o shorthand for --output."""
        output_file = tmp_path / "schema.json"
        result = run_cli(
            "jsonschema",
            "tests/fixtures/valid_schema.yaml",
            "-o",
            str(output_file),
        )

        assert result.returncode == 0
        assert output_file.exists()

    def test_jsonschema_contains_bitschema_metadata(self):
        """Test JSON Schema contains BitSchema-specific metadata."""
        result = run_cli("jsonschema", "tests/fixtures/valid_schema.yaml")

        json_output = json.loads(result.stdout)
        assert "x-bitschema-version" in json_output
        assert "x-bitschema-total-bits" in json_output


class TestVisualizeCommand:
    """Tests for 'bitschema visualize' command."""

    def test_visualize_ascii_default(self):
        """Test visualizing bit layout as ASCII grid (default)."""
        result = run_cli("visualize", "tests/fixtures/valid_schema.yaml")

        assert result.returncode == 0
        # Verify ASCII grid table format (has borders)
        assert "+" in result.stdout
        assert "|" in result.stdout
        # Verify column headers
        assert "Field" in result.stdout
        assert "Type" in result.stdout
        assert "Bits" in result.stdout
        assert "Constraints" in result.stdout

    def test_visualize_markdown(self):
        """Test visualizing bit layout as markdown table."""
        result = run_cli(
            "visualize",
            "tests/fixtures/valid_schema.yaml",
            "--format",
            "markdown",
        )

        assert result.returncode == 0
        # Verify markdown table format (has separator line with dashes)
        assert "|" in result.stdout
        assert "---" in result.stdout
        # Verify column headers
        assert "Field" in result.stdout
        assert "Type" in result.stdout

    def test_visualize_to_file(self, tmp_path):
        """Test visualizing bit layout to file."""
        output_file = tmp_path / "layout.txt"
        result = run_cli(
            "visualize",
            "tests/fixtures/valid_schema.yaml",
            "--output",
            str(output_file),
        )

        assert result.returncode == 0
        assert output_file.exists()

        # Verify file contains table
        content = output_file.read_text()
        assert "Field" in content
        assert "Type" in content

        # Verify stderr message
        assert f"Bit layout visualization written to: {output_file}" in result.stderr

    def test_visualize_with_short_format_flag(self):
        """Test -f shorthand for --format."""
        result = run_cli(
            "visualize",
            "tests/fixtures/valid_schema.yaml",
            "-f",
            "markdown",
        )

        assert result.returncode == 0
        assert "---" in result.stdout

    def test_visualize_with_short_output_flag(self, tmp_path):
        """Test -o shorthand for --output."""
        output_file = tmp_path / "layout.txt"
        result = run_cli(
            "visualize",
            "tests/fixtures/valid_schema.yaml",
            "-o",
            str(output_file),
        )

        assert result.returncode == 0
        assert output_file.exists()


class TestCLIErrors:
    """Tests for CLI error handling."""

    def test_no_subcommand_shows_help(self):
        """Test that running 'bitschema' with no args shows help."""
        result = run_cli()

        # Should exit cleanly and show help
        assert result.returncode == 0
        assert "usage: bitschema" in result.stdout
        assert "subcommands" in result.stdout.lower()

    def test_invalid_schema_shows_error(self, tmp_path):
        """Test error handling for invalid schema."""
        # Create invalid schema with total bits > 64
        invalid_schema = tmp_path / "invalid.yaml"
        invalid_schema.write_text("""
version: "1"
name: "TooManyBits"
fields:
  - name: field1
    type: integer
    min: 0
    max: 18446744073709551615  # Requires 64 bits
  - name: field2
    type: boolean  # +1 bit = 65 total
""")

        result = run_cli("generate", str(invalid_schema))

        assert result.returncode == 1
        assert "Error: Invalid schema" in result.stderr

    def test_generate_help(self):
        """Test 'bitschema generate --help' shows help."""
        result = run_cli("generate", "--help")

        assert result.returncode == 0
        assert "Generate type-safe Python dataclass with encode/decode methods" in result.stdout
        assert "schema_file" in result.stdout

    def test_jsonschema_help(self):
        """Test 'bitschema jsonschema --help' shows help."""
        result = run_cli("jsonschema", "--help")

        assert result.returncode == 0
        assert "Export BitSchema as JSON Schema for interoperability" in result.stdout

    def test_visualize_help(self):
        """Test 'bitschema visualize --help' shows help."""
        result = run_cli("visualize", "--help")

        assert result.returncode == 0
        assert "Generate ASCII or markdown table showing field bit positions" in result.stdout

    def test_invalid_format_for_visualize(self):
        """Test error for invalid format in visualize command."""
        result = run_cli(
            "visualize",
            "tests/fixtures/valid_schema.yaml",
            "--format",
            "invalid",
        )

        # argparse should reject invalid choice
        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower()


class TestCLIIntegration:
    """Integration tests across multiple CLI commands."""

    def test_generate_and_execute_generated_code(self, tmp_path):
        """Test that generated code can be executed without errors."""
        output_file = tmp_path / "generated.py"
        result = run_cli(
            "generate",
            "tests/fixtures/valid_schema.yaml",
            "--output",
            str(output_file),
        )

        assert result.returncode == 0

        # Try to execute the generated file (should not error on imports)
        exec_result = subprocess.run(
            ["python", "-c", f"import sys; sys.path.insert(0, '{tmp_path}'); import generated"],
            capture_output=True,
            text=True,
        )

        # Should not error (module should import successfully)
        assert exec_result.returncode == 0

    def test_all_commands_work_with_json_schema(self, tmp_path):
        """Test all commands work with JSON schema file (not just YAML)."""
        # Test generate
        result_gen = run_cli("generate", "tests/fixtures/valid_schema.json")
        assert result_gen.returncode == 0
        assert "class UserFlags:" in result_gen.stdout

        # Test jsonschema
        result_json = run_cli("jsonschema", "tests/fixtures/valid_schema.json")
        assert result_json.returncode == 0
        json.loads(result_json.stdout)  # Verify valid JSON

        # Test visualize
        result_viz = run_cli("visualize", "tests/fixtures/valid_schema.json")
        assert result_viz.returncode == 0
        assert "Field" in result_viz.stdout

    def test_consistent_output_across_commands(self):
        """Test that different commands produce consistent field information."""
        # Generate dataclass
        result_gen = run_cli("generate", "tests/fixtures/valid_schema.yaml")
        # Export JSON Schema
        result_json = run_cli("jsonschema", "tests/fixtures/valid_schema.yaml")
        # Visualize
        result_viz = run_cli("visualize", "tests/fixtures/valid_schema.yaml")

        # All should succeed
        assert result_gen.returncode == 0
        assert result_json.returncode == 0
        assert result_viz.returncode == 0

        # All should mention the same fields
        assert "active" in result_gen.stdout
        assert "active" in result_json.stdout
        assert "active" in result_viz.stdout

        assert "age" in result_gen.stdout
        assert "age" in result_json.stdout
        assert "age" in result_viz.stdout

        assert "status" in result_gen.stdout
        assert "status" in result_json.stdout
        assert "status" in result_viz.stdout
