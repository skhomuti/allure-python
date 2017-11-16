
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
from robot.api import logger

class AllureListener(object):

    ROBOT_LISTENER_API_VERSION = 2
    DEFAULT_OUTPUT_PATH = os.path.join('output', 'allure')
    LOG_MESSAGE_FORMAT = '{full_message}\n\n[{level}] {message}'

    def __init__(self, logger_path=DEFAULT_OUTPUT_PATH):
        self.reporter = AllureReporter()
        self.logger = AllureFileLogger(logger_path)
        self.stack = []
        self.items_log = {}
        self.pool_id = None
        utils.prepare_log_directory(logger_path)
        plugin_manager.register(self.reporter)
        plugin_manager.register(self.logger)

    def start_suite(self, name, attributes):
        if not self.pool_id:
            self.pool_id = BuiltIn().get_variable_value('${PABOTEXECUTIONPOOLID}')
            self.pool_id = int(self.pool_id) if self.pool_id else 0
        self.start_new_group(name, attributes)

    def end_suite(self, name, attributes):
        self.stop_current_group()

    def start_test(self, name, attributes):
        self.start_new_group(name, attributes)
        self.start_new_test(name, attributes)

    def end_test(self, name, attributes):
        self.stop_current_test(name, attributes)
        self.stop_current_group()

    def start_keyword(self, name, attributes):
        self.start_new_keyword(name, attributes)

    def end_keyword(self, name, attributes):
        self.end_current_keyword(name, attributes)

    def log_message(self, message):
        if message.get('level') == RobotLogLevel.FAIL:
            self.reporter.get_item(self.stack[-1]).statusDetails = StatusDetails(message=message.get('message'))
        self.append_message_to_last_item_log(message)

    def start_new_group(self, name, attributes):
        uuid = uuid4()
        if self.stack:
            parent_suite = self.reporter.get_item(self.stack[-1])
            parent_suite.children.append(uuid)
        self.stack.append(uuid)
        suite = TestResultContainer(uuid=uuid,
                                    name=name,
                                    description=attributes.get('doc'),
                                    start=now())
        self.reporter.start_group(uuid, suite)

    def stop_current_group(self):
        uuid = self.stack.pop()
        self.reporter.stop_group(uuid, stop=now())

    def start_new_test(self, name, attributes):
        uuid = uuid4()
        self.reporter.get_item(self.stack[-1]).children.append(uuid)
        self.stack.append(uuid)
        test_case = TestResult(uuid=uuid,
                               name=name,
                               description=attributes.get('doc'),
                               start=now())
        self.reporter.schedule_test(uuid, test_case)

    def stop_current_test(self, name, attributes):
        uuid = self.stack.pop()
        test = self.reporter.get_test(uuid)
        test.status = utils.get_allure_status(attributes.get('status'))
        test.labels.extend(utils.get_allure_suites(attributes.get('longname')))
        test.labels.extend(utils.get_allure_tags(attributes.get('tags')))
        test.labels.append(utils.get_allure_thread(self.pool_id))
        test.statusDetails = StatusDetails(message=attributes.get('message'))
        test.stop = now()
        self.reporter.close_test(uuid)

    def start_new_keyword(self, name, attributes):
        uuid = uuid4()
        parent_uuid = self.stack[-1]
        step_name = '{} = {}'.format(attributes.get('assign')[0], name) if attributes.get('assign') else name
        args = {
            'name': step_name,
            'description': attributes.get('doc'),
            'parameters': utils.get_allure_parameters(attributes.get('args')),
            'start': now()
        }
        keyword_type = attributes.get('type')
        last_item = self.reporter.get_item(self.stack[-1])
        if keyword_type in RobotKeywordType.FIXTURES and not isinstance(last_item, TestStepResult):
            if isinstance(last_item, TestResult):
                parent_uuid = self.stack[-2]
            if keyword_type == RobotKeywordType.SETUP:
                self.reporter.start_before_fixture(parent_uuid, uuid, TestBeforeResult(**args))
            elif keyword_type == RobotKeywordType.TEARDOWN:
                self.reporter.start_after_fixture(parent_uuid, uuid, TestAfterResult(**args))
            self.stack.append(uuid)
            return
        self.stack.append(uuid)
        self.reporter.start_step(parent_uuid=parent_uuid,
                                 uuid=uuid,
                                 step=TestStepResult(**args))

    def end_current_keyword(self, name, attributes):
        uuid = self.stack.pop()
        if uuid in self.items_log:
            self.reporter.attach_data(uuid=uuid4(),
                                      body=self.items_log.pop(uuid),
                                      name='Keyword Log',
                                      attachment_type=AttachmentType.TEXT)
        args = {
            'uuid': uuid,
            'status': utils.get_allure_status(attributes.get('status')),
            'stop': now()
        }
        keyword_type = attributes.get('type')
        parent_item = self.reporter.get_item(self.stack[-1])
        if keyword_type in RobotKeywordType.FIXTURES and not isinstance(parent_item, TestStepResult):
            if keyword_type == RobotKeywordType.SETUP:
                self.reporter.stop_before_fixture(**args)
                return
            elif keyword_type == RobotKeywordType.TEARDOWN:
                self.reporter.stop_after_fixture(**args)
                return
        self.reporter.stop_step(**args)

    def append_message_to_last_item_log(self, message):
        full_message = self.items_log[self.stack[-1]] if self.stack[-1] in self.items_log else ''
        self.items_log[self.stack[-1]] = self.LOG_MESSAGE_FORMAT.format(full_message=full_message,
                                                                        level=message.get('level'),
                                                                        message=message.get('message').encode('UTF-8'))
