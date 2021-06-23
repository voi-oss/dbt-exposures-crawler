from dataclasses import dataclass

import os
import re
from slugify import slugify
from typing import Mapping


@dataclass
class DbtExposure:
    name: str
    package_name: str
    description: str
    url: str
    depends_on: Mapping
    owner: Mapping

    resource_type: str = 'exposure'
    type: str = 'Dashboard'

    @classmethod
    def from_tableau_workbook(cls, package_name, workbook, owner, models):  # noqa
        name = 'tableau_' + slugify(workbook.name, separator='_')

        '''
        Links coming from the Tableau API will be in the shape of
        http(s)://hostname/path/to/workbook.

        Here we replace the http(s)://hostname with the full Tableau URL provided by the user.
        We expect TABLEAU_URL to be provided without a trailing slash
        '''
        url = re.sub(r'(https?:\/\/.*?)\/', os.environ['TABLEAU_URL'] + '/', workbook.webpage_url)

        description = '''
        # {project} / {name}
        {description} \n

        **Access**: [Link to Tableau]({url})

        **Created at**: {created_at}\n
        **Last updated at**: {updated_at}
        '''.format(
            project=workbook.project_name,
            name=workbook.name,
            description=workbook.description or '*no description*',
            updated_at=workbook.updated_at,
            created_at=workbook.created_at,
            url=url,
        )

        depends_on = {'nodes': list(set([model['unique_id'] for model in models]))}

        owner = {'name': owner.fullname, 'email': owner.name}

        return cls(name, package_name, description, url, depends_on, owner)

    @property
    def unique_id(self) -> str:
        return f'exposure.{self.package_name}.{self.name}'

    def _properties(self) -> dict:
        """
        Returns all properties. Useful for building to_dict

        From: https://stackoverflow.com/questions/5876049/
        """
        class_items = self.__class__.__dict__.items()
        return dict((k, getattr(self, k)) for k, v in class_items if isinstance(v, property))

    def to_dict(self):
        return {**self.__dict__, **self._properties()}
