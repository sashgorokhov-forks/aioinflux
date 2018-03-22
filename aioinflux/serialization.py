import warnings
from collections import defaultdict
from typing import Iterable, Mapping, Union, Dict


# Special characters documentation:
# https://docs.influxdata.com/influxdb/v1.4/write_protocols/line_protocol_reference/#special-characters
# Although not in the official docs, new line characters are removed in order to avoid issues.
key_escape = str.maketrans({',': r'\,', ' ': r'\ ', '=': r'\=', '\n': ''})
tag_escape = str.maketrans({',': r'\,', ' ': r'\ ', '=': r'\=', '\n': ''})
str_escape = str.maketrans({'"': r'\"', '\n': ''})
measurement_escape = str.maketrans({',': r'\,', ' ': r'\ ', '\n': ''})


def escape(string, escape_pattern):
    """Assistant function for string escaping"""
    try:
        return string.translate(escape_pattern)
    except AttributeError:
        warnings.warn("Non-string-like data passed. "
                      "Attempting to convert to 'str'.")
        return str(string).translate(tag_escape)


def parse_data(data, measurement=None, tag_columns=None, **extra_tags):
    """Converts input data into line protocol format"""
    if isinstance(data, bytes):
        return data
    elif isinstance(data, str):
        return data.encode('utf-8')
    elif isinstance(data, Mapping):
        return make_line(data, measurement, **extra_tags)
    elif isinstance(data, Iterable):
        return b'\n'.join([parse_data(i, measurement, tag_columns, **extra_tags) for i in data])
    else:
        raise ValueError('Invalid input', data)


def make_line(point: Mapping, measurement=None, **extra_tags):
    """Converts dictionary-like data into a single line protocol line (point)"""
    p = dict(measurement=_parse_measurement(point, measurement),
             tags=_parse_tags(point, extra_tags),
             fields=_parse_fields(point),
             timestamp=_parse_timestamp(point))
    if p['tags']:
        line = '{measurement},{tags} {fields} {timestamp}'.format(**p)
    else:
        line = '{measurement} {fields} {timestamp}'.format(**p)
    return line.encode('utf-8')


def _parse_measurement(point, measurement):
    try:
        return escape(point['measurement'], measurement_escape)
    except KeyError:
        if measurement is None:
            raise ValueError("'measurement' missing")
        return escape(measurement, measurement_escape)


def _parse_tags(point, extra_tags):
    output = []
    try:
        for k, v in {**point['tags'], **extra_tags}.items():
            k = escape(k, key_escape)
            v = escape(v, tag_escape)
            if not v:
                continue  # ignore blank/null string tags
            output.append('{k}={v}'.format(k=k, v=v))
    except KeyError:
        pass
    if output:
        return ','.join(output)
    else:
        return ''


def _parse_timestamp(point):
    if 'time' not in point:
        return ''
    else:
        return point['time']


def _parse_fields(point):
    output = []
    for k, v in point['fields'].items():
        k = escape(k, key_escape)
        # noinspection PyUnresolvedReferences
        if isinstance(v, bool):
            output.append('{k}={v}'.format(k=k, v=str(v).upper()))
        elif isinstance(v, int):
            output.append('{k}={v}i'.format(k=k, v=v))
        elif isinstance(v, str):
            output.append('{k}="{v}"'.format(k=k, v=v.translate(str_escape)))
        elif v is None:
            continue
        else:
            # Floats and other numerical formats go here.
            # TODO: Add unit test
            output.append('{k}={v}'.format(k=k, v=v))
    return ','.join(output)
