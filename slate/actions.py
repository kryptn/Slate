import json
import re
from pprint import pprint

from py2neo import Relationship

from slate.graph import IngestEvent, User, Message, Reaction, Emoji, Emote, Team, AccessToken, SlackNode
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

    def _emoji_use(self, obj, use_type, **properties):
        user = User(user=obj.event.user, team_id=obj.team_id)
        msg = Message(event_ts=obj.event.item.ts, channel=obj.event.item.channel)
        emoji = Emoji(team_id=obj.team_id, **properties)
        use = use_type(event_ts=obj.event.event_ts, user=obj.event.user, **properties)

        emoji_to_use = Relationship(emoji.n, use.n)
        user_to_use = Relationship(user.n, use.n)
        use_to_message = Relationship(use.n, msg.n)

        items = [msg, emoji, use, emoji_to_use, user_to_use, use_to_message]

        return f'match {msg} ' + ' '.join(f'merge {n}' for n in items)

    async def reaction_added(self, obj):
        props = {'reaction': obj.event.reaction}
        cypher = self._emoji_use(obj, Reaction, **props)
        result = self.graph.run(cypher)

    async def reaction_removed(self, obj):
        user = User(user=obj.event.user, team_id=obj.team_id)
        msg = Message(event_ts=obj.event.item.ts, channel=obj.event.item.channel)
        reaction = Reaction(reaction=obj.event.reaction)
        cypher = f"""
        match {user}-->{reaction}-->{msg} 
          set {reaction.name}.hidden = true
        """
        result = self.graph.run(cypher)

    async def message_deleted(self, obj):
        msg = Message(channel=obj.event.channel, event_ts=obj.event.deleted_ts)
        cypher = f'match {msg} set {msg.name}.hidden = true'
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
        msg = Message(text=obj.event.text, channel=obj.event.channel,
                      event_ts=obj.event.event_ts, __obj=obj)

        # relationships
        author_authored_msg = Relationship(author, 'AUTHORED', msg, event_ts=obj.event.event_ts)

        cypher = f'merge {author} merge {msg} merge {author_authored_msg}'

        # if it's a reply add the thread relationship
        if obj.event.thread_ts:
            thread = Message(channel=obj.event.channel, event_ts=obj.event.thread_ts)
            reply = Relationship(msg, 'REPLY_TO', thread)
            cypher = f'match {thread} {cypher} merge {reply}'

        pattern = re.compile(':(\w+):')
        for emote in pattern.findall(obj.event.text):
            props = {'reaction': emote}
            cypher += '\n' + self._emoji_use(obj, Emote, **props)

        result = self.graph.run(cypher)

    async def handle(self, payload):
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
          on create set {access_token.name}.created_ts=timestamp()
        merge {user_to_token}  merge {token_to_team}
        """

        result = self.graph.run(cypher)



async def init_slack(app):
    app.slack = Slack(app)
