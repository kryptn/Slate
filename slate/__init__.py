import os.path

import yaml


class Settings:
    slack_client_id = ''
    slack_client_secret = ''
    slack_verification_token = ''
    slack_oauth_token = ''

    # app settings
    host = '0.0.0.0'
    port = 8080

    # neo4j settings
    neo4j = {
        'host': 'localhost',
        'password': 'neo4j_password_here'
    }

    # convenience dicts
    Web = {
        'host': host,
        'port': port
    }

    @property
    def slack_creds(self):
        return {
            'client_id': self.slack_client_id,
            'client_secret': self.slack_client_secret,
            'token': self.slack_verification_token
        }


def try_get_yaml(filename):
    data = None
    if os.path.isfile(filename):
        with open(filename) as fd:
            data = yaml.load(fd)
    return data


config_paths = ['/data/env.yml', 'env.yml', 'env.dev.yml']

for path in config_paths:
    data = try_get_yaml(path)
    if not data:
        continue
    for key, value in data.items():
        setattr(Settings, key, value)
