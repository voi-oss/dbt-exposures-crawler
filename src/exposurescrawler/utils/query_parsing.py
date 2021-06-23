from typing import Any, Mapping


def search_model_in_query(query: str, models: Mapping[str, Any]) -> dict[str, Any]:
    """
    Takes a SQL query and a sequence of models and returns which models (if any) were
    found in the query.

    :param query:
    :param models:
    :return:
    """

    found: dict[str, Any] = {}

    query = query.lower().replace('"', '').replace("'", '')

    for model in models.keys():
        if model in query:
            found[model] = models[model]

    return found
