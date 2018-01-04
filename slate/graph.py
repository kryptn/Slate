from py2neo import Graph, Node

from slate import Settings


class Slack(Node):
    def __init__(self, *labels, **properties):
        if 'Slack' not in labels:
            labels = (*labels, 'Slack')
        obj = properties.pop('__obj', None)
        if obj:
            properties['team_id'] = obj.team_id
            properties['api_app_id'] = obj.api_app_id
            properties['event_id'] = obj.event_id
            if obj.event.ts:
                properties['event_ts'] = float(obj.event.ts)
        super().__init__(*labels, **properties)


class Message(Slack):
    def __init__(self, obj):
        labels = ('Message',)
        properties = {
            '__obj': obj,
            'user': obj.event.user,
            'text': obj.event.text,
            'channel': obj.event.channel
        }
        super().__init__(*labels, **properties)


def dump_all(graph):
    graph.run('match (n:Slack) detach delete n')


def init_things(graph):
    graph.run('create constraint on (t:Thing) assert t.id is unique')
    graph.run('create index on :Thing(id)')


def make_graph_with_creds():
    return Graph(**Settings.neo4j)


async def init_graph(app):
    app.graph = make_graph_with_creds()
