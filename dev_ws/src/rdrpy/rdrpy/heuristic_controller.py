from distutils.log import error
import rclpy
from rclpy.node import Node
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist 
import sensor_msgs.msg

import cv2
import numpy as np
from simple_pid import PID

class HeuristicController(Node):

    def __init__(self):
        super().__init__('heuristic_controller')
        self.cvb = CvBridge()
        self.pub_cmd_vel = self.create_publisher(Twist, 'cmd_vel', 10)

        self.subscription_blue = self.create_subscription(
            sensor_msgs.msg.CompressedImage,
            'blue_feed',
            self.listener_callback_blue,
            10)
        self.subscription_yellow = self.create_subscription(
            sensor_msgs.msg.CompressedImage,
            'yellow_feed',
            self.listener_callback_yellow,
            10)
        self.yellow_frame = np.zeros((640, 480))
        self.blue_frame = np.zeros((640, 480))

        self.declare_parameter('midpoint_segments', 16)
        self.midpoint_segments = self.get_parameter('midpoint_segments').get_parameter_value().integer_value
        self.declare_parameter('blue_is_left', True)
        self.blue_is_left = self.get_parameter('blue_is_left').get_parameter_value().bool_value
        self.declare_parameter('use_polyfit', False)
        self.use_polyfit = self.get_parameter('use_polyfit').get_parameter_value().bool_value
        self.declare_parameter('track_width', 400)
        self.track_width = self.get_parameter('track_width').get_parameter_value().integer_value
        self.declare_parameter('base_throttle', 0.2)
        self.base_throttle = self.get_parameter('base_throttle').get_parameter_value().double_value
        
        self.pid = PID(1, 0.1, 0.05, setpoint=0)
        self.pid.proportional_on_measurement = True

    def calculate_steering(self):
        yellowDot = (125, 255, 255)
        blueDot = (255, 125, 125)
        centerDot = (255, 255, 255)
        centerLine = (0, 0, 255)

        imsizeX = self.blue_frame.shape[1]
        imsizeY = self.blue_frame.shape[0]

        midX = imsizeX//2

        predictionHeight = imsizeY//self.midpoint_segments

        midPoints = np.zeros(self.midpoint_segments)
        verticalPoints = np.linspace(imsizeY-predictionHeight//2, predictionHeight//2, num=self.midpoint_segments, dtype=np.int32)

        f = np.zeros((imsizeY, imsizeX, 3))

        for i in range(self.midpoint_segments):
            blue_cropped = self.blue_frame[imsizeY-predictionHeight*(i+1):imsizeY-predictionHeight*i]
            yellow_cropped = self.yellow_frame[imsizeY-predictionHeight*(i+1):imsizeY-predictionHeight*i]

            yellowCont, yellowHier = cv2.findContours(yellow_cropped, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
            if len(yellowCont) > 0:
                yellowRet = True
                cont = max(yellowCont, key = cv2.contourArea)
                M = cv2.moments(cont)
                try:
                    yellowX = int(M['m10']/M['m00'])
                except:
                    yellowRet = False
            else:
                yellowRet = False

            blueCont, blueHier = cv2.findContours(blue_cropped, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
            if len(blueCont) > 0:
                blueRet = True
                cont = max(blueCont, key = cv2.contourArea)
                M = cv2.moments(cont)
                try:
                    blueX = int(M['m10']/M['m00'])
                except:
                    blueRet = False
            else:
                blueRet = False

            cv2.line(f, (imsizeX//2, 0), (imsizeX//2, imsizeY), centerLine, 3)
            if (self.blue_is_left):
                addVal = 1
            else:
                addVal = -1

            circleY = verticalPoints[i]

            if (yellowRet and blueRet):
                midX = (yellowX+blueX)//2
                cv2.circle(f, (yellowX, circleY), 3, yellowDot, -1)
                cv2.circle(f, (blueX, circleY), 3, blueDot, -1)
                cv2.circle(f, (midX, circleY), 3, centerDot, -1)
            elif (yellowRet):
                midX = yellowX - (self.track_width//2) * addVal
                cv2.circle(f, (yellowX, circleY), 3, yellowDot, -1)            
                cv2.circle(f, (midX, circleY), 3, centerDot, -1)
            elif (blueRet):
                midX = blueX + (self.track_width//2) * addVal
                cv2.circle(f, (blueX, circleY), 3, blueDot, -1)
                cv2.circle(f, (midX, circleY), 3, centerDot, -1)

            midPoints[i] = midX 

        if (self.use_polyfit):
            polyfit = np.polyfit(midPoints, verticalPoints, 2)
            a = polyfit[0]
            b = polyfit[1]
            c = polyfit[2]
            for x in range(imsizeX):
                y = int(a * x**2  +  b * x  +  c)
                cv2.circle(f, (x, y), 3, (0, 255, 0), -1)
            
        else:
            cv2.circle(f, (int(midPoints[3]), verticalPoints[3]), 10, (0, 255, 0), -1)
            cv2.imshow("frame", f)
            cv2.waitKey(1)
            return midPoints[3]

    def listener_callback_blue(self, msg):
        self.blue_frame = self.cvb.compressed_imgmsg_to_cv2(msg)
        cv2.imshow("recieve_blue", self.blue_frame)
        cv2.waitKey(1)
        #self.get_logger().info("recieved blue frame")        

    def listener_callback_yellow(self, msg):
        self.yellow_frame = self.cvb.compressed_imgmsg_to_cv2(msg)
        cv2.imshow("recieve_yellow", self.yellow_frame)
        cv2.waitKey(1)
        #self.get_logger().info("recieved yellow frame")
        twist = Twist()
        twist.linear.x = self.base_throttle
        pidError = self.calculate_steering()
        twist.angular.z = self.pid(pidError)
        self.pub_cmd_vel.publish(twist)

def main(args=None):
    rclpy.init(args=args)

    heuristic_controller = HeuristicController()

    rclpy.spin(heuristic_controller)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    heuristic_controller.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()