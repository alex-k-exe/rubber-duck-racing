from setuptools import setup

package_name = 'rdrpy'
submodules = 'rdrpy/submodules'
utils = 'rdrpy/submodules/utils'
models = 'rdrpy/submodules/models'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name, submodules, utils, models],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='nikita',
    maintainer_email='nikita@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'odom = rdrpy.odometry:main',
            'imu = rdrpy.imu:main',
            'hsv_cam = rdrpy.hsv_cam:main',
            'hsv_cam_desktop = rdrpy.hsv_cam_desktop:main',
            'camera_processor = rdrpy.camera_processor:main',
            'camera_viewer = rdrpy.camera_viewer:main',
            'hsv_tuner = rdrpy.hsv_tuner:main',
            'heuristic_controller = rdrpy.heuristic_controller:main',
            'point_cloud = rdrpy.point_cloud:main',
        ],
    },
)
