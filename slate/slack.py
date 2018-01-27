class Event:
    def __init__(self, payload):
        self._keys = payload.keys()
        self._raw = payload
        for k, v in payload.items():
            if 'ts' in k:
                v = float(v)
            setattr(self, k, v)


class Message(Event):
    pass


events = {
    'message': Message
}


class Envelope:

    def __init__(self, payload):
        self._raw = payload
        self.team_id = payload['team_id']
        self.api_app_id = payload['api_app_id']
        self.type = payload['type']
        self.event_id = payload['event_id']
        self.event_time = int(payload['event_time'])
        self.authed_users = payload['authed_users']

        event_payload = payload['event']
        self.event = events.get(event_payload['type'], Event)(event_payload)
