import pathlib

from exposurescrawler.tableau.models import WorkbookReference, WorkbookModelsMapping
from exposurescrawler.tableau.rest_client import TableauRestClient
from exposurescrawler.utils.logger import logger

"""
For the database connections without custom SQL, the Tableau Metadata API returns
already which tables are referenced, but we need to clean and normalize the results
a bit. This is done on the `retrieve_native_sql()` function.

However, for custom SQL, the first problem is that the Tableau Metadata API requires
a different call on the API. I wrote about it on one of Tableau forums. After doing
this other call, then we have access to the raw custom SQL. I think Tableau also
tries to parse which tables  the query is using but I remember reading on their docs
or forums  that this is not that reliable.

Link to my message on their forum: https://community.tableau.com/s/idea/0874T000000HFDxQAO/detail
"""

CURRENT_FOLDER = pathlib.Path(__file__).parent.resolve()
GRAPHQL_CUSTOM_SQL_QUERY_FILE = '_custom_sql_graphql_query.txt'
GRAPHQL_NATIVE_SQL_QUERY_FILE = '_native_sql_graphql_query.txt'


def retrieve_custom_sql(
    tableau_client: TableauRestClient, only_connection_type: str = None
) -> WorkbookModelsMapping:
    """
    Starts at CustomSQLTables and trace them back to workbooks.

    :return:
    """
    results = _fetch_custom_sql(tableau_client)

    logger().info('🔍 Parsing GraphQL result: looking for custom SQL tables')

    workbooks_custom_sqls: WorkbookModelsMapping = {}

    for custom_sql_table in results['customSQLTablesConnection']['nodes']:
        if (
            only_connection_type
            and custom_sql_table['database']['connectionType'] != only_connection_type
        ):
            # logger().debug('- Ignoring {} connectionType for workbook'.format(
            #    custom_sql_table['database']['connectionType']))
            continue

        for downstream_workbook in custom_sql_table['downstreamWorkbooks']:
            workbook = WorkbookReference(downstream_workbook['luid'], downstream_workbook['name'])

            logger().debug(f' ➕ {workbook.name} | adding custom SQL')
            workbooks_custom_sqls.setdefault(workbook, []).append(custom_sql_table['query'])

    logger().info(f'🔍 Found {len(workbooks_custom_sqls.keys())} workbooks with custom SQL')

    return workbooks_custom_sqls


def _fetch_custom_sql(tableau_client):
    query_custom_sql = (CURRENT_FOLDER / GRAPHQL_CUSTOM_SQL_QUERY_FILE).read_text()
    return tableau_client.run_metadata_api(query_custom_sql)


def retrieve_native_sql(
    tableau_client: TableauRestClient, connection_type: str
) -> WorkbookModelsMapping:
    """
    When starting by workbooks -> embeddedDatasources -> upstreamTables, only DatabaseTables are
    included, and not CustomSQLTables. We will need 2 queries.

    1. Starts at workbooks and finds all non-custom SQL tables (this one);
    2. Another query just for Custom SQL (the one above)

    In the results, sometimes fullname has the full name, but other times only the schema and
    table name. If that's the case, we use the name of the database to complete the fullname.

    :return:
    """
    results = _fetch_native_sql(tableau_client, connection_type)

    logger().info('')
    logger().info('🔍 Parsing GraphQL result: looking for native SQL tables')

    workbooks_native_sqls: WorkbookModelsMapping = {}

    for native_sql_table in results['workbooksConnection']['nodes']:
        workbook = WorkbookReference(native_sql_table['luid'], native_sql_table['name'])

        connection_types = []

        for embedded_data_source in native_sql_table['embeddedDatasources']:
            for table in embedded_data_source['upstreamTables']:
                connection_types.append(table['connectionType'])

        if connection_type not in connection_types:
            # logger().debug(' {} has no *native* Snowflake table'.format(workbook.name))
            continue

        for embedded_data_source in native_sql_table['embeddedDatasources']:
            for table in embedded_data_source['upstreamTables']:
                fqn = _fix_fqn_native_sql(table)

                logger().debug(f' ➕ {workbook.name} | adding native SQL: {fqn}')
                workbooks_native_sqls.setdefault(workbook, []).append(fqn)

    logger().info(f'🔍 Found {len(workbooks_native_sqls.keys())} workbooks with native SQL')

    return workbooks_native_sqls


def _fetch_native_sql(tableau_client, connection_type):
    query_native_sql = (CURRENT_FOLDER / GRAPHQL_NATIVE_SQL_QUERY_FILE).read_text()
    query_native_sql = query_native_sql % {'connection_type': connection_type}

    return tableau_client.run_metadata_api(query_native_sql)


def _fix_fqn_native_sql(table):
    # I don't understand why, but sometimes it comes on the format of [DATABASE].[SCHEMA].[NAME]
    full_name = table['fullName'].replace('[', '').replace(']', '')

    periods = full_name.count('.')

    # Already good
    if periods == 2:
        return full_name

    # Most unlikely case, missing both
    elif periods == 0:
        fixed = '{}.{}.{}'.format(table['database']['name'], table['schema'], full_name)
    elif periods == 1:
        fixed = '{}.{}'.format(table['database']['name'], full_name)
    else:
        logger().error('??????')

    logger().debug('  ❓ Fixing incomplete FQN: {} => {}'.format(table['fullName'], fixed))

    return fixed
