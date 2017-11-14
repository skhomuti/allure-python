
from allure_commons.model2 import TestResultContainer, TestResult, TestStepResult, TestAfterResult, TestBeforeResult,\
    StatusDetails
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
    LOG_MESSAGE_FORMAT = '{full_message}\n\n[{level}] {message}'

    def __init__(self, logger_path=DEFAULT_OUTPUT_PATH):
        if not os.path.exists(logger_path):
            os.makedirs(logger_path)
        self.reporter = AllureReporter()
        self.logger = AllureFileLogger(logger_path)
        self.logger_path = logger_path
        self.stack = []
        self.log_attach = {}
        self.pool_id = None
        plugin_manager.register(self.reporter)
        plugin_manager.register(self.logger)

    def start_suite(self, name, attributes):
        if not self.pool_id:
            self.pool_id = BuiltIn().get_variable_value('${PABOTEXECUTIONPOOLID}')
            if not self.pool_id:
                self.pool_id = 1
            if self.pool_id == 1:
                utils.clear_directory(self.logger_path)

        uuid = uuid4()
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
        uuid_group = uuid4()
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
        test.status = utils.get_allure_status(attributes.get('status'))
        test.labels.extend(utils.get_allure_suites(attributes.get('longname')))
        test.labels.extend(utils.get_allure_tags(attributes.get('tags')))
        test.labels.append(utils.get_allure_thread(self.pool_id))
        test.statusDetails = StatusDetails(message=attributes.get('message'))
        test.stop = now()
        self.reporter.close_test(uuid)
        self.reporter.stop_group(uuid_group, stop=now())

    def start_keyword(self, name, attributes):
        if (attributes.get('type') == RobotTestType.SETUP
            or attributes.get('type') == RobotTestType.TEARDOWN) \
                and not isinstance(self.reporter.get_item(self.stack[-1]), TestStepResult):
            self.start_fixture(name, attributes)
            return
        uuid = uuid4()
        parent_uuid = self.stack[-1]
        self.stack.append(uuid)
        step_name = '{} = {}'.format(attributes.get('assign')[0], name) if attributes.get('assign') else name
        step = TestStepResult(name=step_name,
                              description=attributes.get('doc'),
                              parameters=utils.get_allure_parameters(attributes.get('args')),
                              start=now())
        self.reporter.start_step(parent_uuid=parent_uuid, uuid=uuid, step=step)

    def end_keyword(self, name, attributes):
        if (attributes.get('type') == RobotTestType.SETUP
            or attributes.get('type') == RobotTestType.TEARDOWN) \
                and not isinstance(self.reporter.get_item(self.stack[-1]), TestStepResult):
            self.stop_fixture(name, attributes)
            return
        uuid = self.stack.pop()
        if uuid in self.log_attach:
            self.reporter.attach_data(uuid=uuid4(),
                                      body=self.log_attach.pop(uuid),
                                      name='Keyword Log',
                                      attachment_type=AttachmentType.TEXT)
        self.reporter.stop_step(uuid=uuid,
                                status=utils.get_allure_status(attributes.get('status')),
                                stop=now())

    def log_message(self, message):
        if message.get('level') == RobotLogLevel.FAIL:
            statusDetails = StatusDetails(message=message.get('message'))
            self.reporter.get_item(self.stack[-1]).statusDetails = statusDetails
        full_message = self.log_attach[self.stack[-1]] if self.stack[-1] in self.log_attach else ''
        self.log_attach[self.stack[-1]] = self.LOG_MESSAGE_FORMAT.format(full_message=full_message,
                                                                         level=message.get('level'),
                                                                         message=message.get('message').encode('UTF-8'))

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
            'parameters': utils.get_allure_parameters(attributes.get('args')),
            'start': now()
        }
        if attributes.get('type') == RobotTestType.SETUP:
            self.reporter.start_before_fixture(parent_uuid, uuid, TestBeforeResult(**args))
        elif attributes.get('type') == RobotTestType.TEARDOWN:
            self.reporter.start_after_fixture(parent_uuid, uuid, TestAfterResult(**args))

    def stop_fixture(self, name, attributes):
        uuid = self.stack.pop()
        if uuid in self.log_attach:
            self.reporter.attach_data(uuid=uuid4(),
                                      body=self.log_attach.pop(uuid),
                                      name='Keyword Log',
                                      attachment_type=AttachmentType.TEXT)
        if attributes.get('type') == RobotTestType.SETUP:
            self.reporter.stop_before_fixture(uuid,
                                              status=utils.get_allure_status(attributes.get('status')),
                                              stop=now())
        elif attributes.get('type') == RobotTestType.TEARDOWN:
            self.reporter.stop_after_fixture(uuid,
                                             status=utils.get_allure_status(attributes.get('status')),
                                             stop=now())

