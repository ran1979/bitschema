"""BitSchema CLI - Command-line interface for schema validation and code generation.

Usage:
    bitschema generate schema.yaml [--output file.py] [--class-name ClassName]
    bitschema jsonschema schema.yaml [--output file.json] [--indent N]
    bitschema visualize schema.yaml [--format {ascii,markdown}] [--output file.txt]
"""

import argparse
import json
import sys
from pathlib import Path

from bitschema import (
    parse_schema_file,
    compute_bit_layout,
    generate_dataclass_code,
    generate_json_schema,
    visualize_bit_layout,
    ValidationError,
    SchemaError,
    BoolFieldDefinition,
    IntFieldDefinition,
    EnumFieldDefinition,
)


def _schema_fields_to_list(schema):
    """Convert schema.fields dict to list format for compute_bit_layout.

    Args:
        schema: BitSchema with fields dict

    Returns:
        List of field dicts suitable for compute_bit_layout
    """
    fields_list = []
    for name, field_def in schema.fields.items():
        field_dict = {"name": name}
        if isinstance(field_def, BoolFieldDefinition):
            field_dict["type"] = "boolean"
            field_dict["nullable"] = field_def.nullable
        elif isinstance(field_def, IntFieldDefinition):
            field_dict.update({
                "type": "integer",
                "min": field_def.min,
                "max": field_def.max,
                "nullable": field_def.nullable,
            })
        elif isinstance(field_def, EnumFieldDefinition):
            field_dict.update({
                "type": "enum",
                "values": field_def.values,
                "nullable": field_def.nullable,
            })
        fields_list.append(field_dict)
    return fields_list


def cmd_generate(args):
    """Generate Python dataclass code from schema file.

    Args:
        args: Parsed arguments with schema_file, output, class_name
    """
    try:
        # Parse schema file
        schema = parse_schema_file(args.schema_file)

        # Override class name if provided
        if args.class_name:
            schema.name = args.class_name

        # Compute bit layout
        fields_list = _schema_fields_to_list(schema)
        layouts, total_bits = compute_bit_layout(fields_list)

        # Generate dataclass code
        code = generate_dataclass_code(schema, layouts)

        # Write to output or stdout
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(code)
            print(f"Generated dataclass written to: {args.output}", file=sys.stderr)
        else:
            print(code)

    except FileNotFoundError as e:
        print(f"Error: Schema file not found: {args.schema_file}", file=sys.stderr)
        sys.exit(1)
    except (ValidationError, SchemaError) as e:
        print(f"Error: Invalid schema: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_jsonschema(args):
    """Export JSON Schema from BitSchema file.

    Args:
        args: Parsed arguments with schema_file, output, indent
    """
    try:
        # Parse schema file
        schema = parse_schema_file(args.schema_file)

        # Compute bit layout
        fields_list = _schema_fields_to_list(schema)
        layouts, total_bits = compute_bit_layout(fields_list)

        # Generate JSON Schema
        json_schema = generate_json_schema(schema, layouts)

        # Serialize to JSON with specified indent
        json_output = json.dumps(json_schema, indent=args.indent)

        # Write to output or stdout
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(json_output)
            print(f"JSON Schema written to: {args.output}", file=sys.stderr)
        else:
            print(json_output)

    except FileNotFoundError as e:
        print(f"Error: Schema file not found: {args.schema_file}", file=sys.stderr)
        sys.exit(1)
    except (ValidationError, SchemaError) as e:
        print(f"Error: Invalid schema: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_visualize(args):
    """Visualize bit layout as ASCII or markdown table.

    Args:
        args: Parsed arguments with schema_file, format, output
    """
    try:
        # Parse schema file
        schema = parse_schema_file(args.schema_file)

        # Compute bit layout
        fields_list = _schema_fields_to_list(schema)
        layouts, total_bits = compute_bit_layout(fields_list)

        # Generate visualization
        table = visualize_bit_layout(layouts, format=args.format)

        # Write to output or stdout
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(table)
            print(f"Bit layout visualization written to: {args.output}", file=sys.stderr)
        else:
            print(table)

    except FileNotFoundError as e:
        print(f"Error: Schema file not found: {args.schema_file}", file=sys.stderr)
        sys.exit(1)
    except (ValidationError, SchemaError) as e:
        print(f"Error: Invalid schema: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="bitschema",
        description="BitSchema: Bit-level data packing with mathematical correctness",
        epilog="For more information, see documentation.",
    )

    subparsers = parser.add_subparsers(
        title="subcommands",
        description="Available commands",
        help="Use 'bitschema <command> --help' for command-specific help",
        dest="command",
    )

    # Generate subcommand
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate Python dataclass code from schema",
        description="Generate type-safe Python dataclass with encode/decode methods",
    )
    generate_parser.add_argument(
        "schema_file",
        type=str,
        help="Path to BitSchema schema file (JSON or YAML)",
    )
    generate_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    generate_parser.add_argument(
        "--class-name",
        type=str,
        default=None,
        help="Override class name (default: derived from schema)",
    )
    generate_parser.set_defaults(func=cmd_generate)

    # JSON Schema subcommand
    jsonschema_parser = subparsers.add_parser(
        "jsonschema",
        help="Export JSON Schema Draft 2020-12",
        description="Export BitSchema as JSON Schema for interoperability",
    )
    jsonschema_parser.add_argument(
        "schema_file",
        type=str,
        help="Path to BitSchema schema file (JSON or YAML)",
    )
    jsonschema_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    jsonschema_parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation spaces (default: 2)",
    )
    jsonschema_parser.set_defaults(func=cmd_jsonschema)

    # Visualize subcommand
    visualize_parser = subparsers.add_parser(
        "visualize",
        help="Visualize bit layout as table",
        description="Generate ASCII or markdown table showing field bit positions",
    )
    visualize_parser.add_argument(
        "schema_file",
        type=str,
        help="Path to BitSchema schema file (JSON or YAML)",
    )
    visualize_parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["ascii", "markdown"],
        default="ascii",
        help="Output format: ascii (grid table) or markdown (default: ascii)",
    )
    visualize_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    visualize_parser.set_defaults(func=cmd_visualize)

    # Parse arguments and dispatch
    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
