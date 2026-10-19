"""Replaces v2's hand-rolled schema checker (validate_workspace._schema_instance_errors, the static
validator D20.12 says not to port) with jsonschema Draft 2020-12 from the core venv."""
from jsonschema import Draft202012Validator


def _schema_instance_errors(value, schema, root_schema, location):
    validator = Draft202012Validator(root_schema if schema is root_schema else schema)
    return [f"{location}{''.join(f'/{p}' for p in e.absolute_path)}: {e.message}"
            for e in validator.iter_errors(value)]
