### -*- coding: utf-8 -*-
###
### © 2012 Krux Digital, Inc. All rights reserved.
### Author: Paul Lathrop <paul@krux.com>
###

"""
Functions for creating Cloudkick plugins.
"""


from operator import itemgetter


### A dictionary of status => priority pairs. The keys define the
### valid statuses for cloudkick, the values are the relative priority
### of status lines with that status. See highest_priority()
STATUS_PRIORITY = {'ok': 0, 'warn': 1, 'err': 2}

### List of valid metric types. See
### https://support.cloudkick.com/Creating_a_Plugin
VALID_METRICS = ['int', 'float', 'gauge', 'string']

### Number of fields in a status line.
STATUS_FIELD_COUNT = 3

### Index of the status type field in a status line (0-indexed).
STATUS_TYPE_FIELD = 1

### Number of fields in a metric line.
METRIC_FIELD_COUNT = 4

### Index of the metric type field in a metric line (0-indexed).
METRIC_TYPE_FIELD = 2


def valid_status_type(status):
    """
    Return True if status is a valid Cloudkick status.
    """
    return status in STATUS_PRIORITY.iterkeys()


def valid_metric_type(metric_type):
    """
    Return True if line specifies a valid Cloudkick metric type.
    """
    return metric_type in VALID_METRICS


def priority(status):
    """
    Given a valid status, return the priority of that status.
    """
    return valid_status_type(status) and STATUS_PRIORITY[status]


def compare_priority(pri_a, pri_b):
    """
    Given two statuses:

    * Return -1 if the priority of pri_a is less than that of pri_b.

    * Return 0 if the priorities of the two statuses are equal.

    * Return 1 if the priority of pri_a is greater than that of pri_b.
    """
    if priority(pri_a) < priority(pri_b):
        return -1
    if priority(pri_a) == priority(pri_b):
        return 0
    return 1


def get_field(field, line, splits):
    """
    Given a field index, a whitespace-separated record line, and the
    number of splits to make, return the given field of the record
    (0-indexed).
    """
    return line.split(None, splits)[field]


def is_status_line(line):
    """
    Given an output line, return True if it is a Cloudkick-formatted
    status line, False otherwise.
    """
    return all([line.startswith('status '),
                valid_status_type(get_field(STATUS_TYPE_FIELD,
                                            line,
                                            STATUS_FIELD_COUNT))])


def is_metric_line(line):
    """
    Given an output line, return True if it is a Cloudkick-formatted
    metric line, False otherwise.
    """
    return all([line.startswith('metric '),
                valid_metric_type(get_field(METRIC_TYPE_FIELD,
                                            line,
                                            METRIC_FIELD_COUNT))])


def get_status_type(line):
    """
    Given a Cloudkick-formatted status line, return the status type
    specified by that line. Return False if line is not a
    Cloudkick-formatted status line.
    """
    return is_status_line(line) and get_field(STATUS_TYPE_FIELD,
                                              line,
                                              STATUS_FIELD_COUNT)


def get_metric_type(line):
    """
    Given a Cloudkick-formatted metric line, return the metric type
    specified by that line. Return False if line is not a
    Cloudkick-formatted metric line.
    """
    return is_metric_line(line) and get_field(METRIC_TYPE_FIELD,
                                              line,
                                              METRIC_FIELD_COUNT)


def status_tuple(line):
    """
    Given a Cloudkick-formatted status line, return a tuple ('status',
    status, message).
    """
    return is_status_line(line) and tuple(line.split(None, (STATUS_FIELD_COUNT - 1)))


def status_line(tpl):
    """
    Given a tuple of the form ('status', status, message), return a
    Cloudkick-formatted status line.
    """
    line = ' '.join(tpl)
    return is_status_line(line) and line


def ok(message):
    """
    Given a message, return a status line representing an 'ok'
    status with that message.
    """
    return status_line(('status', 'ok', message))


def warn(message):
    """
    Given a message, return a status line representing an 'warn'
    status with that message.
    """
    return status_line(('status', 'warn', message))


def err(message):
    """
    Given a message, return a status line representing an 'err'
    status with that message.
    """
    return status_line(('status', 'err', message))


def metric_tuple(line):
    """
    Given a Cloudkick-formatted metric line, return a tuple ('metric',
    name, type, value).
    """
    return is_metric_line(line) and tuple(line.split(None, (METRIC_FIELD_COUNT - 1)))


def metric_line(tpl):
    """
    Given a tuple of the form ('metric', name, type, value), return a
    Cloudkick-formatted metric line.
    """
    line = ' '.join(tpl)
    return is_metric_line(line) and line


def get_status_lines(output_lines):
    """
    Given a list of output lines, return a list containing only the
    status line(s).
    """
    return [l for l in output_lines if is_status_line(l)]


def get_metric_lines(output_lines):
    """
    Given a list of output lines, return a list containing only the
    metric lines(s).
    """
    return [l for l in output_lines if is_metric_line(l)]


def sort_by_priority(lines):
    """
    Given a list of status lines, return them sorted by descending
    priority. If any line in lines is not a status line, it will be
    filtered out of the results.
    """
    return list(reversed([status_line(tpl) for tpl in
                          sorted([status_tuple(line) for line in
                                  get_status_lines(lines)],
                                 cmp=compare_priority,
                                 key=itemgetter(1))]))


def highest_priority(lines):
    """
    Given a list of lines, return the status line with the highest
    priority.
    """
    return sort_by_priority(get_status_lines(lines))[0]


def add_lines(lines, output_lines):
    """
    Adds new lines to a list of output lines. For each new status
    line, add the line if its priority is greater than all existing
    status lines. For each new metric line, add the line. Ignore any
    other line.
    """
    status = highest_priority([line for line in (lines + output_lines)
                               if is_status_line(line)])
    return [status] + [line for line in (lines + output_lines)
                       if is_metric_line(line)]


if __name__ == '__main__':
    import nose
    nose.main()
