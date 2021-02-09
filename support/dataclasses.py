from dataclasses import dataclass, MISSING, fields, Field


class RowField(Field):
    __slots__ = ('row_field', 'row_callback')

    def __init__(self, row_field, row_callback, default, default_factory, init, repr, hash, compare, metadata):
        super().__init__(default, default_factory, init, repr, hash, compare, metadata)
        self.row_field = row_field
        self.row_callback = row_callback


# noinspection PyShadowingNames
def field(*, field=None, callback=None, default=MISSING, default_factory=MISSING, init=True, repr=True,
          hash=None, compare=True, metadata=None):
    if default is not MISSING and default_factory is not MISSING:
        raise ValueError('cannot specify both default and default_factory')
    if field is not None or callback is not None:
        if callback is not None:
            if field is not None:
                raise ValueError('cannot specify both row_field and row_callback')
            if not callable(callback):
                raise ValueError('row_callback must be callable')
        return RowField(field, callback, default, default_factory, init, repr, hash, compare, metadata)
    else:
        return Field(default, default_factory, init, repr, hash, compare, metadata)


class _FromList:
    def __init__(self, lst: list):
        self.__lst__ = lst

    def __call__(self, fld: Field, row: dict):
        cls = fld.type
        args = [row[k] for k in self.__lst__]
        return cls(*args)


def from_list(lst=None):
    return _FromList(lst)


class _FromDict:
    def __init__(self, dct: dict):
        self.__dct__ = dct

    def __call__(self, fld: Field, row: dict):
        cls = fld.type
        kwargs = dict([(p, row[k]) for p, k in self.__dct__.items()])
        return cls(**kwargs)


def from_dict(dct=None):
    return _FromDict(dct)


def from_args(**kwargs):
    return _FromDict(kwargs)


def _process_class(cls, init, repr, eq, order, unsafe_hash, frozen):

    # noinspection PyShadowingNames
    def from_row(cls, row):
        rkwargs = {}
        try:
            flds = fields(cls)
        except TypeError:
            raise TypeError("Only dataclasses can be decorated with '@row_processor'")
        for fld in flds:
            if isinstance(fld, RowField):
                if fld.row_field is not None:
                    rkwargs[fld.name] = row[fld.row_field]
                if fld.row_callback is not None:
                    rkwargs[fld.name] = fld.row_callback(fld, row)
            if callable(getattr(fld.type, 'from_row', None)):
                rkwargs[fld.name] = fld.type.from_row(row)
        return cls(**rkwargs)

    cls = dataclass(cls, init=init, repr=repr, eq=eq, order=order, unsafe_hash=unsafe_hash, frozen=frozen)
    cls.from_row = classmethod(from_row)
    return cls


def rowclass(cls=None, /, *, init=True, repr=True, eq=True, order=False,
             unsafe_hash=False, frozen=False):

    # noinspection PyShadowingNames
    def wrap(cls):
        return _process_class(cls, init, repr, eq, order, unsafe_hash, frozen)

    if cls is None:
        return wrap

    return wrap(cls)
