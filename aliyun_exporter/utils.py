def format_metric(text: str):
    return text.replace('.', '_')


def format_period(text: str):
    return text.split(',', 1)[0]


def try_or_else(op, default):
    try:
        return op()
    except:
        return default


def expand_metric_names(metrics):
    '''
    Allow a metric item's `name` to be a list (e.g. `name: [A, B, C]`) as a
    shorthand for repeating the same period/measure config across several
    metrics. Expands each such item into one item per name.
    '''
    if not metrics:
        return metrics
    expanded = {}
    for project, items in metrics.items():
        new_items = []
        for item in items or []:
            name = item.get('name')
            if isinstance(name, list):
                if 'rename' in item:
                    raise Exception(
                        "'rename' cannot be used together with a list of metric names "
                        "in project '{}'".format(project))
                for single_name in name:
                    if not single_name:
                        raise Exception(
                            "Empty metric name found in project '{}' (check for a stray "
                            "or trailing comma in the `name` list).".format(project))
                    new_item = dict(item)
                    new_item['name'] = single_name
                    new_items.append(new_item)
            else:
                if not name:
                    raise Exception("'name' must be a non-empty string in project '{}'.".format(project))
                new_items.append(item)
        expanded[project] = new_items
    return expanded

