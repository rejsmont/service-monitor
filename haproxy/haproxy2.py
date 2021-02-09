import datetime
import functools
from typing import Union, Optional


def safe_int(value):
    return int(value) if str(value).isnumeric() else None


def safe_sum(values):
    s = None
    for v in values:
        if s is None:
            if str(v).isnumeric():
                s = int(v)
        elif str(v).isnumeric():
            s += int(v)
    return s


def safe_str(value):
    return str(value) if str(value) else None


def aggregates_sum(func):
    @functools.wraps(func)
    def wrapper_collection_sum(self, *args, **kwargs):
        if self._collection is None:
            return func(self, *args, **kwargs)
        else:
            return safe_sum([func(i, *args, **kwargs) for i in self._collection])
    return wrapper_collection_sum


def aggregates_list(cls):
    def decorator_aggregates_list(func):
        @functools.wraps(func)
        def wrapper_collection_sum(self, *args, **kwargs):
            if self._collection is None:
                return func(self, *args, **kwargs)
            else:
                return cls([func(i, *args, **kwargs) for i in self._collection])
        return wrapper_collection_sum
    return decorator_aggregates_list


class Rate:

    def __init__(self, value, max=None, limit=None):
        if isinstance(value, list):
            self._collection = value
        else:
            self._collection = None
            self._current = safe_int(value)
            max = safe_int(max)
            self._max = max if max is not None and max > self._current else self._current
            limit = safe_int(limit)
            self._limit = limit if limit is not None and limit > 0 else False

    @property
    @aggregates_sum
    def current(self) -> Optional[int]:
        return self._current

    @property
    @aggregates_sum
    def max(self) -> Optional[int]:
        return self._max

    @property
    @aggregates_sum
    def limit(self) -> Union[int, bool]:
        return self._limit

    def __int__(self):
        return int(self.current)

    def __float__(self):
        return float(self.current)

    def __str__(self):
        return str(self.current)

    def as_dict(self):
        return {
            'current': self.current,
            'max': self.max,
            'limit': self.limit,
        }


class Count(Rate):
    pass


class Cache:

    def __init__(self, value, hits=None):
        if isinstance(value, list):
            self._collection = value
        else:
            self._collection = None
            self._lookups = safe_int(value)
            self._hits = safe_int(hits)

    @property
    @aggregates_sum
    def lookups(self) -> Optional[int]:
        return self._lookups

    @property
    @aggregates_sum
    def hits(self) -> Optional[int]:
        return self._hits

    def as_dict(self):
        return {
            'lookups': self.lookups,
            'hits': self.hits,
        }


class AbstractRowProcessor:

    def __init__(self, **kwargs):
        self._collection = None

    @classmethod
    def from_row(cls, row):
        raise NotImplementedError


class AbstractRated(AbstractRowProcessor):

    def __init__(self, r_current=None, r_max=None, r_limit=None, **kwargs):
        super().__init__(**kwargs)
        self._rate = Rate(r_current, r_max, r_limit)

    @classmethod
    def from_row(cls, row):
        raise NotImplementedError

    @property
    @aggregates_list(Rate)
    def rate(self) -> Rate:
        return self._rate

    def as_dict(self):
        return {
            'rate': self.rate.as_dict(),
        }


class AbstractCounted(AbstractRowProcessor):

    def __init__(self, c_current=None, c_max=None, c_limit=None, **kwargs):
        super().__init__(**kwargs)
        self._count = Count(c_current, c_max, c_limit)

    @classmethod
    def from_row(cls, row):
        raise NotImplementedError

    @property
    @aggregates_list(Count)
    def count(self) -> Count:
        return self._count

    def as_dict(self):
        return {
            'count': self.count.as_dict(),
        }


class AbstractTotalled(AbstractRowProcessor):

    def __init__(self, total=None, **kwargs):
        super().__init__(**kwargs)
        self._total = safe_int(total)

    @classmethod
    def from_row(cls, row):
        raise NotImplementedError

    @property
    @aggregates_sum
    def total(self) -> Optional[int]:
        return self._total

    def __int__(self):
        return int(self.total)

    def __float__(self):
        return float(self.total)

    def __str__(self):
        return str(self.total)

    def as_dict(self):
        return {
            'total': self.total,
        }


class AbstractErrored(AbstractRowProcessor):

    def __init__(self, denied=None, error=None, **kwargs):
        super().__init__(**kwargs)
        self._denied = safe_int(denied)
        self._error = safe_int(error)

    @classmethod
    def from_row(cls, row):
        raise NotImplementedError

    @property
    @aggregates_sum
    def denied(self) -> Optional[int]:
        return self._denied

    @property
    @aggregates_sum
    def error(self) -> Optional[int]:
        return self._error

    def as_dict(self):
        return {
            'denied': self.denied,
            'error': self.error,
        }


