from setuptools import setup
from pathlib import Path

setup(name='quickrpc',
      version='0.1.0',
      description='Small, interoperable, automagic RPC library.',
      long_description=Path('README.rst').read_text(),
      long_description_content_type='text/x-rst',
      url='http://github.com/loehnertj/quickrpc',
      author='Johannes Loehnert',
      author_email='loehnert.kde@gmx.de',
      license='MIT',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Topic :: System :: Networking',
      ],
      packages=['quickrpc'],
      python_requires='>3.0',
      zip_safe=True)
