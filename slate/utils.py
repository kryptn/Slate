import copy


class DottedNullableDict:
    def __init__(self, obj):
        self.obj = copy.deepcopy(obj)
        for key, value in self.obj.items():
            if isinstance(value, dict):
                self.obj[key] = DottedNullableDict(value)

    def __getattr__(self, item):
        return self.obj.get(item, None)
