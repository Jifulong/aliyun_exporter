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


def test_metric_generator_skips_points_missing_measure():
    # A metric that only reports some statistics (e.g. no 'Average') for some
    # points must not crash the whole collector; it should just skip that point.
    collector = make_collector({})
    collector.query_metric = lambda project, metric, period: [
        {'timestamp': 1, 'InstanceId': 'a'},
        {'timestamp': 2, 'InstanceId': 'b', 'Average': 5.0},
    ]
    results = list(collector.metric_generator('acs_global_acceleration', {'name': 'GaBaseIpOutBps'}))
    up_metrics = [r for r in results if r.name.endswith('_up')]
    gauges = [r for r in results if not r.name.endswith('_up')]
    assert len(up_metrics) == 1
    assert up_metrics[0].samples[0].value == 1.0
    assert len(gauges) == 1
    assert len(gauges[0].samples) == 1


def test_metric_generator_all_points_missing_measure_marks_down():
    collector = make_collector({})
    collector.query_metric = lambda project, metric, period: [
        {'timestamp': 1, 'InstanceId': 'a'},
    ]
    results = list(collector.metric_generator('acs_global_acceleration', {'name': 'GaBaseIpOutBps'}))
    assert len(results) == 1
    assert results[0].name.endswith('_up')
    assert results[0].samples[0].value == 0.0
