### -*- coding: utf-8 -*-
###
### © 2012 Krux Digital, Inc. All rights reserved.
### Author: Paul Lathrop <paul@krux.com>
###

"""
Tests for monitorlib.cloudkick
"""


from operator import itemgetter

import nose.tools as test

import monitorlib.cloudkick as ck


test.neq_ = test.assert_not_equal
INVALID = ['invalid', 'wont work', 10, iter('foo')]
STATUS_CASES = ['status ok this is a valid ok status line',
                'status warn this is a valid warning status line',
                'status err this is a valid error status line',
                'status foo this is a valid status line with an invalid status type',
                'broken this is not a valid status line'
                'status tooshort']
STATUS_EXCEPTIONS = [(1000, AttributeError),
                     (iter('foo'), AttributeError)]
METRIC_CASES = ['metric one int 1',
                'metric two string tea for two and two for tea',
                'this one does not start with the word metric',
                'metric broken invalid the metric type is invalid']
METRIC_EXCEPTIONS = [('metric tooshort', IndexError),
                     (1000, AttributeError),
                     (iter('foo'), AttributeError)]


def check_status(key):
    assert ck.valid_status_type(key)


def check_invalid_status(status):
    test.assert_false(ck.valid_status_type(status))


def test_valid_status_type():
    for key in ck.STATUS_PRIORITY.iterkeys():
        yield check_status, key
    for status in INVALID:
        yield check_invalid_status, status


def check_valid_metric_type(metric_type):
    assert ck.valid_metric_type(metric_type)


def check_invalid_metric_type(metric_type):
    test.assert_false(ck.valid_metric_type(metric_type))


def test_valid_metric_type():
    for metric_type in ck.VALID_METRICS:
        yield check_valid_metric_type, metric_type
    for metric_type in INVALID:
        yield check_invalid_metric_type, metric_type


def test_priority():
    for status in ck.STATUS_PRIORITY.iterkeys():
        assert ck.priority(status) == ck.STATUS_PRIORITY[status]
    for status in INVALID:
        test.assert_false(ck.priority(status))


def test_compare_priority():
    data = [s[0] for s in sorted(ck.STATUS_PRIORITY.iteritems(), key=itemgetter(1))]
    for priority in data:
        for lesser in data[:data.index(priority)]:
            test.eq_(ck.compare_priority(lesser, priority), -1)
            test.neq_(ck.compare_priority(lesser, priority), 0)
            test.neq_(ck.compare_priority(priority, lesser), 0)
            test.eq_(ck.compare_priority(priority, lesser), 1)
        test.eq_(ck.compare_priority(priority, priority), 0)
        for greater in data[(data.index(priority) + 1):]:
            test.eq_(ck.compare_priority(priority, greater), -1)
            test.neq_(ck.compare_priority(priority, greater), 0)
            test.neq_(ck.compare_priority(greater, priority), 0)
            test.eq_(ck.compare_priority(greater, priority), 1)


def test_get_field():
    test.eq_(ck.get_field(0, 'test 1', ck.STATUS_FIELD_COUNT), 'test')
    test.assert_raises(IndexError, ck.get_field, 2, 'test 2', ck.STATUS_FIELD_COUNT)
    test.assert_raises(AttributeError, ck.get_field, 1, 1000, ck.STATUS_FIELD_COUNT)
    test.assert_raises(AttributeError, ck.get_field, 1, iter('foo'), ck.STATUS_FIELD_COUNT)


def test_is_status_line():
    results = [True, True, True, False, False, False]
    for line, expected in zip(STATUS_CASES, results):
        test.eq_(ck.is_status_line(line), expected)
    for line, exc in STATUS_EXCEPTIONS:
        test.assert_raises(exc, ck.is_status_line, line)


def test_is_metric_line():
    results = [True, True, False, False]
    for line, expected in zip(METRIC_CASES, results):
        test.eq_(ck.is_metric_line(line), expected)
    for line, exc in METRIC_EXCEPTIONS:
        test.assert_raises(exc, ck.is_metric_line, line)


def test_get_status_type():
    results = ['ok', 'warn', 'err', False, False, False]
    for line, expected in zip(STATUS_CASES, results):
        test.eq_(ck.get_status_type(line), expected)
    for line, exc in STATUS_EXCEPTIONS:
        test.assert_raises(exc, ck.get_status_type, line)


def test_get_metric_type():
    results = ['int', 'string', False, False]
    for line, expected in zip(METRIC_CASES, results):
        test.eq_(ck.get_metric_type(line), expected)
    for line, exc in METRIC_EXCEPTIONS:
        test.assert_raises(exc, ck.get_metric_type, line)


def test_status_tuple():
    results = [('status', 'ok', 'this is a valid ok status line'),
               ('status', 'warn', 'this is a valid warning status line'),
               ('status', 'err', 'this is a valid error status line'),
               False, False, False]
    for line, expected in zip(STATUS_CASES, results):
        test.eq_(ck.status_tuple(line), expected)
    for line, exc in STATUS_EXCEPTIONS:
        test.assert_raises(exc, ck.status_tuple, line)


def test_status_line():
    ### At this point we've tested status_tuple() and
    ### is_status_line(), so we can use them.
    results = zip([ck.status_tuple(line) for line in STATUS_CASES
                   if ck.is_status_line(line)],
                  [line for line in STATUS_CASES
                   if ck.is_status_line(line)])
    for tpl, line in results:
        test.eq_(ck.status_line(tpl), line)


def test_ok():
    msg = 'Everything is okay.'
    test.eq_(ck.ok(msg), "status ok %s" % msg)


def test_warn():
    msg = 'Everything is warning.'
    test.eq_(ck.warn(msg), "status warn %s" % msg)


def test_err():
    msg = 'Everything is an error.'
    test.eq_(ck.err(msg), "status err %s" % msg)


def test_metric_tuple():
    results = [('metric', 'one', 'int', '1'),
               ('metric', 'two', 'string', 'tea for two and two for tea'),
               False, False]
    for line, expected in zip(METRIC_CASES, results):
        test.eq_(ck.metric_tuple(line), expected)
    for line, exc in METRIC_EXCEPTIONS:
        test.assert_raises(exc, ck.metric_tuple, line)


def test_metric_line():
    ### At this point we've tested metric_tuple() and
    ### is_metric_line(), so we can use them.
    results = zip([ck.metric_tuple(line) for line in METRIC_CASES
                   if ck.is_metric_line(line)],
                  [line for line in METRIC_CASES
                   if ck.is_metric_line(line)])
    for tpl, line in results:
        test.eq_(ck.metric_line(tpl), line)


def test_get_status_lines():
    ### At this point we've tested is_status_line() so we can use it.
    assert all([ck.is_status_line(line) for line in
                ck.get_status_lines(STATUS_CASES)])


def test_get_metric_lines():
    ### At this point we've tested is_metric_line() so we can use it.
    assert all([ck.is_metric_line(line) for line in
                ck.get_metric_lines(METRIC_CASES)])


def test_sort_by_priority():
    ### At this point we've tested get_status_type() so we can use it.
    test.eq_(ck.get_status_type(ck.sort_by_priority(STATUS_CASES)[0]), 'err')


def test_highest_priority():
    ### At this point we've tested get_status_type() so we can use it.
    test.eq_(ck.get_status_type(ck.highest_priority(STATUS_CASES)), 'err')
