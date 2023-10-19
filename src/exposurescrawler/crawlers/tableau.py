import itertools
import logging
import os
from typing import Collection, List
from unicodedata import name
import pathlib


from exposurescrawler.tableau.models import WorkbookReference, WorkbookModelsMapping
from exposurescrawler.tableau.rest_client import TableauRestClient
from exposurescrawler.utils.logger import logger

import click
import tableauserverclient as TSC
from functools import lru_cache

from exposurescrawler.dbt.exposure import DbtExposure
from exposurescrawler.dbt.manifest import DbtManifest
from manifest import DbtManifest
from graphql_client import (
    retrieve_custom_sql,
    retrieve_native_sql
)
from exposurescrawler.tableau.models import WorkbookModelsMapping
from rest_client import TableauRestClient
from exposurescrawler.utils.logger import logger
from query_parsing import search_model_in_query

def _should_ignore_workbook(workbook, projects_to_ignore: Collection[str]) -> bool:
    #print("nothing to ignore")
    try:
        return workbook.project_name in projects_to_ignore
    except:
        print("An exception occurred")



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
            #print(custom_sql)
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

    tableau_token = os.environ['TABLEAU_TOKEN']
    tableau_server_url = os.environ['TABLEAU_URL']
    
    tableau_auth = TSC.PersonalAccessTokenAuth(token_name='crawler', personal_access_token=tableau_token, site_id='loom')
    server = TSC.Server(tableau_server_url, use_server_version=True)
    tableau_client = server.auth.sign_in(tableau_auth)
    with server.auth.sign_in(tableau_auth):
    # Now you have a signed-in server object (server) that you can use for making API calls
    # For example: workbooks, views, projects, etc.
        print('Signed in successfully!')
    #print(models)

    # Configure the Tableau REST client
    #tableau_client = TableauRestClient()

    # Retrieve custom SQLs and find model references
    workbooks_custom_sqls = retrieve_custom_sql(tableau_auth,server , 'snowflake')
    workbooks_custom_sql_models = _parse_tables_from_sql(workbooks_custom_sqls, models)

    # Retrieve native SQLs and find model references
    workbooks_native_sqls = retrieve_native_sql(tableau_auth,server , 'snowflake')
    workbooks_native_sql_models = _parse_tables_from_sql(workbooks_native_sqls, models)

    # Merge the results by chaining the iterables
    # Here it is fine to have duplicates on the list
    # Duplicates will be handled in the DbtExposure class
    workbooks_models: WorkbookModelsMapping = {}

    for workbook_reference, found in itertools.chain(
        workbooks_custom_sql_models.items(),
        workbooks_native_sql_models.items()
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
    def retrieve_workbook(tableau_auth, server, workbook_id: str):
        with server.auth.sign_in(tableau_auth):
            workbook = server.workbooks.get_by_id(workbook_id)

        return workbook

    def retrieve_user(tableau_auth, server, user_id: str):
        with server.auth.sign_in(tableau_auth):
            user = server.users.get_by_id(user_id)

        return user


    for workbook_reference, found in workbooks_models.items():
        workbook = retrieve_workbook(tableau_auth, server,workbook_reference.id)
        owner = retrieve_user(tableau_auth, server,workbook.owner_id)

        if _should_ignore_workbook(workbook, tableau_projects_to_ignore):
            logger().debug(
                f'⏩ Skipping workbook: {workbook.name} ({workbook.project_name} is ignored)'
            )
            continue

        exposure = DbtExposure.from_tableau_workbook(dbt_package_name, workbook, owner, found)
        #print(exposure)

        #import json
        #test_raw = exposure.to_dict()
        #test_name = test_raw.get("name")
        #new_name = test_name.rsplit("_",1)[0]
        #print(new_name)
        #file_name = '/Users/sandhya.yadav/Desktop/dbt/dbt2/loom-dbt/target/' + new_name + '.txt'
        #print(file_name)
        #f = open(file_name, "a")
        #f.write(str(exposure.to_dict()))
        #f.write('\n')
        #f.close()
        manifest.add_exposure(exposure, found)

    # Terminate the Tableau client

    # Persist the modified manifest
    logger().info('')
    logger().info(f'💾 Writing results to file: {manifest_path}')
    manifest.save(manifest_path)
    #manifest.save('/Users/sandhya.yadav/Desktop/dbt/loom-dbt/target/sandhya_log.txt')

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