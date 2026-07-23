import json
import logging
import time
import os

from datetime import datetime, timedelta
from prometheus_client import Summary
from prometheus_client.core import GaugeMetricFamily, REGISTRY
from alibabacloud_cms20190101 import models as cms_models
from alibabacloud_rds20140815 import models as rds_models

from aliyun_exporter.clients import AliyunClients
from aliyun_exporter.credential import build_credential_client, build_openapi_config
from aliyun_exporter.info_provider import InfoProvider
from aliyun_exporter.ratelimit import RateLimiter
from aliyun_exporter.utils import try_or_else, expand_metric_names

rds_performance = 'rds_performance'
special_projects = {
    rds_performance: lambda collector : RDSPerformanceCollector(collector),
}

requestSummary = Summary('cloudmonitor_request_latency_seconds', 'CloudMonitor request latency', ['project'])
requestFailedSummary = Summary('cloudmonitor_failed_request_latency_seconds', 'CloudMonitor failed request latency', ['project'])

class CollectorConfig(object):
    def __init__(self,
                 pool_size=10,
                 rate_limit=10,
                 credential=None,
                 metrics=None,
                 info_metrics=None,
                 ):
        # if metrics is None:
        # raise Exception('Metrics config must be set.')

        self.credential = credential
        self.metrics = expand_metric_names(metrics)
        self.rate_limit = rate_limit
        self.info_metrics = info_metrics

        if self.credential is None:
            self.credential = {}

        # ENV
        access_id = os.environ.get('ALIYUN_ACCESS_ID')
        access_secret = os.environ.get('ALIYUN_ACCESS_SECRET')
        region = os.environ.get('ALIYUN_REGION')
        if access_id is not None and len(access_id) > 0:
            self.credential['access_key_id'] = access_id
        if access_secret is not None and len(access_secret) > 0:
            self.credential['access_key_secret'] = access_secret
        if region is not None and len(region) > 0:
            self.credential['region_id'] = region

        # access_key_id/access_key_secret are optional: when omitted, the
        # Alibaba Cloud default credential chain is used instead (env AK/SK,
        # then RRSA/OIDC, then ECS RAM role, etc). But if only one of the two
        # is set, that's a configuration mistake.
        if bool(self.credential.get('access_key_id')) != bool(self.credential.get('access_key_secret')):
            raise Exception('Credential is not fully configured: access_key_id and access_key_secret must be set together.')

        if not self.credential.get('region_id'):
            self.credential['region_id'] = 'cn-hangzhou'

