import pathlib

from setuptools import setup, find_packages

# Get the long description from the README file
current_folder = pathlib.Path(__file__).parent.resolve()
long_description = (current_folder / 'README.md').read_text(encoding='utf-8')

# Based on: https://packaging.python.org/tutorials/packaging-projects/
setup(
    name='dbt-exposures-crawler',
    version='0.0.1',
    description='Extracts information from different systems and convert them to dbt exposures',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/voi-oss/dbt-exposures-crawler',
    author='Voi Technology AB',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License 2.0 (Apache-2.0)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
    ],
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires='>=3.9, <4',
    install_requires=[
        'click ~= 8.0.1',
        'python-slugify ~= 4.0.1',
        'tableauserverclient ~= 0.10',
    ],
)
