#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "rdr/JHPWMPCA9685.hpp"

using std::placeholders::_1;

class MotorDriver : public rclcpp::Node
{
  public:
  PCA9685 *pca9685 = new PCA9685();
    MotorDriver()
    : Node("motor_driver")
    {
      sub_cmd_vel_ = this->create_subscription<geometry_msgs::msg::Twist>(
      "cmd_vel", 10, std::bind(&MotorDriver::topic_callback, this, _1));
      pca9685->openPCA9685();
      pca9685->setAllPWM(0,0);
      pca9685->reset();
      pca9685->setPWMFrequency(60);

    }

  private:
  int servoMin = 300;
  int servoMax = 460;
  int escMin = 300;
  int escMax = 520;
  
    static int map ( float x, int in_min, int in_max, int out_min, int out_max) {
        float toReturn =  (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min ;
        // For debugging:
        // printf("MAPPED %d to: %d\n", x, toReturn);
        return (int)toReturn;
    }

    void topic_callback(const geometry_msgs::msg::Twist::SharedPtr msg) const
    {
      RCLCPP_INFO(this->get_logger(), "Received cmd_vel: %f %f", msg->linear.x, msg->angular.z);
      float linear_x = msg->linear.x;
      float angular_z = msg->angular.z;
      int throttle = map(linear_x, -1, 1, escMin, escMax);
      int steering = map(angular_z, 1, -1, servoMin, servoMax);
      RCLCPP_INFO(this->get_logger(), "Mapped cmd_vel: %d %d", throttle, steering);
      pca9685->setPWM(15, 0, throttle);
      pca9685->setPWM(0, 0, steering);
    }
    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr sub_cmd_vel_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<MotorDriver>());
  rclcpp::shutdown();
  return 0;
}
