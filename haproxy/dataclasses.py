from dataclasses import dataclass
from support.dataclasses import rowclass, field, from_args


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