class Sessions(AbstractRated, AbstractCounted, AbstractTotalled):

    def __init__(self, sessions=None, **kwargs):
        super().__init__(**kwargs)
        self._collection = sessions

    @classmethod
    def from_row(cls, row):
        return cls(r_current=row['rate'], r_max=row['rate_max'], r_limit=row['rate_lim'],
                   c_current=row['scur'], c_max=row['smax'], c_limit=row['slim'], total=row['stot'])

    def as_dict(self):
        return {
            'count': self.count.as_dict(),
            'rate': self.rate.as_dict(),
            'total': self.total,
        }


class Connections(AbstractRated, AbstractTotalled, AbstractErrored):

    def __init__(self, connections=None, **kwargs):
        super().__init__(**kwargs)
        self._collection = connections

    @classmethod
    def from_row(cls, row):
        return cls(r_current=row['conn_rate'], r_max=row['conn_rate_max'], r_limit=None,
                   total=row['conn_tot'], denied=row['dcon'], error=row['econ'])

    def as_dict(self):
        return {
            'rate': self.rate.as_dict(),
            'total': self.total,
            'denied': self.denied,
            'error': self.error,
        }


class Requests(AbstractRated, AbstractTotalled, AbstractErrored):

    def __init__(self, requests=None, intercepted=None, failed_rw=None, c_lookups=None, c_hits=None, **kwargs):
        super().__init__(**kwargs)
        self._collection = requests
        self._intercepted = safe_int(intercepted)
        self._failed_rewrites = safe_int(failed_rw)
        self._cache = Cache(c_lookups, c_hits)

    @classmethod
    def from_row(cls, row):
        return cls(r_current=row['req_rate'], r_max=row['req_rate_max'], r_limit=None,
                   total=row['req_tot'], denied=row['dreq'], error=row['ereq'],
                   intercepted=row['intercepted'], failed_rw=row['wrew'],
                   c_lookups=row['cache_lookups'], c_hits=row['cache_hits'])

    @property
    @aggregates_sum
    def intercepted(self) -> Optional[int]:
        return self._intercepted

    @property
    @aggregates_sum
    def failed_rewrites(self) -> Optional[int]:
        return self._failed_rewrites

    @property
    @aggregates_list(Cache)
    def cache(self) -> Cache:
        return self._cache

    def as_dict(self):
        return {
            'rate': self.rate.as_dict(),
            'total': self.total,
            'denied': self.denied,
            'error': self.error,
            'intercepted': self.intercepted,
            'failed_rewrites': self.failed_rewrites,
            'cache': self.cache.as_dict(),
        }


class Responses(AbstractErrored):

    def __init__(self, hrsp_1xx=None, hrsp_2xx=None, hrsp_2xx_compressed=None, hrsp_3xx=None, hrsp_4xx=None,
                 hrsp_5xx=None, hrsp_other=None, **kwargs):
        super().__init__(**kwargs)
        self._hrsp_1xx = safe_int(hrsp_1xx)
        self._hrsp_2xx = safe_int(hrsp_2xx)
        self._hrsp_2xx_compressed = safe_int(hrsp_2xx_compressed)
        self._hrsp_3xx = safe_int(hrsp_3xx)
        self._hrsp_4xx = safe_int(hrsp_4xx)
        self._hrsp_5xx = safe_int(hrsp_5xx)
        self._hrsp_other = safe_int(hrsp_other)

    @classmethod
    def from_row(cls, row):
        return cls(hrsp_1xx=row['hrsp_1xx'], hrsp_2xx=row['hrsp_2xx'], hrsp_2xx_compressed=row['comp_rsp'],
                   hrsp_3xx=row['hrsp_3xx'], hrsp_4xx=row['hrsp_4xx'], hrsp_5xx=row['hrsp_5xx'],
                   hrsp_other=row['hrsp_other'], denied=row['dresp'], error=row['eresp'])

    @property
    @aggregates_sum
    def hrsp_1xx(self) -> Optional[int]:
        return self._hrsp_1xx

    @property
    @aggregates_sum
    def hrsp_2xx(self) -> Optional[int]:
        return self._hrsp_2xx

    @property
    @aggregates_sum
    def hrsp_2xx_compressed(self) -> Optional[int]:
        return self._hrsp_2xx_compressed

    @property
    @aggregates_sum
    def hrsp_3xx(self) -> Optional[int]:
        return self._hrsp_3xx

    @property
    @aggregates_sum
    def hrsp_4xx(self) -> Optional[int]:
        return self._hrsp_4xx

    @property
    @aggregates_sum
    def hrsp_5xx(self) -> Optional[int]:
        return self._hrsp_5xx

    @property
    @aggregates_sum
    def hrsp_other(self) -> Optional[int]:
        return self._hrsp_other

    def as_dict(self):
        return {
            'hrsp_1xx': self.hrsp_1xx,
            'hrsp_2xx': self.hrsp_2xx,
            'hrsp_2xx_compressed': self.hrsp_2xx_compressed,
            'hrsp_3xx': self.hrsp_3xx,
            'hrsp_4xx': self.hrsp_4xx,
            'hrsp_5xx': self.hrsp_5xx,
            'hrsp_other': self.hrsp_other,
            'denied': self.denied,
            'error': self.error,
        }


