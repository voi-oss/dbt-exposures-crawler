from exposurescrawler.utils.query_parsing import search_model_in_query


class TestQuerySearcher:
    def test_basic(self):
        query = '//comment SELECT * FROM "MART"."CORE"."RIDE"'
        models = {
            'mart.core.ride': {'name': 'mart.core.ride'},
            'mart.tasks.task': {'name': 'mart.tasks.task'},
        }

        assert search_model_in_query(query, models) == {
            'mart.core.ride': {'name': 'mart.core.ride'}
        }
