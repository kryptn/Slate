from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='slate',
    version='0.1',
    license='MIT',
    packages=['slate'],
    install_requires=requirements
)
