import os
import shutil
import stat

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install

this_directory = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


def post_install():
    path = '/usr/local/bin/wowusbgui'  # I give up, I have no clue how to get bin path that is used by pip
    shutil.copy2(this_directory + '/WowUSB/wowusbgui', path)  # I'll just hard code it until someone finds better way

    shutil.copy2(this_directory + '/miscellaneous/com.rebots.wowusb.ds9.policy', "/usr/share/polkit-1/actions")

    try:
        os.makedirs('/usr/share/icons/WowUSB-DS9')
    except FileExistsError:
        pass

    shutil.copy2(this_directory + '/WowUSB/data/icon.ico', '/usr/share/icons/WowUSB-DS9/icon.ico')
    shutil.copy2(this_directory + '/miscellaneous/WowUSB-DS9.desktop', "/usr/share/applications/WowUSB-DS9.desktop")

    os.chmod('/usr/share/applications/WowUSB-DS9.desktop',
             stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IEXEC)  # 755



class PostDevelopCommand(develop):
    """Post-installation for development mode."""

    def run(self):
        # TODO
        develop.run(self)


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        post_install()
        install.run(self)


setup(
    name='WowUSB-DS9',
    version='0.3.0',
    description='WowUSB-DS9 is a simple tool that enables you to create your own USB stick Windows installer from an ISO image or a real DVD. This is a fork of WoeUSB-ng with added features.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/rebots-online/WowUSB',
    author='Robin L. M. Cheung, MBA',
    author_email='robin@robincheung.com',
    license='GPL-3',
    zip_safe=False,
    packages=['WowUSB'],
    include_package_data=True,
    scripts=[
        'WowUSB/wowusb',
    ],
    install_requires=[
        'termcolor',
        'wxPython',
    ],
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand
    }
)
