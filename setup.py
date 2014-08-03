from setuptools import setup

setup(name='bdemeta',
      version='0.4',
      description='Build and test BDE-style code',
      url='https://github.com/frutiger/bdemeta',
      author='Masud Rahman',
      license='MIT',
      packages=['bdemeta'],
      entry_points={
          'console_scripts': ['bdemeta=bdemeta:main'],
      })
