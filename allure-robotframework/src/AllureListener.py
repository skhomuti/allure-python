
from allure_commons.model2 import TestResultContainer, TestResult, TestStepResult, TestAfterResult, TestBeforeResult,\
    Status, Parameter, Label
from allure_commons.reporter import AllureReporter
from allure_commons.utils import now, uuid4
from allure_commons.logger import AllureFileLogger
from allure_commons.types import AttachmentType
from allure_commons import plugin_manager
from robot.libraries.BuiltIn import BuiltIn
from constants import *
import utils
import os


class AllureListener(object):

    ROBOT_LISTENER_API_VERSION = 2
    DEFAULT_OUTPUT_PATH = os.path.join('output', 'allure')

    def __init__(self, logger_path=DEFAULT_OUTPUT_PATH):
        if not os.path.exists(logger_path):
            os.makedirs(logger_path)
        utils.clear_directory(logger_path)
        self.reporter = AllureReporter()
        self.logger = AllureFileLogger(logger_path)
        self.stack = []
        self.current_log_attach = ''
        plugin_manager.register(self.reporter)
        plugin_manager.register(self.logger)

    def start_suite(self, name, attributes):
        uuid = self._get_uuid(attributes.get('id'))
        if self.stack:
            parent_suite = self.reporter.get_item(self.stack[-1])
            parent_suite.children.append(uuid)
        self.stack.append(uuid)
        suite = TestResultContainer(uuid=uuid,
                                    name=name,
                                    description=attributes.get('doc'),
                                    descriptionHtml=attributes.get('doc'),
                                    start=now())
        self.reporter.start_group(uuid, suite)

    def end_suite(self, name, attributes):
        uuid = self.stack.pop()
        self.reporter.stop_group(uuid, stop=now())

    def start_test(self, name, attributes):
        uuid_group = self._get_uuid(attributes.get('id'))
        uuid = uuid4()
        args = {
            'name': name,
            'description': attributes.get('doc'),
            'start': now()
        }
        parent_suite = self.reporter.get_item(self.stack[-1])
        parent_suite.children.append(uuid_group)
        test_group = TestResultContainer(uuid=uuid_group, **args)
        self.stack.extend([uuid_group, uuid])
        test_group.children.append(uuid)
        test_case = TestResult(uuid=uuid, **args)
        self.reporter.start_group(uuid_group, test_group)
        self.reporter.schedule_test(uuid, test_case)

    def end_test(self, name, attributes):
        uuid = self.stack.pop()
        uuid_group = self.stack.pop()
        test = self.reporter.get_test(uuid)
        test.status = self._get_allure_status(attributes.get('status'))
        test.labels.extend(self._get_allure_suites(attributes.get('longname')))
        test.labels.extend(self._get_allure_tags(attributes.get('tags')))
        test.stop = now()
        self.reporter.close_test(uuid)
        self.reporter.stop_group(uuid_group, stop=now())

    def start_keyword(self, name, attributes):
        if attributes.get('type') == RobotTestType.SETUP or attributes.get('type') == RobotTestType.TEARDOWN:
            self.start_fixture(name, attributes)
            return
        uuid = uuid4()
        parent_uuid = self.stack[-1]
        self.stack.append(uuid)
        if attributes.get('assign'):
            name = attributes.get('assign')[0] + ' = ' + name
        step = TestStepResult(id=attributes.get('id'),
                              name=name,
                              description=attributes.get('doc'),
                              parameters=self._get_allure_parameters(attributes.get('args')),
                              start=now())
        self.reporter.start_step(parent_uuid=parent_uuid, uuid=uuid, step=step)

    def end_keyword(self, name, attributes):
        if attributes.get('type') == RobotTestType.SETUP or attributes.get('type') == RobotTestType.TEARDOWN:
            self.stop_fixture(name, attributes)
            return
        uuid = self.stack.pop()
        if self.current_log_attach:
            self.reporter.attach_data(uuid4(), self.current_log_attach, name='log', attachment_type=AttachmentType.TEXT)
            self.current_log_attach = ''
        self.reporter.stop_step(uuid=uuid,
                                status=self._get_allure_status(attributes.get('status')),
                                stop=now())

    def log_message(self, message):
        self.current_log_attach += '[{}] {} \n\n'.format(message.get('level'), message.get('message'))

    def start_fixture(self, name, attributes):
        uuid = uuid4()
        if isinstance(self.reporter.get_item(self.stack[-1]), TestResult):
            parent_uuid = self.stack[-2]
        else:
            parent_uuid = self.stack[-1]
        self.stack.append(uuid)
        args = {
            'name': name,
            'description': attributes.get('doc'),
            'parameters': self._get_allure_parameters(attributes.get('args')),
            'start': now()
        }
        if attributes.get('type') == RobotTestType.SETUP:
            self.reporter.start_before_fixture(parent_uuid, uuid, TestBeforeResult(**args))
        elif attributes.get('type') == RobotTestType.TEARDOWN:
            self.reporter.start_after_fixture(parent_uuid, uuid, TestAfterResult(**args))

    def stop_fixture(self, name, attributes):
        uuid = self.stack.pop()
        if self.current_log_attach:
            self.reporter.attach_data(uuid4(), self.current_log_attach, name='log', attachment_type=AttachmentType.TEXT)
        if attributes.get('type') == RobotTestType.SETUP:
            self.reporter.stop_before_fixture(uuid,
                                              status=self._get_allure_status(attributes.get('status')),
                                              stop=now())
        elif attributes.get('type') == RobotTestType.TEARDOWN:
            self.reporter.stop_after_fixture(uuid,
                                             status=self._get_allure_status(attributes.get('status')),
                                             stop=now())

    def _get_uuid(self, test_id):
        pool_id = BuiltIn().get_variable_value('${PABOTEXECUTIONPOOLID}')
        if pool_id:
            return '{pool_id}-{test_id}'.format(pool_id=pool_id, test_id=test_id)
        else:
            return test_id

    def _get_parent_uuid(self, uuid):
        return uuid.rsplit('-', 1)[0]

    def _get_allure_status(self, status):
        return Status.PASSED if status == RobotStatus.PASSED else Status.FAILED

    def _get_allure_parameters(self, parameters):
        return [Parameter(name="arg{}".format(i + 1), value=param) for i, param in enumerate(parameters)]

    def _get_allure_suites(self, longname):
        labels = []
        suites = longname.split('.')
        if len(suites) > 3:
            labels.append(Label('parentSuite', suites.pop(0)))
        labels.extend([Label('suite', suites.pop(0)),
                       Label('subSuite', '.'.join(suites[:-1]))])
        return labels

    def _get_allure_tags(self, tags):
        return [Label('tag', tag) for tag in tags]