class Bytes:

    def __init__(self, value=None, out=None):
        if isinstance(value, list):
            self._collection = value
        else:
            self._collection = None
            self._in = safe_int(value)
            self._out = safe_int(out)

    @property
    @aggregates_sum
    def inbound(self) -> Optional[int]:
        return self._in

    @property
    @aggregates_sum
    def outbound(self) -> Optional[int]:
        return self._out

    def __str__(self):
        return '<' + str(self._in) + '|' + str(self._out) + '>'

    def as_dict(self):
        return {
            'in': self.inbound,
            'out': self.outbound,
        }


class Proxy:

    def __init__(self, value, status=None, sessions=None, connections=None, requests=None, bts=None):
        if isinstance(value, list):
            self._collection = value
        else:
            self._collection = None
            self._name = safe_str(value)
            self._status = safe_str(status)
            self._sessions = sessions
            self._connections = connections
            self._requests = requests
            self._bytes = bts
            self._timestamp = datetime.datetime.now()

    @classmethod
    def from_row(cls, row):
        return cls(value=row['# pxname'], status=row['status'], sessions=Sessions.from_row(row),
                   connections=Connections.from_row(row), requests=Requests.from_row(row),
                   bts=Bytes(row['bin'], row['bout']))

    @property
    def name(self) -> Optional[str]:
        if self._collection is None:
            return self._name
        else:
            return self._collection[0].name

    @property
    def timestamp(self) -> datetime.datetime:
        if self._collection is None:
            return self._timestamp
        else:
            return self._collection[0].timestamp

    @property
    def status(self) -> Optional[str]:
        if self._collection is None:
            return self._status
        else:
            status = None
            for s in [i.status for i in self._collection]:
                status = s if status is None else status
                if s != status:
                    return 'DEGRADED'
            return status

    @property
    @aggregates_list(Sessions)
    def sessions(self) -> Sessions:
        return self._sessions

    @property
    @aggregates_list(Connections)
    def connections(self) -> Connections:
        return self._connections

    @property
    @aggregates_list(Requests)
    def requests(self) -> Requests:
        return self._requests

    @property
    @aggregates_list(Bytes)
    def bytes(self) -> Bytes:
        return self._bytes

    def as_dict(self):
        return {
            'name': self.name,
            'timestamp': self.timestamp,
            'status': self.status,
            'sessions': self.sessions.as_dict(),
            'connections': self.connections.as_dict(),
            'requests': self.requests.as_dict(),
            'bytes': self.bytes.as_dict(),
        }


class Frontend(Proxy):

    def __init__(self, host, value, status=None, sessions=None, connections=None, requests=None, bts=None):
        super().__init__(value, status, sessions, connections, requests, bts)
        self._host = host

    @classmethod
    def from_row(cls, host, row):
        return cls(host, value=row['# pxname'], status=row['status'], sessions=Sessions.from_row(row),
                   connections=Connections.from_row(row), requests=Requests.from_row(row),
                   bts=Bytes(row['bin'], row['bout']))

    @property
    def host(self) -> Optional[str]:
        if self._collection is None:
            return self._host
        else:
            return None

    def as_dict(self):
        return {
            'name': self.name,
            'host': self.host,
            'timestamp': self.timestamp,
            'status': self.status,
            'sessions': self.sessions.as_dict(),
            'connections': self.connections.as_dict(),
            'requests': self.requests.as_dict(),
            'bytes': self.bytes.as_dict(),
        }


class Backend(Proxy):

    def __init__(self, host, value, status=None, sessions=None, connections=None, requests=None, bts=None):
        super().__init__(value, status, sessions, connections, requests, bts)
        self._host = host

    @classmethod
    def from_row(cls, host, row):
        return cls(host, value=row['# pxname'], status=row['status'], sessions=Sessions.from_row(row),
                   connections=Connections.from_row(row), requests=Requests.from_row(row),
                   bts=Bytes(row['bin'], row['bout']))

    @property
    def host(self) -> Optional[str]:
        if self._collection is None:
            return self._host
        else:
            return None
