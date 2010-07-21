#!/usr/bin/env python

try:
    from setuptools import setup
except:
    from distutils.core import setup


setup(
      name='django-photo-albums',
      version='0.21.1',
      author='Mikhail Korobov',
      author_email='kmike84@gmail.com',
      url='http://bitbucket.org/kmike/django-photo-albums/',
      download_url = 'http://bitbucket.org/kmike/django-photo-albums/get/tip.zip',

      description = 'Pluggable Django image gallery app.',
      license = 'MIT license',
      packages=['photo_albums', 'photo_albums.lib'],
      package_data={'photo_albums': ['locale/en/LC_MESSAGES/*',
                                     'locale/ru/LC_MESSAGES/*',
                                     'locale/pl/LC_MESSAGES/*'
                                     ]},
      include_package_data = True,

      requires = ['django (>=1.1)'],
      install_requires=['django-generic-images >= 0.36', 'django-annoying > 0.7'],

      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Web Environment',
          'Framework :: Django',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Python Modules'
        ],
)