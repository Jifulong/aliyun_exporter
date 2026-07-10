import pytest

from aliyun_exporter.utils import format_metric, format_period, expand_metric_names

def test_format_metric():
    assert format_metric("") == ""
    assert format_metric("a.b.c") == "a_b_c"
    assert format_metric("aBcD") == "aBcD"
    assert format_metric(".a.b.c.") == "_a_b_c_"


def test_format_period():
    assert format_period("") == ""
    assert format_period("3000") == "3000"
    assert format_period("5,10,25,50,100,300") == "5"
    assert format_period("300_00,500_00") == "300_00"


def test_expand_metric_names_passthrough():
    metrics = {'acs_cdn': [{'name': 'QPS', 'period': 60}]}
    assert expand_metric_names(metrics) == metrics


def test_expand_metric_names_list():
    metrics = {
        'acs_global_acceleration': [
            {'name': ['A', 'B', 'C'], 'period': 60},
        ],
    }
    expanded = expand_metric_names(metrics)
    assert expanded == {
        'acs_global_acceleration': [
            {'name': 'A', 'period': 60},
            {'name': 'B', 'period': 60},
            {'name': 'C', 'period': 60},
        ],
    }


def test_expand_metric_names_rejects_rename_with_list():
    metrics = {'acs_cdn': [{'name': ['A', 'B'], 'rename': 'x'}]}
    with pytest.raises(Exception):
        expand_metric_names(metrics)


def test_expand_metric_names_none():
    assert expand_metric_names(None) is None


def test_expand_metric_names_rejects_empty_name_in_list():
    # e.g. a stray trailing comma in `name: [A, B,]` parses as ['A', 'B', None]
    metrics = {'acs_global_acceleration': [{'name': ['A', 'B', None], 'period': 60}]}
    with pytest.raises(Exception):
        expand_metric_names(metrics)


def test_expand_metric_names_rejects_empty_scalar_name():
    metrics = {'acs_cdn': [{'name': None, 'period': 60}]}
    with pytest.raises(Exception):
        expand_metric_names(metrics)
