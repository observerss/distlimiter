#!/usr/bin/env python

from distutils.core import setup

setup(
    name='distlimiter',
    version='0.1.1',
    description='Distributed Limiter based on Redis',
    author='Jingchao Hu',
    install_requires=['hiredis', 'redis'],
    author_email='jingchaohu@gmail.com',
    url='https://github.com/observerss/distlimiter',
    packages=['distlimiter'],
)
