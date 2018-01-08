from py2neo import Graph, Node, Relationship

from slate import Settings


class AbstractThing:
    _thing_type = None
    _thing_default_labels = []
    _thing_default_properties = {}

    def __init__(self, *labels, **properties):
        self.labels = self._thing_default_labels[:] + list(labels)
        self.properties = self._thing_default_properties.copy()
        self.properties.update(properties)

    @property
    def obj(self):
        if self._thing_type:
            return self._thing_type(*self.labels, **self.properties)
        return self._thing_type

    def __repr__(self):
        return repr(self.obj)

    def __getattribute__(self, item):
        if hasattr(self.obj, item):
            getattr(self.obj, item)
        obj = self.__getattr__(self, item)
        if obj and obj.is_float and 'ts' in item:
            return float(obj)
        return obj


class _Message(AbstractThing):
    _thing_type = Node
    _thing_default_labels = ['Slack']


class SlackNode(Node):
    def __init__(self, *labels, **properties):
        if 'Slack' not in labels:
            labels = (*labels, 'Slack')
        obj = properties.pop('__obj', None)
        if obj:
            properties['team_id'] = obj.team_id
            properties['api_app_id'] = obj.api_app_id
            properties['event_id'] = obj.event_id
        super().__init__(*labels, **properties)


class SlackRelationship(Relationship):
    Relationship(Node(), 'a', Node())


class Message(SlackNode):
    def __init__(self, obj):
        labels = ('Message',)
        properties = {
            '__obj': obj,
            'user': obj.event.user,
            'text': obj.event.text,
            'channel': obj.event.channel,
            'event_ts': float(obj.event.event_ts)
        }
        if obj.event.thread_ts:
            properties['thread_ts'] = float(obj.event.thread_ts)
        super().__init__(*labels, **properties)


def dump_all(graph):
    graph.run('match (n:Slack) detach delete n')


def make_graph_with_creds():
    return Graph(**Settings.neo4j)


async def init_graph(app):
    app.graph = make_graph_with_creds()
