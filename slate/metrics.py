import time
from contextlib import contextmanager

import prometheus_client
from aiohttp import web
from prometheus_client import Counter, Gauge, Histogram


class Prometheus:
    def __init__(self):
        self.request_count = Counter('requests_total', 'Total Request Count',
                                     ['app_name', 'method', 'endpoint', 'http_status'])
        self.request_latency = Histogram('request_latency_seconds', 'Request Latency',
                                         ['app_name', 'endpoint'])
        self.request_in_progress = Gauge('requests_in_progress_total', 'Requests in progress',
                                         ['app_name', 'endpoint', 'method'])
        self.graph_stats = Counter('graph_stats', 'Graph Stats',
                                   ['constraints_added', 'constraints_removed', 'contains_updates', 'indexes_added',
                                    'indexes_removed', 'labels_added', 'labels_removed', 'nodes_created',
                                    'nodes_deleted', 'properties_set', 'relationships_created',
                                    'relationships_deleted', 'query_count'])

    @contextmanager
    def in_flight(self, name, path, method):
        self.request_in_progress.labels(name, path, method).inc()
        yield
        self.request_in_progress.labels(name, path, method).dec()

    @contextmanager
    def latency(self, name, path):
        start = time.time()
        yield
        self.request_latency.labels(name, path).observe(time.time() - start)


async def metrics(request: web.Request):
    latest = prometheus_client.generate_latest()
    return web.Response(body=latest.decode('utf-8'))


async def prometheus_middleware(app: web.Application, handler):
    async def middleware(request: web.Request):
        p = app.prometheus  # type: Prometheus
        name = app.app_name
        try:
            path = request.path
            method = request.method

            with p.latency(name, path):
                with p.in_flight(name, path, method):
                    response = await handler(request)

            p.request_count.labels(name, method, path, response.status).inc()
            return response
        except Exception as ex:
            raise

    return middleware


def setup_prometheus(app: web.Application, name: str):
    app.prometheus = Prometheus()
    app.app_name = name

    app.router.add_get('/metrics/', metrics, name='metrics')
