import pathlib

from setuptools import setup, find_packages

# Get the long description from the README file
current_folder = pathlib.Path(__file__).parent.resolve()
long_description = (current_folder / 'README.md').read_text(encoding='utf-8')

# Based on: https://packaging.python.org/tutorials/packaging-projects/
setup(
    name='dbt-exposures-crawler',
    use_scm_version={
        "write_to": "src/exposurescrawler/_version.py",
        "write_to_template": '__version__ = "{version}"\n',
        "local_scheme": "no-local-version",
    },
    description='Extracts information from different systems and convert them to dbt exposures',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/voi-oss/dbt-exposures-crawler',
    author='Voi Technology AB',
    author_email='opensource@voiapp.io',
    license='Apache License, Version 2.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3 :: Only',
    ],
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    package_data={'exposurescrawler': ['**/*.txt']},
    python_requires='>=3.8, <4',
    setup_requires=['wheel', 'setuptools_scm'],
    install_requires=[
        'click ~= 8.0.1',
        'python-slugify ~= 4.0.1',
        'tableauserverclient ~= 0.10',
    ],
)
