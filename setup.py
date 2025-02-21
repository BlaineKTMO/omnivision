from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'omnivision'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Blaine Oania',
    maintainer_email='Blaine.Oania@gmail.com',
    description='This package collects 360 video feed and LiDAR data,' +
                'and fuses them together to create a textured point cloud.',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'fusion = omnivision.fusion:main',
        ],
    },
)
