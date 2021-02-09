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


@dataclass(frozen=True)
class Rate:
    current: int = None
    max: int = None


@dataclass(frozen=True)
class LimitedRate(Rate):
    limit: int = False


@dataclass(frozen=True)
class Count:
    current: int = None
    max: int = None


@dataclass(frozen=True)
class LimitedCount(Count):
    limit: int = False


@dataclass(frozen=True)
class Time:
    average: int = 0
    max: int = 0


@dataclass(frozen=True)
class Cache:
    lookups: int = None
    hits: int = None


@dataclass(frozen=True)
class Error:
    total: int = 0
    client: int = 0
    server: int = 0


@rowclass(frozen=True)
class Session:
    rate: Rate = field(callback=from_args(current='rate', max='rate_max'), default=None)
    count: LimitedCount = field(callback=from_args(current='scur', max='smax', limit='slim'), default=None)
    total: int = field(field='stot', default=0)


@rowclass(frozen=True)
class RateLimitedSession(Session):
    rate: LimitedRate = field(callback=from_args(current='rate', max='rate_max', limit='rate_lim'), default=None)


@rowclass(frozen=True)
class Connection:
    rate: Rate = field(callback=from_args(current='conn_rate', max='conn_rate_max'), default=None)
    total: int = field(field='conn_tot', default=0)
    error: int = field(field='econ', default=0)


@rowclass(frozen=True)
class AbstractHTTP:
    total: int = field(field='req_tot', default=0)
    hrsp_1xx: int = field(field='hrsp_1xx', default=0)
    hrsp_2xx: int = field(field='hrsp_2xx', default=0)
    hrsp_3xx: int = field(field='hrsp_3xx', default=0)
    hrsp_4xx: int = field(field='hrsp_4xx', default=0)
    hrsp_5xx: int = field(field='hrsp_5xx', default=0)
    hrsp_other: int = field(field='hrsp_other', default=0)
    failed_rw: int = field(field='wrew', default=0)


@rowclass(frozen=True)
class AbstractCachedHTTP(AbstractHTTP):
    cache: Cache = field(callback=from_args(lookups='cache_lookups', hits='cache_hits'), default=None)
    hrsp_2xx_compressed: int = field(field='comp_rsp', default=0)


@rowclass(frozen=True)
class DummyRequest:
    denied: int = field(field='dreq', default=0)


@rowclass(frozen=True)
class Request(DummyRequest):
    error: int = field(field='ereq', default=0)


@rowclass(frozen=True)
class HTTPRequest(AbstractCachedHTTP, Request):
    rate: Rate = field(callback=from_args(current='req_rate', max='req_rate_max'), default=None)
    intercepted: int = field(field='intercepted', default=0)


@rowclass(frozen=True)
class DummyResponse:
    denied: int = field(field='dresp', default=0)


@rowclass(frozen=True)
class Response(DummyResponse):
    errors: Error = field(callback=from_args(total='eresp', client='cli_abrt', server='srv_abrt'), default=None)


@rowclass(frozen=True)
class HTTPResponse(AbstractHTTP, Response):
    time: Time = field(callback=from_args(average='rtime', max='rtime_max'), default=None)


@rowclass(frozen=True)
class CachedHTTPResponse(AbstractCachedHTTP, HTTPResponse):
    pass


@dataclass(frozen=True)
class Bytes:
    inbound: int = 0
    outbound: int = 0


@dataclass(frozen=True)
class Proxy:
    host: str = field(field='_host')
    name: str = field(field='# pxname')
    status: str = field(field='status', default='UNKNOWN')
    sessions: Session = None
    connections: Connection = None
    requests: DummyRequest = None
    responses: DummyResponse = None
    bytes: Bytes = field(callback=from_args(inbound='bin', outbound='bout'), default=None)

    @classmethod
    def from_row(cls, host, row):
        svname = row['svname']
        row['_host'] = host
        if svname == 'FRONTEND':
            proxy = Frontend
        elif svname == 'BACKEND':
            proxy = Backend
        else:
            proxy = Worker

        return proxy.from_row(row)


@rowclass(frozen=True)
class Frontend(Proxy):
    requests: Request = \
        field(callback=lambda _, r: HTTPRequest.from_row(r) if r['mode'] == 'http' else Request.from_row(r),
              default=None)


@rowclass(frozen=True)
class Backend(Proxy):
    responses: Response = \
        field(callback=lambda _, r: CachedHTTPResponse.from_row(r) if r['mode'] == 'http' else Response.from_row(r),
              default=None)


@rowclass(frozen=True)
class Worker(Backend):
    responses: Response = \
        field(callback=lambda _, r: HTTPResponse.from_row(r) if r['mode'] == 'http' else Response.from_row(r),
              default=None)
