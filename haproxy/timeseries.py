import random
import string
from dataclasses import is_dataclass
from haproxy.collections import Collection
from haproxy.dataclasses import Proxy, Frontend


class TimeSeries(Collection):

    def __aggregate__(self, field):
        if not self._items:
            return None
        else:
            values = (getattr(i, field.name) for i in self._items)
            if is_dataclass(field.type):
                values = [v for v in values if v is not None]
                if len(values) >= 1:
                    cls_uuid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    cls = type(field.type.__name__ + 'TimeSeries_' + cls_uuid, (TimeSeries, field.type), {})
                    return cls(values)
                else:
                    return None
            else:
                return values

    def append(self, item):
        classes = tuple(cls for cls in self.__class__.__mro__ if cls not in Collection.__mro__
                        and not issubclass(cls, Collection))
        if not isinstance(item, classes):
            raise TypeError('Item must be an instance of ' +
                            ' or '.join(', '.join([c.__name__ for c in classes]).rsplit(', ', 1)))
        self._items.append(item)


class ProxyTimeSeries(TimeSeries, Proxy):
    pass


class FrontendTimeSeries(TimeSeries, Frontend):
    pass
