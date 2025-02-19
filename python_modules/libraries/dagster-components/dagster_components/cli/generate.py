import sys
from pathlib import Path
from typing import Optional

import click
from pydantic import TypeAdapter

from dagster_components import ComponentTypeRegistry
from dagster_components.core.deployment import (
    CodeLocationProjectContext,
    find_enclosing_code_location_root_path,
    is_inside_code_location_project,
)
from dagster_components.generate import (
    ComponentGeneratorUnavailableReason,
    generate_component_instance,
)
from dagster_components.utils import CLI_BUILTIN_COMPONENT_LIB_KEY


@click.group(name="generate")
def generate_cli() -> None:
    """Commands for generating Dagster components and related entities."""


@generate_cli.command(name="component")
@click.argument("component_type", type=str)
@click.argument("component_name", type=str)
@click.option("--json-params", type=str, default=None)
@click.pass_context
def generate_component_command(
    ctx: click.Context,
    component_type: str,
    component_name: str,
    json_params: Optional[str],
) -> None:
    builtin_component_lib = ctx.obj.get(CLI_BUILTIN_COMPONENT_LIB_KEY, False)
    if not is_inside_code_location_project(Path.cwd()):
        click.echo(
            click.style(
                "This command must be run inside a Dagster code location project.", fg="red"
            )
        )
        sys.exit(1)

    context = CodeLocationProjectContext.from_code_location_path(
        find_enclosing_code_location_root_path(Path.cwd()),
        ComponentTypeRegistry.from_entry_point_discovery(
            builtin_component_lib=builtin_component_lib
        ),
    )
    if not context.has_component_type(component_type):
        click.echo(
            click.style(f"No component type `{component_type}` could be resolved.", fg="red")
        )
        sys.exit(1)

    component_type_cls = context.get_component_type(component_type)
    if json_params:
        generator = component_type_cls.get_generator()
        if isinstance(generator, ComponentGeneratorUnavailableReason):
            raise Exception(
                f"Component type {component_type} does not have a generator. Reason: {generator.message}."
            )
        generate_params = TypeAdapter(generator.generator_params).validate_json(json_params)
    else:
        generate_params = {}

    generate_component_instance(
        context.component_instances_root_path,
        component_name,
        component_type_cls,
        component_type,
        generate_params,
    )
