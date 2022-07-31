import json
from collections import UserDict
from os import name
from typing import Any, Dict, Type
from exposurescrawler.dbt.exposure import DbtExposure


class DbtManifest(UserDict):
    @classmethod
    def from_file(cls: Type['DbtManifest'], path: str) -> 'DbtManifest':
        with open(path) as file:
            manifest = json.load(file)

        return cls(manifest)

    def retrieve_models_and_sources(self) -> Dict[str, Any]:
        """
        Returns all models and sources from the manifest in a dictionary.
        The key is the fully qualified name (on the database, and not on
        the dbt object tree), and the value is the node.

        :return:
        """
        models = {}

        for node_id, node in self.data['nodes'].items():
            fqn = '{}.{}.{}'.format(node['database'], node['schema'], node['alias'])
            node['materialized_name'] = fqn
            models[fqn] = node

        for node_id, node in self.data['sources'].items():
            fqn = '{}.{}.{}'.format(node['database'], node['schema'], node['name'])
            node['materialized_name'] = fqn
            models[fqn] = node

        return models

    def add_exposure(self, exposure: DbtExposure, found):
        self['exposures'][exposure.unique_id] = exposure.to_dict()
        self['parent_map'][exposure.unique_id] = list(set([model['unique_id'] for model in found]))
        #print(self)

        #yaml = YAML()

        #ff = open(file_name, 'w+')
#
        ##    version: 2
        ##   exposures: [{'name','type','url','description','owner'}]
        ##"""
        #depends = list(('ref(''' + "'" + k.split('.')[-1] + "'" + ')''').lower() for k in set([model['unique_id'] for model in found]))
        #bb = exposure.to_dict()
        #l = {'name','type','url','description','owner'}
        #bc = {key: bb[key] for key in l if key in bb}
        #yamlData = {
        #'version': 2,
        #'exposures': [{'name': bc.get('name').lower(),'type': bc.get('type').lower(),'url':bc.get('url').lower(),'description':bc.get('description').lower(),'owner':bc.get('owner'), 'depends_on': depends}]
        #}
        #yaml.indent(sequence=4, offset=2)
        #yaml.dump(yamlData, ff)

    def to_dict(self):
        return self.data

    def save(self, path):
        with open(path, 'w') as file:
            json.dump(self.to_dict(), file, indent=4)
