#!/usr/bin/env python3
from pathlib import Path
from setuptools import setup


def read(fname):
    # type: (str) -> str
    path = Path(__file__).parent / fname
    return path.read_text('utf-8')


setup(
    name='pytest-output-to-files',
    version='0.1.0',
    author='Jacob Lifshay',
    author_email='programmerjake@gmail.com',
    maintainer='Jacob Lifshay',
    maintainer_email='programmerjake@gmail.com',
    license='LGPL-3.0+',
    url='https://git.libre-soc.org/?p=pytest-output-to-files.git;a=summary',
    description='A pytest plugin that shortens test output with the full output stored in files',
    long_description=read('README.md'),
    py_modules=['pytest_output_to_files'],
    python_requires='>=3.7',
    install_requires=['pytest>=3.2.5'],
    classifiers=[
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Operating System :: POSIX',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
    ],
    entry_points={
        'pytest11': [
            'output_to_files = pytest_output_to_files',
        ],
    },
)
