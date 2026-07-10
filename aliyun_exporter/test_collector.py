import json
from unittest.mock import MagicMock

from aliyun_exporter.collector import AliyunCollector
from aliyun_exporter.ratelimit import RateLimiter


class FakeBody(object):
    def __init__(self, data):
        self._data = data

    def to_map(self):
        return self._data


class FakeResp(object):
    def __init__(self, data):
        self.body = FakeBody(data)


def make_collector(cms_response_data):
    collector = object.__new__(AliyunCollector)
    collector.rateLimiter = RateLimiter(max_calls=100)
    fake_cms = MagicMock()
    fake_cms.describe_metric_last.return_value = FakeResp(cms_response_data)
    collector.clients = MagicMock(cms=fake_cms)
    return collector


def test_query_metric_missing_datapoints_returns_empty_list():
    # e.g. a business-level failure (bad permission, wrong metric name, ...)
    # that still comes back as a normal response without a Datapoints field.
    collector = make_collector({'Code': '200', 'Success': False, 'Message': 'no permission'})
    assert collector.query_metric('acs_global_acceleration', 'GaBaseIpOutBps', 60) == []


def test_query_metric_with_datapoints():
    collector = make_collector({'Datapoints': json.dumps([{'timestamp': 1, 'Average': 1.0}])})
    points = collector.query_metric('acs_global_acceleration', 'GaBaseIpOutBps', 60)
    assert points == [{'timestamp': 1, 'Average': 1.0}]
