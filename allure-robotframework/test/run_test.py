"""
>>> from allure_commons_test.report import AllureReport, has_test_case
>>> from hamcrest import assert_that

>>> allure_report = AllureReport('output')


>>> assert_that(allure_report,
...             has_test_case('Passed Case'))

>>> assert_that(allure_report,
...             has_test_case('Failed Case'))
"""