import json
import re
from pprint import pprint

from py2neo import Relationship

from slate.graph import IngestEvent, User, Message, Reaction, Emoji, Emote, Team, AccessToken
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

    def _emoji_use(self, obj, use_type, msg=None, **properties):
        user = User(user=obj.event.user, team_id=obj.team_id)
        if not msg:
            msg = Message(event_ts=obj.event.item.ts, channel=obj.event.item.channel)
        emoji = Emoji(team_id=obj.team_id, **properties)
        use = use_type(user=obj.event.user, **properties)

        emoji_to_use = Relationship(emoji.n, use.n)
        user_to_use = Relationship(user.n, use.n)
        use_to_message = Relationship(use.n, msg.n)

        items = [emoji.n, use.n, emoji_to_use, user_to_use, use_to_message]

        return f'match {msg.n}' + ' '.join(f'merge {n}' for n in items)

    async def reaction_added(self, obj):
        props = {
            'reaction': obj.event.reaction,
            'event_ts': obj.event.event_ts
        }
        cypher = self._emoji_use(obj, Reaction, **props)
        result = self.graph.run(cypher)

    async def reaction_removed(self, obj):
        user = User(user=obj.event.user, team_id=obj.team_id)
        msg = Message(event_ts=obj.event.item.ts, channel=obj.event.item.channel)
        reaction = Reaction(reaction=obj.event.reaction)
        cypher = f"""
        match {user.n}-->{reaction.n}-->{msg.n} 
          set {reaction.name}.hidden = true
        """
        result = self.graph.run(cypher)

    async def message_deleted(self, obj):
        msg = Message(channel=obj.event.channel, event_ts=obj.event.deleted_ts)
        cypher = f'match {msg.n} set {msg.name}.hidden = true'
        result = self.graph.run(cypher)

    async def message_changed(self, obj):
        if obj.event.hidden and obj.event.previous_message:
            # ignoring subscribed thread message?
            return

        msg = Message(channel=obj.event.channel, event_ts=obj.event.message.ts)

        cypher = f"""
        match {msg}
        set 
          {msg.n}.text = '{obj.event.message.text}', 
          {msg.n}.last_edited_ts = {obj.event.message.edited.ts}, 
          {msg.n}.last_edited_by = '{obj.event.message.edited.user}'
        """
        result = self.graph.run(cypher)

    async def _update_users(self, obj):
        with self.graph.begin() as tx:
            for user in obj.authed_users:
                u = User(user=user, team_id=obj.team_id)
                cypher = f"""
                merge {u}
                  on create set {u.n}.created_at = timestamp(),{u.n}.last_seen = timestamp()
                  on match set {u.n}.last_seen = timestamp()
                """
                tx.run(cypher)

    async def message(self, obj):
        #  nodes
        author = User(user=obj.event.user, team_id=obj.team_id)
        msg = Message(
            text=obj.event.text,
            channel=obj.event.channel,
            event_ts=float(obj.event.event_ts),
            user=obj.event.user,
        )

        # relationships
        author_authored_msg = Relationship(author.n, 'AUTHORED', msg.n, event_ts=obj.event.event_ts)

        cypher = f'merge {author.n} merge {msg.n} merge {author_authored_msg}'

        # if it's a reply add the thread relationship
        if obj.event.thread_ts:
            thread = Message(channel=obj.event.channel, event_ts=obj.event.thread_ts)
            reply = Relationship(msg.n, 'REPLY_TO', thread.n)
            cypher = f'match {thread.n} {cypher} merge {reply}'

        result = self.graph.run(cypher)
        pattern = re.compile(':(\w+):')
        for emote in pattern.findall(obj.event.text):
            cypher = self._emoji_use(obj, Emote, msg, reaction=emote)
            self.graph.run(cypher)

    async def handle(self, payload):
        event = IngestEvent(data=json.dumps(payload),
                            event_id=payload['event_id'],
                            event_time=payload['event_time'],
                            team_id=payload['team_id'],
                            api_app_id=payload['api_app_id'])

        result = self.graph.merge(event.n)
        print(result)
        await self.dispatch(DottedNullableDict(payload))

    async def dispatch(self, obj):
        event_type = obj.event.subtype or obj.event.type
        print(f'routing to {event_type}')
        handler = getattr(self, event_type, self._print)
        await handler(obj)

    async def authorize(self, data):
        team = Team(team_name=data['team_name'], team_id=data['team_id'])
        access_token = AccessToken(access_token=data['access_token'], user=data['user_id'])
        user = User(team_id=data['team_id'], user_id=data['user_id'])
        user_to_token = Relationship(user.n, 'OWNS', access_token.n)
        token_to_team = Relationship(access_token.n, 'ACCESSES', team.n)

        cypher = f"""
        merge {team.n} merge {user.n} 
        merge {access_token.n}
          on create set {access_token.name}.created_ts=timestamp()
        merge {user_to_token}  merge {token_to_team}
        """

        result = self.graph.run(cypher)


async def init_slack(app):
    app.slack = Slack(app)