class AliyunCollector(object):
    def __init__(self, config: CollectorConfig):
        self.metrics = config.metrics
        self.info_metrics = config.info_metrics
        region_id = config.credential['region_id']
        credential_client = build_credential_client(config.credential)
        openapi_config = build_openapi_config(region_id, credential_client)
        self.clients = AliyunClients(openapi_config)
        self.rateLimiter = RateLimiter(max_calls=config.rate_limit)
        self.info_provider = InfoProvider(self.clients, region_id)
        self.special_collectors = dict()
        for k, v in special_projects.items():
            if k in self.metrics:
                self.special_collectors[k] = v(self)


    def query_metric(self, project: str, metric: str, period: int):
        with self.rateLimiter:
            req = cms_models.DescribeMetricLastRequest(
                namespace=project,
                metric_name=metric,
                period=str(period),
            )
            start_time = time.time()
            try:
                resp = self.clients.cms.describe_metric_last(req)
            except Exception as e:
                logging.error('Error request cloud monitor api', exc_info=e)
                requestFailedSummary.labels(project).observe(time.time() - start_time)
                return []
            else:
                requestSummary.labels(project).observe(time.time() - start_time)
        data = resp.body.to_map()
        if 'Datapoints' in data:
            points = json.loads(data['Datapoints'])
            return points
        else:
            logging.error(
                'Error query metrics for {}_{}, the response body does not have a Datapoints field, '
                'please check your permission or workload. Response: {}'.format(project, metric, data))
            return []

    def parse_label_keys(self, point):
        return [k for k in point if k not in ['timestamp', 'Maximum', 'Minimum', 'Average']]

    def format_metric_name(self, project, name):
        return 'aliyun_{}_{}'.format(project, name)

    def metric_generator(self, project, metric):
        if 'name' not in metric:
            raise Exception('name must be set in metric item.')
        name = metric['name']
        metric_name = metric['name']
        period = 60
        measure = 'Average'
        if 'rename' in metric:
            name = metric['rename']
        if 'period' in metric:
            period = metric['period']
        if 'measure' in metric:
            measure = metric['measure']

        try:
            points = self.query_metric(project, metric_name, period)
        except Exception as e:
            logging.error('Error query metrics for {}_{}'.format(project, metric_name), exc_info=e)
            yield metric_up_gauge(self.format_metric_name(project, name), False)
            return
        if len(points) < 1:
            yield metric_up_gauge(self.format_metric_name(project, name), False)
            return
        label_keys = self.parse_label_keys(points[0])
        gauge = GaugeMetricFamily(self.format_metric_name(project, name), '', labels=label_keys)
        added = 0
        for point in points:
            if measure not in point:
                logging.error(
                    'Error query metrics for {}_{}, point does not have "{}" field: {}'.format(
                        project, metric_name, measure, point))
                continue
            gauge.add_metric([try_or_else(lambda: str(point[k]), '') for k in label_keys], point[measure])
            added += 1
        if added < 1:
            yield metric_up_gauge(self.format_metric_name(project, name), False)
            return
        yield gauge
        yield metric_up_gauge(self.format_metric_name(project, name), True)

    def collect(self):
        for project in self.metrics:
            if project in special_projects:
                continue
            for metric in self.metrics[project]:
                yield from self.metric_generator(project, metric)
        if self.info_metrics != None:
            for resource in self.info_metrics:
                yield self.info_provider.get_metrics(resource)
        for v in self.special_collectors.values():
            yield from v.collect()



def metric_up_gauge(resource: str, succeeded=True):
    metric_name = resource + '_up'
    description = 'Did the {} fetch succeed.'.format(resource)
    return GaugeMetricFamily(metric_name, description, value=int(succeeded))


class RDSPerformanceCollector:

    def __init__(self, delegate: AliyunCollector):
        self.parent = delegate

    def collect(self):
        for id in [s.labels['DBInstanceId'] for s in self.parent.info_provider.get_metrics('rds').samples]:
            metrics = self.query_rds_performance_metrics(id)
            for metric in metrics:
                yield from self.parse_rds_performance(id, metric)

    def parse_rds_performance(self, id, value):
        value_format: str = value['ValueFormat']
        metric_name = value['Key']
        keys = ['value']
        if value_format is not None and '&' in value_format:
            keys = value_format.split('&')
        metric = value['Values']['PerformanceValue']
        if len(metric) < 1:
            return
        values = metric[0]['Value'].split('&')
        for k, v in zip(keys, values):
            gauge = GaugeMetricFamily(
                self.parent.format_metric_name(rds_performance, metric_name + '_' + k),
                '', labels=['instanceId'])
            gauge.add_metric([id], float(v))
            yield gauge

    def query_rds_performance_metrics(self, id):
        now = datetime.utcnow();
        now_str = now.replace(second=0, microsecond=0).strftime("%Y-%m-%dT%H:%MZ")
        one_minute_ago_str = (now - timedelta(minutes=1)).replace(second=0, microsecond=0).strftime("%Y-%m-%dT%H:%MZ")
        req = rds_models.DescribeDBInstancePerformanceRequest(
            dbinstance_id=id,
            key=','.join([metric['name'] for metric in self.parent.metrics[rds_performance]]),
            start_time=one_minute_ago_str,
            end_time=now_str,
        )
        try:
            resp = self.parent.clients.rds.describe_dbinstance_performance(req)
        except Exception as e:
            logging.error('Error request rds performance api', exc_info=e)
            return []
        data = resp.body.to_map()
        return data['PerformanceKeys']['PerformanceKey']
