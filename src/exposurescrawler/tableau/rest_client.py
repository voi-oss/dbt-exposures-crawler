import tableauserverclient as TSC
from functools import lru_cache


class TableauRestClient:
    """
    Thin wrapper around the official Tableau Server client.
    Initialized with user+passw or access token
    """

    def __init__(self, url: str):
        self.url = url
        self.server = TSC.Server(url, use_server_version=True)

    @classmethod
    def config_user_and_password(cls, url: str, username: str, password: str):
        # Specific initialization to tableau server via user and password
        tableau_cls = cls(url=url)
        tableau_cls.tableau_auth = TSC.TableauAuth(username, password)

        return tableau_cls

    @classmethod
    def config_token(cls, url: str, token_name: str, token_value: str):
        # Specific initialization to tableau server via access token
        tableau_cls = cls(url=url)
        tableau_cls.tableau_auth = TSC.PersonalAccessTokenAuth(token_name, token_value)

        return tableau_cls

    @lru_cache(maxsize=None)
    def retrieve_workbook(self, workbook_id: str):
        with self.server.auth.sign_in(self.tableau_auth):
            workbook = self.server.workbooks.get_by_id(workbook_id)

        return workbook

    @lru_cache(maxsize=None)
    def retrieve_user(self, user_id: str):
        with self.server.auth.sign_in(self.tableau_auth):
            user = self.server.users.get_by_id(user_id)

        return user

    def run_metadata_api(self, query: str):
        with self.server.auth.sign_in(self.tableau_auth):
            response = self.server.metadata.query(query)

        return response['data']

    def retrieve_all_workbooks(self):
        with self.server.auth.sign_in(self.tableau_auth):
            all_workbooks = list(TSC.Pager(self.server.workbooks))

        return all_workbooks

    def retrieve_all_users(self):
        with self.server.auth.sign_in(self.tableau_auth):
            all_users = list(TSC.Pager(self.server.users))

        return all_users
