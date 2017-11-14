import os
from allure_commons.model2 import Status, Label, Parameter
from constants import RobotStatus


def _clear_directory(path):
    for the_file in os.listdir(path):
        file_path = os.path.join(path, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(e)


def prepare_log_directory(logger_path, pool_id):
    if not os.path.exists(logger_path):
        os.makedirs(logger_path)
    if pool_id == 1:
        _clear_directory(logger_path)

def get_allure_status(status):
    return Status.PASSED if status == RobotStatus.PASSED else Status.FAILED


def get_allure_parameters(parameters):
    return [Parameter(name="arg{}".format(i + 1), value=param) for i, param in enumerate(parameters)]


def get_allure_suites(longname):
    labels = []
    suites = longname.split('.')
    if len(suites) > 3:
        labels.append(Label('parentSuite', suites.pop(0)))
    labels.extend([Label('suite', suites.pop(0)),
                   Label('subSuite', '.'.join(suites[:-1]))])
    return labels


def get_allure_tags(tags):
    return [Label('tag', tag) for tag in tags]


def get_allure_thread(pool_id):
    return Label('thread', 'Thread #{number}'.format(number=pool_id))
