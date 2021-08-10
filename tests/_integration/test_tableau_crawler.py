import os
import shutil
from collections import namedtuple
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from pytest import fixture

from exposurescrawler.crawlers.tableau import tableau_crawler
from exposurescrawler.dbt.manifest import DbtManifest

CURRENT_FOLDER = Path(__file__).resolve().parent
PATH_TO_MANIFEST_FIXTURE = CURRENT_FOLDER.parent / '_fixtures' / 'manifest.json'


@fixture
def manifest_path():
    """
    To prevent overwriting the fixture on the tests, we actually use a copy of it.
    """
    with NamedTemporaryFile() as temp_file:
        shutil.copy(PATH_TO_MANIFEST_FIXTURE, temp_file.name)
        yield temp_file.name


@fixture(autouse=True)
def mock_graphql_custom_sql_result():
    # Format extracted from a real execution of the project
    results = {
        'customSQLTablesConnection': {
            'nodes': [
                {
                    'query': "select * from sample_db.public.customers",
                    'name': 'Custom SQL Query',
                    'isEmbedded': None,
                    'database': {'name': 'SAMPLE_DB', 'connectionType': 'snowflake'},
                    'tables': [],
                    'downstreamWorkbooks': [
                        {
                            'luid': 'customers-workbook-luid',
                            'name': 'Customers workbook',
                        }
                    ],
                },
                {
                    'query': "select * from sample_db.public.customers left join "
                    "sample_db.public.orders on customers.id = orders.customer_id",
                    'name': 'Custom SQL Query',
                    'isEmbedded': None,
                    'database': {'name': 'SAMPLE_DB', 'connectionType': 'snowflake'},
                    'tables': [],
                    'downstreamWorkbooks': [
                        {
                            'luid': 'company-kpis-workbook-luid',
                            'name': 'Company KPIs workbook',
                        }
                    ],
                },
            ]
        }
    }

    with patch('exposurescrawler.tableau.graphql_client._fetch_custom_sql', autospec=True) as mock:
        mock.return_value = results
        yield


@fixture(autouse=True)
def mock_graphql_native_sql_result():
    # Format extracted from a real execution of the project
    results = {
        'workbooksConnection': {
            'nodes': [
                {
                    'id': '[irrelevant]',
                    'luid': 'orders-workbook-luid',
                    'name': 'Orders workbook',
                    'embeddedDatasources': [
                        {
                            'id': '[irrelevant]',
                            'name': 'DATASOURCE NAME',
                            'upstreamTables': [
                                {
                                    'database': {'name': 'SAMPLE_DB'},
                                    'schema': 'PUBLIC',
                                    'fullName': '[PUBLIC].[ORDERS]',
                                    'connectionType': 'snowflake',
                                }
                            ],
                        },
                    ],
                },
                {
                    'id': '[irrelevant]',
                    'luid': 'd2b5bfce-3211-49fb-a88d-63e5b98ee317',
                    'name': 'Unrelated workbook',
                    'embeddedDatasources': [
                        {
                            'id': '[irrelevant]',
                            'name': 'UNRELATED DATASOURCE',
                            'upstreamTables': [
                                {
                                    'database': {'name': 'FOO_DB'},
                                    'schema': 'PUBLIC',
                                    'fullName': 'FOO_DB.SOME_SCHEMA.RANDOM_TABLE',
                                    'connectionType': 'snowflake',
                                }
                            ],
                        },
                    ],
                },
            ]
        }
    }

    with patch('exposurescrawler.tableau.graphql_client._fetch_native_sql', autospec=True) as mock:
        mock.return_value = results
        yield


@fixture(autouse=True)
def mock_tableau_rest_api():
    WorkbookDetailsMock = namedtuple(
        'WorkbookDetailsMock',
        [
            'id',
            'name',
            'description',
            'webpage_url',
            'owner_id',
            'project_name',
            'tags',
            'created_at',
            'updated_at',
        ],
        defaults=[
            None,
            None,
            'Workbook description',
            'http://hostname/path/to/workbook',
            'owner-id',
            'A Tableau folder',
            [],
            'created-at',
            'updated-at',
        ],
    )

    UserDetailsMock = namedtuple('UserDetailsMock', ['id', 'fullname', 'name'])

    workbook_details = {
        'customers-workbook-luid': WorkbookDetailsMock(id='aaa', name='Customers workbook'),
        'company-kpis-workbook-luid': WorkbookDetailsMock(id='bbb', name='Company KPIs workbook'),
        'orders-workbook-luid': WorkbookDetailsMock(
            id='ccc', name='Orders workbook', tags=['certified']
        ),
    }

    def _get_workbook_details(workbook_id):
        return workbook_details[workbook_id]

    with patch('exposurescrawler.crawlers.tableau.TableauRestClient', autospec=True) as mock:
        instance = mock.return_value
        instance.retrieve_workbook.side_effect = _get_workbook_details
        instance.retrieve_user.return_value = UserDetailsMock(
            'user-id', 'John Doe', 'john.doe@example.com'
        )
        yield


@patch.dict(
    os.environ,
    {
        'TABLEAU_URL': 'https://my-tableau-server.com',
        'TABLEAU_USERNAME': '',
        'TABLEAU_PASSWORD': '',
    },
    clear=True,
)
def test_tableau_crawler(manifest_path):
    with patch.object(DbtManifest, 'save', autospec=True) as mock:
        tableau_crawler(manifest_path, 'jeffle_shop', [], True)

        final_manifest = mock.call_args.args[0].data
        exposure = final_manifest['exposures']['exposure.jeffle_shop.tableau_orders_workbook_ccc']

        assert len(final_manifest['exposures']) == 3
        assert exposure['name'] == 'tableau_orders_workbook_ccc'
        assert 'Workbook description' in exposure['description']
        assert 'https://my-tableau-server.com/path/to/workbook' in exposure['description']
        assert exposure['type'] == 'Dashboard'
        assert exposure['tags'] == ['tableau:certified']
        assert exposure['depends_on'] == {'nodes': ['model.jaffle_shop.orders']}
        assert exposure['owner'] == {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
        }
