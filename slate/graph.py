from itertools import chain

from py2neo import Graph, Node

from slate import Settings
from slate.utils import Thunk


class AbstractNode(Thunk):
    default_labels = []
    default_properties = {}

    def __init__(self, *labels, **properties):
        super().__init__(Node, *labels, **properties)

    @property
    def n(self):
        defaults = (i.default_labels for i in type(self).__mro__ if issubclass(i, AbstractNode))
        self.args = set(chain(*defaults, self.args))
        return self.value

    @property
    def name(self):
        return self.n.__name__

    def __repr__(self):
        return repr(self.n)


class SlackNode(AbstractNode):
    default_labels = ['Slack']


class Message(SlackNode):
    default_labels = ['Message']


class IngestEvent(SlackNode):
    default_labels = ['IngestEvent']


class User(SlackNode):
    default_labels = ['User']


class Reaction(SlackNode):
    default_labels = ['Reaction']


class Emoji(SlackNode):
    default_labels = ['Emoji']


class Emote(SlackNode):
    default_labels = ['Emote']


class Team(SlackNode):
    default_labels = ['Team']


class AccessToken(SlackNode):
    default_labels = ['AccessToken']


def dump_all(graph):
    graph.run('match (n:Slack) detach delete n')


def make_graph_with_creds():
    return Graph(**Settings.neo4j)


async def init_graph(app):
    app.graph = make_graph_with_creds()
