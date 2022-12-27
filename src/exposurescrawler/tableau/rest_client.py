import tableauserverclient as TSC
from functools import lru_cache


class TableauRestClient:
    """
    Thin wrapper around the official Tableau Server client.
    """

    def __init__(self, url: str, username: str, password: str):
        self.tableau_auth = TSC.TableauAuth(username, password)
        self.server = TSC.Server(url, use_server_version=True)

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
