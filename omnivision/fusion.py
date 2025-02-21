##############################################################################
# Omnivision - 360 Degree Camera and LiDAR fusion
#
# Software License Agreement (GPL-3.0)
# Copyright (C) 2025 Blaine Oania
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2 as pc2  
from cv_bridge import CvBridge
import cv2
import numpy as np

class Fusion(Node):
    def __init__(self):
        super().__init__('fuser')

        self.declare_parameter('transformation_matrix', [
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1
            ])

        self.declare_parameter('pointcloud_topic', 'velodyne_points')
        self.declare_parameter('image_topic', 'camera/image')
        self.declare_parameter('depth_map', 'camera/image/depth')

        self.subscriber_ = self.create_subscription(
            Image,
            self.get_parameter('image_topic').value,
            self.image_callback,
            1)

        self.lidar_sub_ = self.create_subscription(
            PointCloud2,
            self.get_parameter('pointcloud_topic').value,
            self.lidar_callback,
            1)
        
        self.depth_map_publisher_ = self.create_publisher(
            Image,
            self.get_parameter('depth_map').value,
            1)

        self.texturized_pointcloud_publisher_ = self.create_publisher(
            PointCloud2,
            'textured_pointcloud',
            1)

        self.texturized_depth_map_publisher_ = self.create_publisher(
            Image,
            "texturized_depth_map",
            1)
        
        self.get_logger().info(str(self.get_parameter('transformation_matrix').value))
        self.transformation_matrix = np.array(
            self.get_parameter('transformation_matrix').value).reshape((4, 4))

        self.bridge=CvBridge()
        self.latest_image = None
        self.latest_pointcloud = None

    def image_callback(self, msg):
        self.get_logger().info('Received image')

        self.latest_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self.latest_image = cv2.flip(self.latest_image, 1)

        self.process_data()

    def lidar_callback(self, msg):
        self.get_logger().info('Received lidar')

        self.latest_pointcloud = msg
 
    def process_data(self):
        if self.latest_image is None or self.latest_pointcloud is None:
            return

        numpy_image = self.latest_image.copy()

        # Parse point cloud data
        points = pc2.read_points(self.latest_pointcloud, field_names=("x", "y", "z", "intensity", "ring", "time"), skip_nans=True)
        points = list(points)
        points_array = np.array(points, dtype=[
            ('x', np.float32),
            ('y', np.float32),
            ('z', np.float32),
            ('intensity', np.float32),
            ('ring', np.uint16),
            ('time', np.float32)]
        )

        x = np.array(points_array['x'])
        y = np.array(points_array['y'])
        z = np.array(points_array['z'])
        ones = np.ones_like(x)

        # Transform points to camera frame
        points_matrix = np.stack((x, y, z, ones), axis=-1)
        transformed_points = np.dot(points_matrix, self.transformation_matrix.T)
        x, y, z = transformed_points[:, 0], transformed_points[:, 1], transformed_points[:, 2]

        # Convert into azimuth, elevation, and radius
        r = np.sqrt(x**2 + y**2 + z**2)
        theta = np.arctan2(y, x)
        phi = np.arccos(z / r)

        # Normalize angles to image coordinates
        u = ((theta + np.pi) / (2 * np.pi) * self.latest_image.shape[1]).astype(int)
        v = ((phi) / np.pi * self.latest_image.shape[0]).astype(int)

        # Clip bounds
        valid_indices = (
            (u >= 0) & (u < self.latest_image.shape[1]) &
            (v >= 0) & (v < self.latest_image.shape[0])
        )

        u = u[valid_indices]
        v = v[valid_indices]
        x = x[valid_indices]
        y = y[valid_indices]

        colors = numpy_image[v, u]

        if self.texturized_pointcloud_publisher_.get_subscription_count() > 0:
            # Add alpha channel and concatenate for rviz2
            alpha = np.full(colors.shape[0], 255, dtype=np.uint32)
            rgba_colors = np.column_stack((colors.astype(np.uint32), alpha))
            rgba_uint32 = (
                (rgba_colors[:, 3].astype(np.uint32) << 24) |
                (rgba_colors[:, 2].astype(np.uint32) << 16) |
                (rgba_colors[:, 1].astype(np.uint32) << 8) |
                rgba_colors[:, 0].astype(np.uint32)
            )

            # Create point cloud object with rgb8 field
            textured_points = np.zeros((len(x),), dtype=[
                ('x', np.float32),
                ('y', np.float32),
                ('z', np.float32),
                ('rgba', np.uint32)
            ])

            textured_points['x'] = x
            textured_points['y'] = y
            textured_points['z'] = z
            textured_points['rgba'] = rgba_uint32

            header = self.latest_pointcloud.header
            fields = [
                pc2.PointField(name='x', offset=0, datatype=pc2.PointField.FLOAT32, count=1),
                pc2.PointField(name='y', offset=4, datatype=pc2.PointField.FLOAT32, count=1),
                pc2.PointField(name='z', offset=8, datatype=pc2.PointField.FLOAT32, count=1),
                pc2.PointField(name='rgba', offset=12, datatype=pc2.PointField.UINT32, count=1),
            ]
            textured_pointcloud = pc2.create_cloud(header, fields, textured_points)

            # Publish the textured point cloud
            self.texturized_pointcloud_publisher_.publish(textured_pointcloud)
            self.get_logger().info('Published textured point cloud')

        if self.depth_map_publisher_.get_subscription_count() > 0:
            # Create a depth map from the transformed points
            depth_map = np.zeros((numpy_image.shape[0], numpy_image.shape[1]), dtype=np.float32)
            for i in range(len(u)):
                u_coord = u[i]
                v_coord = v[i]
                depth = r[i]
                depth_map[v_coord, u_coord] = depth
            
            # Package as ros2 message
            depth_map = cv2.normalize(depth_map,
                                        None,
                                        0,
                                        255,
                                        cv2.NORM_MINMAX).astype(np.uint8)

            depth_image = self.bridge.cv2_to_imgmsg(depth_map, encoding='mono8')
            self.depth_map_publisher_.publish(depth_image)
        
        if self.texturized_depth_map_publisher_.get_subscription_count() > 0:
            # Create a colored depth map
            colored_depth_map = np.zeros_like(numpy_image)
            for i in range(len(u)):
                u_coord = u[i]
                v_coord = v[i]
                colored_depth_map[v_coord, u_coord] = colors[i]
            
            self.texturized_depth_map_publisher_.publish(
                self.bridge.cv2_to_imgmsg(colored_depth_map, encoding='bgr8'))

def main(args=None):
    rclpy.init(args=args)
    fuser = Fusion()
    rclpy.spin(fuser)
    fuser.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
