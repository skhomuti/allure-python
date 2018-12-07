from __future__ import absolute_import
from allure_commons.model2 import Status, Label, Parameter
from allure_commons.types import LabelType
from allure_commons.utils import func_parameters, func_argspec
from allure_robotframework.types import RobotStatus
from robot.libraries.BuiltIn import BuiltIn
from robot.running.arguments import PythonArgumentParser
from robot.running.arguments.argumentmapper import DefaultValue
from robot.running.context import EXECUTION_CONTEXTS
import inspect
from itertools import chain


def get_allure_status(status):
    return Status.PASSED if status == RobotStatus.PASSED else Status.FAILED


def get_allure_parameters(parameters, name):
    library, keyword_name = name.split('.', maxsplit=1) if '.' in name else (None, name)
    if name == 'BuiltIn.Wait Until Keyword Succeeds':
        return []
    if _is_resource(library):
        params = _get_keyword_params_by_resource(library, keyword_name, parameters)
    else:
        params = _get_keyword_params_by_library(library, keyword_name, parameters)
    if params:
        return [Parameter(name=name, value=value) for name, value in params.items()]
    return []


def _get_keyword_params_by_resource(library, keyword_name, parameters):
    kw_store = EXECUTION_CONTEXTS.current.namespace._kw_store
    for lib in chain(kw_store.resources.values(), (kw_store.user_keywords,)):
        for handler in lib.handlers:
            if handler.name == keyword_name and (handler.libname == library or library is None):
                args = handler.arguments
                args.args = args.positional
                position, named = args.map(*args.resolve(parameters), replace_defaults=False)
                return func_argspec(args, *position, **dict(named))


def _get_keyword_params_by_library(library, keyword_name, parameters):
    keyword = _get_keyword_by_name(library, keyword_name)
    if keyword:
        return _parse_keyword_params(keyword, parameters)


def _is_resource(library):
    if library is None or library not in BuiltIn().get_library_instance(all=True):
        return True
    return False


def _get_keyword_by_name(library, keyword_name):
    keyword_name = keyword_name.lower().replace(' ', '_')
    members = inspect.getmembers(BuiltIn().get_library_instance(library), lambda x: all((
        inspect.isroutine(x), inspect.isbuiltin(x) is False)))
    for member_name, member in members:
        if member_name == keyword_name:
            return member
    return None


def _parse_keyword_params(keyword, params):
    parse = PythonArgumentParser().parse(keyword)
    position, named = parse.map(*parse.resolve(params), replace_defaults=False)
    position = list(map(lambda x: x.value if isinstance(x, DefaultValue) else x, position))
    if inspect.isfunction(keyword):
        return func_parameters(keyword, *position, **dict(named))
    else:
        return func_parameters(keyword, None, *position, **dict(named))


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
