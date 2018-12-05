from __future__ import absolute_import
from allure_commons.model2 import Status, Label, Parameter
from allure_commons.types import LabelType
from allure_robotframework.types import RobotStatus
from robot.libraries.BuiltIn import BuiltIn
from robot.running.arguments import PythonArgumentParser
from robot.running.arguments.argumentmapper import DefaultValue

import inspect


def get_allure_status(status):
    return Status.PASSED if status == RobotStatus.PASSED else Status.FAILED


def get_allure_parameters(parameters, name):
    library, keyword_name = name.split('.', maxsplit=1)
    keyword_name = keyword_name.lower().replace(' ', '_')
    keyword = _get_keyword_by_name(library, keyword_name)
    params = _parse_keyword_params(keyword, parameters)
    return [Parameter(name=name, value=value) for name, value in params.items()]


def _get_keyword_by_name(library, keyword_name):
    members = inspect.getmembers(BuiltIn().get_library_instance(library), lambda x: all((
        inspect.ismethod(x), inspect.isbuiltin(x) is False)))
    for member_name, member in members:
        if member_name == keyword_name:
            return member


def _parse_keyword_params(keyword, params):
    parse = PythonArgumentParser().parse(keyword)
    position, named = parse.map(*parse.resolve(params), replace_defaults=False)
    params_dict = {}
    for key, value in zip(parse.positional, position):
        params_dict[key] = value.value if isinstance(value, DefaultValue) else value
    return params_dict


def get_allure_suites(longname):
    """
    >>> get_allure_suites('Suite1.Test')
    [Label(name=<LabelType.SUITE: 'suite'>, value='Suite1')]
    >>> get_allure_suites('Suite1.Suite2.Test') # doctest: +NORMALIZE_WHITESPACE
    [Label(name=<LabelType.SUITE: 'suite'>, value='Suite1'),
    Label(name=<LabelType.SUB_SUITE: 'subSuite'>, value='Suite2')]
    >>> get_allure_suites('Suite1.Suite2.Suite3.Test') # doctest: +NORMALIZE_WHITESPACE
    [Label(name=<LabelType.PARENT_SUITE: 'parentSuite'>, value='Suite1'),
    Label(name=<LabelType.SUITE: 'suite'>, value='Suite2'),
    Label(name=<LabelType.SUB_SUITE: 'subSuite'>, value='Suite3')]
    """
    labels = []
    suites = longname.split('.')
    if len(suites) > 3:
        labels.append(Label(LabelType.PARENT_SUITE, suites.pop(0)))
    labels.append(Label(LabelType.SUITE, suites.pop(0)))
    if len(suites) > 1:
        labels.append(Label(LabelType.SUB_SUITE, '.'.join(suites[:-1])))
    return labels


def allure_tags(attributes):
    return [Label(LabelType.TAG, tag) for tag in attributes.get('tags', ())]


def allure_labels(attributes, prefix):
    tags = attributes.get('tags', ())

    def is_label(label):
        return label.startswith("{label}:".format(label=prefix))

    def label_value(label):
        return label.split(':')[1] or 'unknown'

    return [Label(name=prefix, value=label_value(tag)) for tag in tags if is_label(tag)]
