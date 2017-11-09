class RobotStatus(object):
    FAILED = 'FAIL'
    PASSED = 'PASS'


class RobotTestType(object):
    SETUP = 'Setup'
    TEARDOWN = 'Teardown'
    KEYWORD = 'Keyword'


class RobotLogLevel(object):
    FAIL = 'FAIL'
    WARNING = 'WARN'
    INFORMATION = 'INFO'
    DEBUG = 'DEBUG'
    TRACE = 'TRACE'
