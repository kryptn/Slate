from pprint import pprint

from slate.graph import Message
from slate.utils import DottedNullableDict


class Slack:

    def __init__(self, app):
        self.app = app
        self.history = []

    @property
    def graph(self):
        return self.app.graph

    async def _print(self, obj):
        pprint(obj)

    async def message_changed(self, obj):
        q = f"""
        match (n:Message {{channel: '{obj.event.channel}', event_ts: {obj.event.message.ts}}})
        set 
          n.text = '{obj.event.message.text}', 
          n.last_edited_ts = {obj.event.message.edited.ts}, 
          n.last_edited_by = '{obj.event.message.edited.user}'
        return n
        """
        r = self.graph.run(q)

    async def message(self, obj):
        msg = Message(obj)
        self.graph.merge(msg)

    async def handle(self, payload):
        print('appending?')
        self.history.append(payload)
        await self.dispatch(DottedNullableDict(payload))

    async def dispatch(self, obj):
        handler = getattr(self, obj.event.subtype or obj.event.type, self._print)
        await handler(obj)


async def init_slack(app):
    app.slack = Slack(app)
