import random
import string
# noinspection PyProtectedMember
from dataclasses import fields, is_dataclass, MISSING, Field
from haproxy.dataclasses import Proxy, Frontend


class Collection:

    def __init__(self, items):
        if not is_dataclass(self):
            raise TypeError('Collections can only be applied to dataclasses')
        # noinspection PyDataclass
        self.__fields = fields(self)
        for item in items:
            classes = tuple(cls for cls in self.__class__.__mro__ if cls not in Collection.__mro__
                            and not isinstance(cls, Collection))
            if not isinstance(item, classes):
                raise TypeError('Items must be instances of ' +
                                ' or '.join(', '.join([c.__name__ for c in classes]).rsplit(', ', 1)))
        self._items = items

    def __getattribute__(self, item):
        if not item.startswith('_'):
            try:
                super().__getattribute__(item)
                return self.__aggregate__(item, None)
            except Exception as e:
                raise e
            # for field in self.__fields:
            #     if field.name == item:
            #         return self.__aggregate__(field)
        return super().__getattribute__(item)

    def __aggregate__(self, field, f_type=None):
        default = None
        if isinstance(field, Field):
            f_type = field.type
            field = field.name
            default = field.default
        if not self._items:
            return None
        else:
            values = (getattr(i, field) for i in self._items)
            if is_dataclass(f_type):
                values = [v for v in values if v is not None]
                if len(values) > 1:
                    cls_uuid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    cls = type(f_type.__name__ + 'Collection_' + cls_uuid, (Collection, f_type), {})
                    return cls(values)
                elif len(values) == 1:
                    return values[0]
                else:
                    return None
            elif f_type in (int, float, complex):
                values = (v for v in values if v is not None)
                return sum(values) if values else None
            else:
                value = list(values)[0]
                for v in values[1:]:
                    if v != value:
                        return None if isinstance(default, MISSING) else default
                return value

    def __getitem__(self, key):
        return self._items[key]

    def __len__(self):
        return len(self._items)


class ProxyCollection(Collection, Proxy):
    pass


class FrontendCollection(Collection, Frontend):
    pass


