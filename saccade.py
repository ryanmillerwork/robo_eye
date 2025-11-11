#!/usr/bin/env python3
"""
Saccade Control CLI for Phidget Servo-based Eye Movement System

Controls pan (x-axis, servo 0) and tilt (y-axis, servo 1) servos to simulate
rapid eye movements (saccades) with configurable velocity and acceleration.
"""

from Phidgets.Devices.AdvancedServo import AdvancedServo
from Phidgets.PhidgetException import PhidgetException
import argparse
import sys
import time


# Default saccade parameters based on human eye movement characteristics
# Human saccades can reach peak velocities of 400-700 deg/s
DEFAULT_MAX_VELOCITY = 400.0  # degrees per second
# Human saccades have high accelerations (10,000-40,000 deg/s²)
# Using more conservative value suitable for servo motors
DEFAULT_ACCELERATION = 2000.0  # degrees per second squared

# Servo channel assignments
PAN_CHANNEL = 0   # X-axis (horizontal movement)
TILT_CHANNEL = 1  # Y-axis (vertical movement)


class SaccadeController:
    """Controls servo motors to perform saccadic eye movements."""
    
    def __init__(self, pan_zero=90.0, tilt_zero=90.0):
        """
        Initialize the saccade controller.
        
        Args:
            pan_zero: Zero position for pan servo (degrees)
            tilt_zero: Zero position for tilt servo (degrees)
        """
        self.servo = AdvancedServo()
        self.pan_zero = pan_zero
        self.tilt_zero = tilt_zero
        self.connected = False
    
    def connect(self):
        """Connect to the Phidget servo controller."""
        try:
            # Open connection to Phidget device
            self.servo.openPhidget()
            # Wait up to 5 seconds for device to attach
            self.servo.waitForAttach(5000)
            print(f"Connected to: {self.servo.getDeviceName()}")
            print(f"Serial Number: {self.servo.getSerialNum()}")
            self.connected = True
            return True
        except PhidgetException as e:
            print(f"Error connecting to Phidget device: {e}", file=sys.stderr)
            return False
    
    def configure_servo(self, channel, acceleration, max_velocity):
        """
        Configure a servo channel with specified parameters.
        
        Args:
            channel: Servo channel number (0 or 1)
            acceleration: Acceleration in degrees/second²
            max_velocity: Maximum velocity in degrees/second
        """
        try:
            # Enable smooth speed ramping
            self.servo.setSpeedRampingOn(channel, True)
            # Set acceleration rate
            self.servo.setAcceleration(channel, acceleration)
            # Set maximum velocity
            self.servo.setVelocityLimit(channel, max_velocity)
        except PhidgetException as e:
            print(f"Error configuring servo channel {channel}: {e}", file=sys.stderr)
            raise
    
    def initialize(self, acceleration=DEFAULT_ACCELERATION, max_velocity=DEFAULT_MAX_VELOCITY):
        """
        Initialize servos to their zero positions.
        
        Args:
            acceleration: Acceleration for initialization movement
            max_velocity: Max velocity for initialization movement
        """
        if not self.connected:
            print("Error: Not connected to device", file=sys.stderr)
            return False
        
        try:
            print(f"Initializing servos to zero position...")
            print(f"  Pan (X) zero: {self.pan_zero}°")
            print(f"  Tilt (Y) zero: {self.tilt_zero}°")
            
            # Configure both servo channels
            self.configure_servo(PAN_CHANNEL, acceleration, max_velocity)
            self.configure_servo(TILT_CHANNEL, acceleration, max_velocity)
            
            # Engage servos
            self.servo.setEngaged(PAN_CHANNEL, True)
            self.servo.setEngaged(TILT_CHANNEL, True)
            
            # Move to zero positions
            self.servo.setPosition(PAN_CHANNEL, self.pan_zero)
            self.servo.setPosition(TILT_CHANNEL, self.tilt_zero)
            
            # Wait for movement to complete
            time.sleep(1.0)
            
            print("Initialization complete")
            return True
            
        except PhidgetException as e:
            print(f"Error during initialization: {e}", file=sys.stderr)
            return False
    
    def saccade(self, x, y, acceleration=DEFAULT_ACCELERATION, max_velocity=DEFAULT_MAX_VELOCITY):
        """
        Perform a saccade to the specified position.
        
        Args:
            x: Target X position in degrees (relative to pan zero)
            y: Target Y position in degrees (relative to tilt zero)
            acceleration: Acceleration for this saccade
            max_velocity: Max velocity for this saccade
        """
        if not self.connected:
            print("Error: Not connected to device", file=sys.stderr)
            return False
        
        try:
            # Calculate absolute positions
            pan_target = self.pan_zero + x
            tilt_target = self.tilt_zero + y
            
            print(f"Executing saccade to ({x}°, {y}°)")
            print(f"  Absolute positions: Pan={pan_target}°, Tilt={tilt_target}°")
            print(f"  Acceleration: {acceleration}°/s²")
            print(f"  Max velocity: {max_velocity}°/s")
            
            # Reconfigure servos with new parameters if needed
            self.configure_servo(PAN_CHANNEL, acceleration, max_velocity)
            self.configure_servo(TILT_CHANNEL, acceleration, max_velocity)
            
            # Ensure servos are engaged
            self.servo.setEngaged(PAN_CHANNEL, True)
            self.servo.setEngaged(TILT_CHANNEL, True)
            
            # Execute simultaneous movement to target position
            self.servo.setPosition(PAN_CHANNEL, pan_target)
            self.servo.setPosition(TILT_CHANNEL, tilt_target)
            
            print("Saccade complete")
            return True
            
        except PhidgetException as e:
            print(f"Error during saccade: {e}", file=sys.stderr)
            return False
    
    def get_current_position(self):
        """Get current servo positions relative to zero."""
        try:
            pan_abs = self.servo.getPosition(PAN_CHANNEL)
            tilt_abs = self.servo.getPosition(TILT_CHANNEL)
            
            # Convert to relative positions
            pan_rel = pan_abs - self.pan_zero
            tilt_rel = tilt_abs - self.tilt_zero
            
            return pan_rel, tilt_rel
        except PhidgetException as e:
            print(f"Error reading position: {e}", file=sys.stderr)
            return None, None
    
    def disengage(self):
        """Disengage (power off) the servos."""
        if self.connected:
            try:
                self.servo.setEngaged(PAN_CHANNEL, False)
                self.servo.setEngaged(TILT_CHANNEL, False)
                print("Servos disengaged")
            except PhidgetException as e:
                print(f"Error disengaging servos: {e}", file=sys.stderr)
    
    def close(self):
        """Close connection to the Phidget device."""
        if self.connected:
            try:
                self.servo.closePhidget()
                self.connected = False
                print("Connection closed")
            except PhidgetException:
                pass


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Saccade Control System for Servo-based Eye Movement',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize servos to default zero position (90°, 90°)
  %(prog)s init
  
  # Initialize with custom zero positions
  %(prog)s init --pan-zero 100 --tilt-zero 85
  
  # Perform saccade to (10°, -5°) with default parameters
  %(prog)s saccade 10 -5
  
  # Saccade with custom velocity and acceleration
  %(prog)s saccade 15 20 --velocity 500 --acceleration 3000
  
  # Get current position
  %(prog)s position
  
  # Disengage servos (power off)
  %(prog)s disengage
        """
    )
    
    # Global options
    parser.add_argument('--pan-zero', type=float, default=90.0,
                        help='Zero position for pan servo in degrees (default: 90)')
    parser.add_argument('--tilt-zero', type=float, default=90.0,
                        help='Zero position for tilt servo in degrees (default: 90)')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Initialize command
    init_parser = subparsers.add_parser('init', help='Initialize servos to zero position')
    init_parser.add_argument('--acceleration', type=float, default=DEFAULT_ACCELERATION,
                            help=f'Acceleration in deg/s² (default: {DEFAULT_ACCELERATION})')
    init_parser.add_argument('--velocity', type=float, default=DEFAULT_MAX_VELOCITY,
                            help=f'Max velocity in deg/s (default: {DEFAULT_MAX_VELOCITY})')
    
    # Saccade command
    saccade_parser = subparsers.add_parser('saccade', help='Perform saccade to target position')
    saccade_parser.add_argument('x', type=float,
                               help='Target X position in degrees (relative to zero)')
    saccade_parser.add_argument('y', type=float,
                               help='Target Y position in degrees (relative to zero)')
    saccade_parser.add_argument('--acceleration', type=float, default=DEFAULT_ACCELERATION,
                               help=f'Acceleration in deg/s² (default: {DEFAULT_ACCELERATION})')
    saccade_parser.add_argument('--velocity', type=float, default=DEFAULT_MAX_VELOCITY,
                               help=f'Max velocity in deg/s (default: {DEFAULT_MAX_VELOCITY})')
    
    # Position command
    position_parser = subparsers.add_parser('position', help='Get current position')
    
    # Disengage command
    disengage_parser = subparsers.add_parser('disengage', help='Disengage (power off) servos')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Create controller
    controller = SaccadeController(pan_zero=args.pan_zero, tilt_zero=args.tilt_zero)
    
    try:
        # Connect to device
        if not controller.connect():
            return 1
        
        # Execute command
        if args.command == 'init':
            success = controller.initialize(
                acceleration=args.acceleration,
                max_velocity=args.velocity
            )
            return 0 if success else 1
            
        elif args.command == 'saccade':
            success = controller.saccade(
                x=args.x,
                y=args.y,
                acceleration=args.acceleration,
                max_velocity=args.velocity
            )
            return 0 if success else 1
            
        elif args.command == 'position':
            x, y = controller.get_current_position()
            if x is not None and y is not None:
                print(f"Current position: X={x:.2f}°, Y={y:.2f}°")
                return 0
            return 1
            
        elif args.command == 'disengage':
            controller.disengage()
            return 0
    
    finally:
        # Always clean up
        controller.close()


if __name__ == '__main__':
    sys.exit(main())

