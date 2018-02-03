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


class Thunk:
    def __init__(self, _callable, *args, **kwargs):
        self._callable = _callable
        self.args = args
        self.kwargs = kwargs
        self._value = None

    @property
    def value(self):
        if not self._value:
            self._value = self._callable(*self.args, **self.kwargs)
        return self._value
