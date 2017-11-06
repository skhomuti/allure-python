
from allure_commons.model2 import TestResultContainer, TestResult, TestStepResult, Status, Parameter
from allure_commons.reporter import AllureReporter
from allure_commons.utils import now, uuid4
from allure_commons.logger import AllureFileLogger
from allure_commons import plugin_manager
from robot.libraries.BuiltIn import BuiltIn
import utils

class AllureListener(object):

    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, logger_path='output\\allure'):
        utils.clear_directory(logger_path)
        self.reporter = AllureReporter()
        self.logger = AllureFileLogger(logger_path)
        self.executable_stack = []
        plugin_manager.register(self.reporter)
        plugin_manager.register(self.logger)

    def start_suite(self, name, attributes):
        uuid = self._get_uuid(attributes.get('id'))
        parent_suite = self.reporter.get_item(uuid=self._get_parent_uuid(uuid))
        if parent_suite and not parent_suite.stop:
            parent_suite.children.append(uuid)
        suite = TestResultContainer(uuid=uuid,
                                    name=name,
                                    description=attributes.get('doc'),
                                    descriptionHtml=attributes.get('doc'),
                                    start=now())
        self.reporter.start_group(uuid, suite)

    def end_suite(self, name, attributes):
        uuid = self._get_uuid(attributes.get('id'))
        self.reporter.stop_group(uuid, stop=now())

    def start_test(self, name, attributes):
        uuid = self._get_uuid(attributes.get('id'))
        self.executable_stack.append(uuid)
        parent_suite = self.reporter.get_item(self._get_parent_uuid(uuid))
        parent_suite.children.append(uuid)
        test_case = TestResult(uuid=uuid,
                               name=name,
                               description=attributes.get('doc'))
        self.reporter.schedule_test(uuid, test_case)

    def end_test(self, name, attributes):
        uuid = self.executable_stack.pop()
        test = self.reporter.get_test(uuid)
        test.status = self._get_allure_status(attributes.get('status'))
        self.reporter.close_test(uuid)

    def start_keyword(self, name, attributes):
        uuid = uuid4()
        parent_uuid = self.executable_stack[-1]
        self.executable_stack.append(uuid)
        step = TestStepResult(id=attributes.get('id'),
                              name=name,
                              description=attributes.get('doc'),
                              parameters=self._get_allure_parameters(attributes.get('args')),
                              start=now())
        self.reporter.start_step(parent_uuid=parent_uuid, uuid=uuid, step=step)

    def end_keyword(self, name, attributes):
        uuid = self.executable_stack.pop()
        self.reporter.stop_step(uuid=uuid,
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
        return Status.PASSED if status == 'PASS' else Status.FAILED

    def _get_allure_parameters(self, parameters):
        return [Parameter(name="arg{}".format(i + 1), value=param) for i, param in enumerate(parameters)]
