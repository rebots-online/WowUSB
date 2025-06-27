
import os
import shutil
import stat
import sys
from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install

# Get the directory where setup.py is located
this_directory = os.path.abspath(os.path.dirname(__file__))

# Read the long description from README.md
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Define package data to include
package_data = {
    'WoeUSB': ['locale/*/LC_MESSAGES/*.mo', 'data/*', 'data/*/*'],
    'WowUSB': [
        'locale/*/LC_MESSAGES/*.mo',
        'data/*',
        'data/*/*', # This covers data/bootloaders, data/drivers, data/scripts
        'data/grub-themes/wowusb/*' # Specifically include theme files
    ],
}

# Define dependencies based on the operating system
install_requires = [
    'termcolor>=1.1.0',
    'wxPython>=4.0.0',
    # Jinja2 is not used by current grub_manager.py, f-strings are used instead.
    # If Jinja2 were to be used for templates:
    # 'Jinja2>=3.0',
]

# Define filesystem tool dependencies (for documentation and potential checks)
# These are system dependencies, not Python packages installed by pip.
SYSTEM_DEPENDENCIES_INFO = {
    'Core': ['parted', 'wipefs', 'grub2-common', 'grub-pc-bin', 'grub-efi-amd64-bin', 'p7zip-full'],
    'Filesystems': {
        'fat32': ['dosfstools'],
        'ntfs': ['ntfs-3g'],
        'exfat': ['exfat-utils | exfatprogs'], # Use | to denote alternatives
        'f2fs': ['f2fs-tools'],
        'btrfs': ['btrfs-progs'],
    },
    'Multiboot_Linux_Install': {
        'sgdisk': ['gdisk'], # sgdisk is often in gdisk package
        'debootstrap': ['debootstrap'], # For Debian/Ubuntu full install
        'pacstrap': ['arch-install-scripts'], # For Arch full install
    }
}

# Define entry points
entry_points = {
    'console_scripts': [
        'wowusb=WowUSB.core:main',
    ],
    'gui_scripts': [
        'wowusbgui=WowUSB.gui:main',
    ],
}

# Define classifiers for PyPI
classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Environment :: X11 Applications :: GTK',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Topic :: System :: Installation/Setup',
    'Topic :: Utilities',
]

def post_install():
    """
    Post-installation tasks:
    - Copy GUI executable to system path
    - Install policy file for elevated privileges
    - Install desktop icon and application shortcut
    """
    path = '/usr/local/bin/wowusbgui'  # I give up, I have no clue how to get bin path that is used by pip
    shutil.copy2(this_directory + '/WowUSB/wowusbgui', path)  # I'll just hard code it until someone finds better way

    # Install policy file for elevated privileges
    try:
        os.makedirs('/usr/share/polkit-1/actions', exist_ok=True)
        shutil.copy2(this_directory + '/miscellaneous/com.rebots.wowusb.ds9.policy',
                    "/usr/share/polkit-1/actions")
    except (IOError, OSError) as e:
        print(f"Warning: Failed to install policy file: {e}", file=sys.stderr)

    # Install application icon
    try:
        os.makedirs('/usr/share/icons/WowUSB-DS9', exist_ok=True)
        shutil.copy2(this_directory + '/WowUSB/data/icon.ico',
                    '/usr/share/icons/WowUSB-DS9/icon.ico')
    except (IOError, OSError) as e:
        print(f"Warning: Failed to install icon: {e}", file=sys.stderr)

    # Install desktop shortcut
    try:
        shutil.copy2(this_directory + '/miscellaneous/WowUSB-DS9.desktop',
                    "/usr/share/applications/WowUSB-DS9.desktop")
        os.chmod('/usr/share/applications/WowUSB-DS9.desktop',
                 stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IEXEC)  # 755
    except (IOError, OSError) as e:
        print(f"Warning: Failed to install desktop shortcut: {e}", file=sys.stderr)

class PostDevelopCommand(develop):
    """Post-installation for development mode."""

    def run(self):
        develop.run(self)
        # Development mode doesn't need system-wide installation
        # but we can add development-specific tasks here if needed

class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):

        install.run(self)
        post_install()

setup(
    name='WowUSB-DS9',
    version='0.4.0',
    description='Create bootable Windows USB drives with support for large files and Windows-To-Go',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/rebots-online/WowUSB',
    author='Robin L. M. Cheung, MBA',
    author_email='robin@robincheung.com',
    license='GPL-3',
    python_requires='>=3.6',
    zip_safe=False,
    packages=find_packages(),
    include_package_data=True,
    package_data=package_data,
    scripts=[
        'WowUSB/wowusb',
        'WowUSB/wowusbgui',
    ],
    install_requires=install_requires,
    entry_points=entry_points,
    classifiers=classifiers,
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand
    },
    project_urls={
        'Bug Reports': 'https://github.com/rebots-online/WowUSB/issues',
        'Source': 'https://github.com/rebots-online/WowUSB',
        'Documentation': 'https://github.com/rebots-online/WowUSB/wiki',
    },
)
