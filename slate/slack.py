import json
from pprint import pprint

from py2neo import Relationship

from slate.graph import SlackNode
from slate.utils import DottedNullableDict

S = SlackNode
IngestEvent = lambda *l, **p: S('IngestEvent', *l, **p)
User = lambda *l, **p: S('User', *l, **p)
Message = lambda *l, **p: S('Message', *l, **p)
Reaction = lambda *l, **p: S('Reaction', *l, **p)
Emoji = lambda *l, **p: S('Emoji', *l, **p)
Team = lambda *l, **p: S('Team', *l, **p)
AccessToken = lambda *l, **p: S('AccessToken', *l, **p)


class Slack:

    def __init__(self, app):
        self.app = app
        self.history = []

    @property
    def graph(self):
        return self.app.graph

    async def _print(self, obj):
        pprint(obj)

    async def reaction_added(self, obj):
        user = User(user=obj.event.user, team_id=obj.team_id)
        msg = Message(event_ts=obj.event.item.ts, channel=obj.event.item.channel)
        emoji = Emoji(team_id=obj.team_id, reaction=obj.event.reaction)
        reaction = Reaction(event_ts=obj.event.event_ts, reaction=obj.event.reaction, user=obj.event.user)

        emoji_to_reaction = Relationship(emoji, reaction)
        user_to_reaction = Relationship(user, reaction)
        reaction_to_message = Relationship(reaction, msg)

        cypher = f"""
        // nodes
        match {msg}
        merge {user} merge {emoji} merge {reaction}
        // relationships
        merge {user_to_reaction}
        merge {emoji_to_reaction}
        merge {reaction_to_message}
        """

        result = self.graph.run(cypher)

    async def reaction_removed(self, obj):
        user = User(user=obj.event.user, team_id=obj.team_id)
        msg = Message(event_ts=obj.event.item.ts, channel=obj.event.item.channel)
        reaction = Reaction(reaction=obj.event.reaction)
        cypher = f'match {user}-->{reaction}-->{msg} set {reaction.__name__}.hidden = true'
        result = self.graph.run(cypher)

    async def message_deleted(self, obj):
        msg = Message(channel=obj.event.channel, event_ts=obj.event.deleted_ts)
        cypher = f'match {msg} set {msg.__name__}.hidden = true'
        result = self.graph.run(cypher)

    async def message_changed(self, obj):
        if obj.event.hidden and obj.event.previous_message:
            # ignoring subscribed thread message?
            return

        msg = Message(channel=obj.event.channel, event_ts=obj.event.message.ts)
        n = msg.__name__

        cypher = f"""
        match {msg}
        set 
          {n}.text = '{obj.event.message.text}', 
          {n}.last_edited_ts = {obj.event.message.edited.ts}, 
          {n}.last_edited_by = '{obj.event.message.edited.user}'
        """
        result = self.graph.run(cypher)

    async def _update_users(self, obj):
        with self.graph.begin() as tx:
            for user in obj.authed_users:
                tx.merge(User(user=user, team_id=obj.team_id))

    async def message(self, obj):
        author = User(user=obj.event.user, team_id=obj.team_id)
        msg = Message(text=obj.event.text, channel=obj.event.channel,
                      event_ts=obj.event.event_ts, __obj=obj)
        author_authored_msg = Relationship(author, 'AUTHORED', msg, event_ts=obj.event.event_ts)
        cypher = f'merge {author} merge {msg} merge {author_authored_msg}'
        if obj.event.thread_ts:
            thread = Message(channel=obj.event.channel, event_ts=obj.event.thread_ts)
            reply = Relationship(msg, 'REPLY_TO', thread)
            cypher = f'match {thread} {cypher} merge {reply}'
        result = self.graph.run(cypher)

    async def handle(self, payload):
        print('appending?')
        event = IngestEvent(data=json.dumps(payload),
                            event_id=payload['event_id'],
                            event_time=payload['event_time'],
                            team_id=payload['team_id'],
                            api_app_id=payload['api_app_id'])
        self.graph.merge(event)
        await self.dispatch(DottedNullableDict(payload))

    async def dispatch(self, obj):
        self.app.loop.create_task(self._update_users(obj))
        event_type = obj.event.subtype or obj.event.type
        print(f'routing to {event_type}')
        handler = getattr(self, event_type, self._print)
        await handler(obj)

    async def authorize(self, data):
        team = Team(team_name=data['team_name'], team_id=data['team_id'])
        access_token = AccessToken(access_token=data['access_token'], user=data['user_id'])
        user = User(team_id=data['team_id'], user_id=data['user_id'])
        user_to_token = Relationship(user, 'OWNS', access_token)
        token_to_team = Relationship(access_token, 'ACCESSES', team)

        cypher = f"""
        merge {team} merge {user} 
        merge {access_token}
          on create set {access_token.__name__}.created_ts=timestamp()
        merge {user_to_token}  merge {token_to_team}
        """

        result = self.graph.run(cypher)


async def init_slack(app):
    app.slack = Slack(app)
