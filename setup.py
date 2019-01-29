from setuptools import setup
import os

def readme():
    with open('README.md') as f:
        return f.read()


setup(name='sumo',
      version='0.1',
      description='Scripts for SUMO data access',
      long_description=readme(),
      keywords='sumo surveygizmo kitsune twitter reviews',
      url='https://github.com/ophie200/sumo',
      author='Nancy Wong',
      author_email='nawong@mozilla.com',
      license='...',
      packages=['SurveyGizmo'],
      install_requires=[
          'requests',
      ],
      test_suite='nose.collector',
      tests_require=['nose', 'nose-cover3'],
      entry_points={
          'console_scripts': ['run-surveygizmo=SurveyGizmo.run_get_survey_data:main'],
      },
      include_package_data=True,
      zip_safe=False)

