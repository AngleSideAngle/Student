"""
File docstring
"""

################################################################################
# Imports
################################################################################

# General
import copy
import time
import threading
from enum import Enum
import os # TODO: see if this can be removed

# ROS
import rospy
from sensor_msgs.msg import LaserScan
from sensor_msgs.msg import Image
from ackermann_msgs.msg import AckermannDriveStamped
import XboxController


################################################################################
# Racecar class
################################################################################

class Racecar:
    """
    Class docstring
    """
    def __init__(self):
        self.__cur_update = self.__default_update

        # Modules
        self.drive = self.Drive()
        self.controller = self.Controller(self)
        
        # User provided start and update functions
        self.__user_start = None
        self.__user_update = None

        # Start thread in default drive mode
        self.__handle_back()
        self.__thread = threading.Thread(target=self.__run)
        self.__thread.daemon = True
        self.__thread.start()

        # Print welcome message
        print(">> Racecar initialization successful")
        print(">> Press the START button to run your program, "
            "press the BACK button to enter default drive mode, "
            "and press BACK and START at the same time to exit.")

    def set_start_update(self, start, update):
        self.__user_start = start
        self.__user_update = update

    def __handle_start(self):
        print(">> Entering user program mode")
        self.__user_start()
        self.__cur_update = self.__user_update

    def __handle_back(self):
        print(">> Entering default drive mode")
        self.__default_start()
        self.__cur_update = self.__default_update

    def __handle_exit(self):
        print(">> Goodbye!")
        exit(0)

    def __run(self):
        FRAMES_PER_SECOND = 30
        timer = rospy.Rate(FRAMES_PER_SECOND)
        while True:
            self.__cur_update()
            self.__update_modules()
            timer.sleep()

    def __update_modules(self):
        self.drive._Drive__update()
        self.controller._Controller__update()

    def __default_start(self):
        pass

    def __default_update(self):
        SPEED_MULTIPLIER = 1.0
        ANGLE_MULTIPLIER = 20

        forwardSpeed = self.controller.get_trigger(self.controller.Trigger.LEFT)
        backSpeed = self.controller.get_trigger(self.controller.Trigger.RIGHT)
        speed = (forwardSpeed - backSpeed) * SPEED_MULTIPLIER

        # If both triggers are pressed, stop for safety
        if (forwardSpeed > 0 and backSpeed > 0):
            speed = 0

        angle = self.controller.get_joystick(self.controller.Joystick.LEFT)[0] \
            * ANGLE_MULTIPLIER

        self.drive.set_speed_angle(speed, angle)

    class Drive:
        """
        Controls the car's movement by allowing the user to set the state
        associated with speed and turning
        """
        __TOPIC = "/drive"

        def __init__(self):
            self.__publisher = rospy.Publisher(self.__TOPIC, \
                AckermannDriveStamped, queue_size=1)
            self.__message = AckermannDriveStamped()

        def set_speed_angle(self, speed, angle):
            """
            Sets the speed at which the wheels turn and the angle of the front
            wheels

            Inputs:
                speed (float) = the speed, with positive for forward and
                    negative for reverse
                angle (float) = the angle of the front wheels, with positive for
                        right turns and negative for left turns

            Constants:
                MAX_SPEED = the maximum magnitude of speed allowed
                MAX_ANGLE = the maximum angle magnitude
                CONVERSION_FACTOR = the conversion factor used to convert
                    degrees to the units expected by ROS
            """
            MAX_SPEED = 5
            MAX_ANGLE = 20
            CONVERSION_FACTOR = 1 / 80

            speed = max(-MAX_SPEED, min(MAX_SPEED, speed))
            angle = max(-MAX_ANGLE, min(MAX_ANGLE, angle))
            self.__message = AckermannDriveStamped()
            self.__message.drive.speed = speed
            self.__message.drive.steering_angle = angle # * CONVERSION_FACTOR

        def stop(self):
            """
            Brings the car to a stop and points the front wheels forward
            """
            self.set_speed_angle(0, 0)

        def __update(self):
            self.__publisher.publish(self.__message)

    class Controller:
        """
        Docstring
        """
        class Button(Enum):
            A = 0
            B = 1
            X = 2
            Y = 3
            LB = 4
            RB = 5
            LJOY = 6
            RJOY = 7

        class Trigger(Enum):
            LEFT = 0
            RIGHT = 1

        class Joystick(Enum):
            LEFT = 0
            RIGHT = 1

        def __init__(self, racecar):
            self.__racecar = racecar
            self.__controller = XboxController.XboxController(
                controllerCallBack = None,
                joystickNo = 0,
                deadzone = 0.15,
                scale = 1,
                invertYAxis = False)

            self.__was_down = [False] * len(self.Button)
            self.__is_down = [False] * len(self.Button)
            self.__cur_down = [False] * len(self.Button)

            self.__last_trigger = [0, 0]
            self.__cur_trigger = [0, 0]

            self.__last_joystick = [[0, 0], [0, 0]]
            self.__cur_joystick = [[0, 0], [0, 0]]

            self.__cur_start = 0
            self.__cur_back = 0


            # Set button callbacks
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.A,
                lambda value : self.__button_callback(self.Button.A, value)
            )
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.B,
                lambda value : self.__button_callback(self.Button.B, value)
            )
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.X,
                lambda value : self.__button_callback(self.Button.X, value)
            )
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.Y,
                lambda value : self.__button_callback(self.Button.Y, value)
            )
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.LB,
                lambda value : self.__button_callback(self.Button.LB, value)
            )
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.RB,
                lambda value : self.__button_callback(self.Button.RB, value)
            )
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.LEFTTHUMB,
                lambda value : self.__button_callback(self.Button.LJOY, value)
            )
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.RIGHTTHUMB,
                lambda value : self.__button_callback(self.Button.RJOY, value)
            )


            # Set trigger callbacks
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.LTRIGGER,
                lambda value : self.__trigger_callback(self.Trigger.LEFT, value)
            )
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.RTRIGGER,
                lambda value : self.__trigger_callback(self.Trigger.RIGHT, \
                    value)
            )


            # Set joystick callbacks
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.LTHUMBX,
                lambda value : self.__joystick_callback(self.Joystick.RIGHT, \
                    0, value)
            )
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.LTHUMBY,
                lambda value : self.__joystick_callback(self.Joystick.RIGHT, \
                    1, value)
            )
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.RTHUMBX,
                lambda value : self.__joystick_callback(self.Joystick.RIGHT, \
                    0, value)
            )
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.RTHUMBX,
                lambda value : self.__joystick_callback(self.Joystick.RIGHT, \
                    1, value)
            )


            # Set START and BACK callbacks
            self.__controller.setupControlCallback(
                self.__controller.XboxControls.START,
                self.__start_callback
            )

            self.__controller.setupControlCallback(
                self.__controller.XboxControls.BACK,
                self.__back_callback
            )

            self.__controller.start()

        def is_down(self, button):
            if isinstance(button, self.Button):
                return self.__is_down[button.value]
            return False

        def was_pressed(self, button):
            if isinstance(button, self.Button):
                return self.__is_down[button.value] \
                    and not self.__was_down[button.value]
            return False

        def was_released(self, button):
            if isinstance(button, self.Button):
                return not self.__is_down[button.value] \
                    and self.__was_down[button.value]
            return False

        def get_trigger(self, trigger):
            if isinstance(trigger, self.Trigger):
                return self.__last_trigger[trigger.value]
            return 0

        def get_joystick(self, joystick):
            if isinstance(joystick, self.Joystick):
                return self.__last_joystick[joystick.value]
            return (0, 0)
 
        def __button_callback(self, button, value):
            self.__cur_down[button.value] = bool(value)

        def __trigger_callback(self, trigger, value):
            self.__cur_trigger[trigger.value] = value

        def __joystick_callback(self, joystick, axis, value):
            self.__cur_joystick[joystick.value][axis] = value

        def __start_callback(self, value):
            self.__cur_start = value
            if value:
                if self.__cur_back:
                    self.__racecar._Racecar__handle_exit()
                else:
                    self.__racecar._Racecar__handle_start()

        def __back_callback(self, value):
            self.__cur_back = value
            if value:
                if self.__cur_start:
                    self.__racecar._Racecar__handle_exit()
                else:
                    self.__racecar._Racecar__handle_back()

        def __update(self):
            self.__was_down = copy.deepcopy(self.__is_down)
            self.__is_down = copy.deepcopy(self.__cur_down)
            self.__last_trigger = copy.deepcopy(self.__cur_trigger)
            self.__last_joystick = copy.deepcopy(self.__cur_joystick)  

    # class Physics:
    #     def get_acceleration(self) -> Tuple[float, float, float]:
    #         return (0, 0, 0)

    #     def get_angular_velocity(self) -> Tuple[float, float, float]:
    #         return (0, 0, 0)

    #     def get_speed(self) -> float:
    #         return 0

    # class Camera:
    #     def get_image(self):
    #         return np.fromstring(self.last_image,dtype=np.uint8).reshape((480,-1,3))[...,::-1]

    #     def get_depth_image(self):
    #         return None

    # class Lidar:
    #     def get_raw(self):
    #         return None
        
    #     def get_map(self):
    #         return None    

    # class GPIO:
    #     def get_pin(self, pin: int) -> int:
    #         return 0

    #     def set_pin(self, pin: int, value: int):
    #         raise NotImplementedError()


    # class Controller:
    #     def is_pressed(self, button) -> bool:
    #         return False

    #     def get_trigger(self, trigger) -> float:
    #         return 0

    #     def get_joystick(self, joystick) -> Tuple[float, float]:
    #         return (0, 0)

    # class Display:

    # class Sound: 


        

    # def image_callback(self, msg):
    #     self.last_image = msg.data
        
    # def scan_callback(self, msg):
    #     self.last_scan = msg.ranges
        
    # def get_lidar(self):
    #     return None



    # def show_image(self, image):
    #     raise NotImplementedError()

    # def show_text(self, text: str, size: float = 12, color: Tuple[float, float, float] = (0, 0, 0)):
    #     raise NotImplementedError()
    
    # def get_mic_amplitude(self, ) -> float:
    #     return 0

    # def set_wav(self, wav):
    #     raise NotImplementedError()

    # def play_wave(self):
    #     raise NotImplementedError()

    # def is_wav_playing(self) -> bool:
    #     return False