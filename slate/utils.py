import copy


def is_ts(item, name):
    if 'ts' in name:
        try:
            return float(item)
        except:
            pass
    return None


class DottedNullableDict:
    def __init__(self, obj):
        self.obj = copy.deepcopy(obj)
        for key, value in self.obj.items():
            if isinstance(value, dict):
                self.obj[key] = DottedNullableDict(value)

    def __getattr__(self, item):
        obj = self.obj.get(item, None)
        return is_ts(obj, item) or obj
