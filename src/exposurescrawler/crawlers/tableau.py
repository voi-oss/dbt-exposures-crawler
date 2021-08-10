import itertools
import logging
import os
from typing import Collection, List

import click

from exposurescrawler.dbt.exposure import DbtExposure
from exposurescrawler.dbt.manifest import DbtManifest
from exposurescrawler.tableau.graphql_client import (
    retrieve_custom_sql,
    retrieve_native_sql,
)
from exposurescrawler.tableau.models import WorkbookModelsMapping
from exposurescrawler.tableau.rest_client import TableauRestClient
from exposurescrawler.utils.logger import logger
from exposurescrawler.utils.query_parsing import search_model_in_query


def _should_ignore_workbook(workbook, projects_to_ignore: Collection[str]) -> bool:
    return workbook.project_name in projects_to_ignore


def _parse_tables_from_sql(workbooks_sqls: WorkbookModelsMapping, models) -> WorkbookModelsMapping:
    """
    Receives a map of workbook (references) and their respective SQLs (list), and look
    for occurrences of `models` in the SQLs.

    :param workbooks_sqls: map of workbook (references) to SQLs
    :param models: the node dict coming from the manifest.json

    :return: another map, but instead of workbooks to SQLs, it
             has workbooks to models
    """
    logger().info('⚙️ Parsing SQL: looking for references to models')

    output: WorkbookModelsMapping = {}

    for workbook_reference, custom_sqls in workbooks_sqls.items():
        # a list of dbt model represented as their original dicts from the manifest
        all_found: List[dict] = []

        for custom_sql in custom_sqls:
            if models_found_query := search_model_in_query(custom_sql, models):
                all_found.extend(models_found_query.values())

        if all_found:
            logger().debug(
                ' ✅ {}: found models {}'.format(
                    workbook_reference.name,
                    [model['materialized_name'] for model in all_found],
                )
            )

            output[workbook_reference] = all_found
        else:
            logger().debug(f' ❌ {workbook_reference.name}: found no models')

    logger().info(f'⚙️ Found {len(output.keys())} workbooks with linked models')
    return output


def tableau_crawler(
    manifest_path: str,
    dbt_package_name: str,
    tableau_projects_to_ignore: Collection[str],
    verbose: bool,
) -> None:
    # Enable verbose logging
    if verbose:
        logger().setLevel(logging.DEBUG)

    # Parse arguments
    manifest_path = os.path.expandvars(manifest_path)
    manifest_path = os.path.expanduser(manifest_path)

    # Parse the dbt manifest JSON file
    manifest: DbtManifest = DbtManifest.from_file(manifest_path)

    # Retrieve all models
    models = manifest.retrieve_models_and_sources()

    # Configure the Tableau REST client
    tableau_client = TableauRestClient(
        os.environ['TABLEAU_URL'],
        os.environ['TABLEAU_USERNAME'],
        os.environ['TABLEAU_PASSWORD'],
    )

    # Retrieve custom SQLs and find model references
    workbooks_custom_sqls = retrieve_custom_sql(tableau_client, 'snowflake')
    workbooks_custom_sql_models = _parse_tables_from_sql(workbooks_custom_sqls, models)

    # Retrieve native SQLs and find model references
    workbooks_native_sqls = retrieve_native_sql(tableau_client, 'snowflake')
    workbooks_native_sql_models = _parse_tables_from_sql(workbooks_native_sqls, models)

    # Merge the results by chaining the iterables
    # Here it is fine to have duplicates on the list
    # Duplicates will be handled in the DbtExposure class
    workbooks_models: WorkbookModelsMapping = {}

    for workbook_reference, found in itertools.chain(
        workbooks_custom_sql_models.items(), workbooks_native_sql_models.items()
    ):
        workbooks_models.setdefault(workbook_reference, []).extend(found)

    logger().info('')
    logger().info(
        '💡 Results merged: {} + {} = {} workbooks'.format(
            len(workbooks_custom_sql_models),
            len(workbooks_native_sql_models),
            len(workbooks_models),
        )
    )

    logger().info('')
    logger().info('🌏 Retrieving workbooks and authors metadata from the Tableau REST API')

    # For every workbook and the models found, create exposures and add
    # to the manifest (in-memory)
    for workbook_reference, found in workbooks_models.items():
        workbook = tableau_client.retrieve_workbook(workbook_reference.id)
        owner = tableau_client.retrieve_user(workbook.owner_id)

        if _should_ignore_workbook(workbook, tableau_projects_to_ignore):
            logger().debug(
                f'⏩ Skipping workbook: {workbook.name} ({workbook.project_name} is ignored)'
            )
            continue

        exposure = DbtExposure.from_tableau_workbook(dbt_package_name, workbook, owner, found)
        manifest.add_exposure(exposure, found)

    # Terminate the Tableau client
    tableau_client.sign_out()

    # Persist the modified manifest
    logger().info('')
    logger().info(f'💾 Writing results to file: {manifest_path}')
    manifest.save(manifest_path)


@click.command()
@click.option(
    '--manifest-path',
    required=True,
    metavar='PATH',
    help='The path to the dbt manifest artifact',
)
@click.option(
    '--dbt-package-name',
    required=True,
    metavar='PROJECT_NAME',
    help='The name of the dbt pacakge where the exposures should be added. If in doubt, check the '
    'name of your dbt project on dbt_project.yml',
)
@click.option(
    '--tableau-ignore-projects',
    'tableau_projects_to_ignore',
    default=[],
    help='The name of Tableau projects (folders) to ignore',
)
@click.option('-v', '--verbose', is_flag=True, default=False, help='Enable verbose logging')
def tableau_crawler_command(
    manifest_path: str,
    dbt_package_name: str,
    tableau_projects_to_ignore: Collection[str],
    verbose: bool,
):
    tableau_crawler(manifest_path, dbt_package_name, tableau_projects_to_ignore, verbose)


if __name__ == '__main__':
    tableau_crawler_command()
