
from setuptools import setup

install_requires = [
    "allure-python-commons==2.2.3b1"
]

PACKAGE = "allure-robotframework"
VERSION = "0.1"

if __name__ == '__main__':
    setup(
        name=PACKAGE,
        version=VERSION,
        description="Allure robotframework integration",
        license="Apache-2.0",
        keywords="allure reporting robotframework",
        packages=["allure_robotframework"],
        package_dir={"allure_robotframework": "src"},
        install_requires=install_requires
    )
