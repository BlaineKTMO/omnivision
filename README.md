# Omnivision

Omnivision is a ROS 2 package designed for 360-degree camera and LiDAR fusion. This package collects 360 video feed and LiDAR data, and fuses them together to create a textured point cloud.

## Features

- **360-degree Camera Integration**: Captures video feed from a 360-degree camera.
- **LiDAR Integration**: Collects point cloud data from a LiDAR sensor.
- **Data Fusion**: Combines the video feed and LiDAR data to create a textured point cloud.
- **Depth Map Generation**: Generates depth maps from the fused data.

## Installation

1. Clone the repository into your ROS 2 workspace:
    ```sh
    git clone <repository_url> /path/to/ros2_ws/src/omnivision
    ```

2. Build the package:
    ```sh
    cd /path/to/ros2_ws
    colcon build
    ```

3. Source the workspace:
    ```sh
    source /path/to/ros2_ws/install/setup.bash
    ```

## Usage

To launch the Omnivision package, use the provided launch file:

```sh
ros2 launch omnivision bringup.launch.py
```

## To Do (Contributions welcome!)
- Find optimization methods
- Add media
- Add camera header information to depth map
- Add option for LiDAR interpolation(?)
- Configure launch file