import math
import rclpy
from rclpy.node import Node
import cv2
import numpy as np
import torch
import sensor_msgs.msg
from cv_bridge import CvBridge
from std_srvs.srv import Empty
from .submodules.yutils import YUtils


class HSVCam(Node):
    def __init__(self):
        super().__init__('hsv_cam')
        
        self.calibrate_warp_srv = self.create_service(Empty, 'calibrate_warp', self.calibrate_warp_callback)
        self.refresh_params_srv = self.create_service(Empty, 'refresh_params', self.refresh_params_callback)

        self.pub_blue_img = self.create_publisher(sensor_msgs.msg.CompressedImage, 'blue_feed', 1)
        self.pub_yellow_img = self.create_publisher(sensor_msgs.msg.CompressedImage, 'yellow_feed', 1)

        self.yellow_hsv_vals = [25, 54, 60, 32, 255, 255]
        self.declare_parameter('yellow_hsv_vals', self.yellow_hsv_vals)
        self.blue_hsv_vals = [100, 120, 85, 122, 255, 255]
        self.declare_parameter('blue_hsv_vals', self.blue_hsv_vals)        

        self.declare_parameter('warp_calib_file', 'warp_calib.npz')
        self.declare_parameter('warp_calib_save', 'warp_calib')
        
        self.yutils = YUtils()

        self.yellow_hsv_vals = self.get_parameter('yellow_hsv_vals').get_parameter_value().integer_array_value
        self.blue_hsv_vals = self.get_parameter('blue_hsv_vals').get_parameter_value().integer_array_value

        try:
            calib_file_path =  self.get_parameter('warp_calib_file').get_parameter_value().string_value
            data = np.load(calib_file_path)
            self.homography = data['homography']
            self.bwidth = int(data['width'])
            self.bheight = int(data['height'])
        except Exception as e:
            self.get_logger().info("failed to read warp calibration file, no warp will be applied")

        timer_period = 1 / 60
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.cap = cv2.VideoCapture(0)
        self.get_logger().info("camera stream initialised")
        ret, self.frame = self.cap.read()
        self.cvb = CvBridge()
        self.get_logger().info("CvBridge initialised")     

    @staticmethod
    def generateFlatCorners():
        cornersFlat = np.zeros((70, 1, 2))

        for x in range (8):
            for y in range(5):
                i = y + x * 7
                cornersFlat[i][0][0] = x * 28
                cornersFlat[i][0][1] = y * 28
        return cornersFlat
    
    @staticmethod
    def getPointRotation(pt1, pt2):
        slope = (pt1[1] - pt2[1]) / (pt1[0] - pt2[0])
        return math.degrees(math.atan(slope))

    def calibrateWarp(self):
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        while (1):
            ret, frame = self.cap.read()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            retCorners, cornersReal = cv2.findChessboardCorners(gray, (5, 8))
            cornersFlat = self.generateFlatCorners()

            if(retCorners):
                corners2 = cv2.cornerSubPix(gray,cornersReal, (11,11), (-1,-1), criteria)
                H, _ = cv2.findHomography(corners2, cornersFlat)

                corners = np.array([
                    [0, 0],
                    [0, frame.shape[0] - 1],
                    [frame.shape[1] - 1, frame.shape[0] -1],
                    [frame.shape[1] - 1, 0]
                ])

                cornersFinal = cv2.perspectiveTransform(np.float32([corners]), H)[0]

                bx, by, bwidth, bheight = cv2.boundingRect(cornersFinal)

                angle = self.getPointRotation(cornersFinal[1], cornersFinal[2])
                print(angle)
                rotationMtx = cv2.getRotationMatrix2D((bwidth/2, bheight/2), angle, 1)

                cornersFlat = cv2.transform(cornersFlat, rotationMtx)
                H, _ = cv2.findHomography(corners2, cornersFlat)

                corners = np.array([
                    [0, 0],
                    [0, frame.shape[0] - 1],
                    [frame.shape[1] - 1, frame.shape[0] -1],
                    [frame.shape[1] - 1, 0]
                ])

                cornersFinal = cv2.perspectiveTransform(np.float32([corners]), H)[0]

                bx, by, bwidth, bheight = cv2.boundingRect(cornersFinal)

                th = np.array([
                    [ 1, 0, -bx ],
                    [ 0, 1, -by ],
                    [ 0, 0,   1 ]
                ])

                pth = th.dot(H)
                
                calib_file_path = self.get_parameter('warp_calib_save').get_parameter_value().string_value
                np.savez(calib_file_path, homography=pth, width=bwidth, height=bheight)

                return pth, bwidth, bheight

    def hsv_line_detect(self, image):
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        resized_image = cv2.resize(hsv_image, (320, 240), cv2.INTER_NEAREST)
        blue_mask = cv2.inRange(resized_image, 
            (
                self.blue_hsv_vals[0],
                self.blue_hsv_vals[1],
                self.blue_hsv_vals[2]
            ),
            (
                self.blue_hsv_vals[3],
                self.blue_hsv_vals[4],
                self.blue_hsv_vals[5]
                
            ))
        yellow_mask = cv2.inRange(resized_image, 
            (
                self.yellow_hsv_vals[0],
                self.yellow_hsv_vals[1],
                self.yellow_hsv_vals[2]
            ),
            (
                self.yellow_hsv_vals[3],
                self.yellow_hsv_vals[4],
                self.yellow_hsv_vals[5]
                
            ))
        return blue_mask, yellow_mask
        
    def timer_callback(self):
        try:
            ret, self.frame = self.cap.read()
            image = self.frame
            
            if (ret):
                if (hasattr(self, 'homography')):
                    image = cv2.warpPerspective(image, self.homography, (self.bwidth, self.bheight))
                
                blue_mask, yellow_mask = self.hsv_line_detect(image)

                print(self.yutils.detect(image, True, 0.60))
                
                self.pub_blue_img.publish(self.cvb.cv2_to_compressed_imgmsg(blue_mask))
                self.pub_yellow_img.publish(self.cvb.cv2_to_compressed_imgmsg(yellow_mask))

        except Exception as e:
            self.get_logger().info(str(e)) 

    def calibrate_warp_callback(self, request, response):
        self.get_logger().info('Request to calibrate recieved')
        try:
            self.homography, self.bwidth, self.bheight = self.calibrateWarp()
        except Exception as e:
            self.get_logger().info('Calibration Failed')
            self.get_logger().info(str(e))
        else:
            self.get_logger().info('Calibration Succeeded')
        return response

    def refresh_params_callback(self, request, response):
        self.get_logger().info('Refreshing the parameters')
        self.yellow_hsv_vals = self.get_parameter('yellow_hsv_vals').get_parameter_value().integer_array_value
        self.blue_hsv_vals = self.get_parameter('blue_hsv_vals').get_parameter_value().integer_array_value
        return response

def main(args=None):
    rclpy.init(args=args)

    hsv_cam = HSVCam()

    rclpy.spin(hsv_cam)

    rclpy.shutdown()

if __name__ == '__main__':
    main()