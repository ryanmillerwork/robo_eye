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
    
    def saccade(self, x, y, acceleration=DEFAULT_ACCELERATION, max_velocity=DEFAULT_MAX_VELOCITY, check_limits=True):
        """
        Perform a saccade to the specified position.
        
        Args:
            x: Target X position in degrees (relative to pan zero)
            y: Target Y position in degrees (relative to tilt zero)
            acceleration: Acceleration for this saccade
            max_velocity: Max velocity for this saccade
            check_limits: Whether to check position limits before moving
        """
        if not self.connected:
            print("Error: Not connected to device", file=sys.stderr)
            return False
        
        # Check if position is within limits
        if check_limits:
            valid, error_msg = self.check_position_valid(x, y)
            if not valid:
                print(f"Error: Position out of range - {error_msg}", file=sys.stderr)
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
    
    def get_position_limits(self):
        """
        Get the position limits for both servos.
        
        Returns:
            Tuple of (pan_min, pan_max, tilt_min, tilt_max) in absolute degrees,
            or None if error occurs
        """
        try:
            pan_min = self.servo.getPositionMin(PAN_CHANNEL)
            pan_max = self.servo.getPositionMax(PAN_CHANNEL)
            tilt_min = self.servo.getPositionMin(TILT_CHANNEL)
            tilt_max = self.servo.getPositionMax(TILT_CHANNEL)
            
            return pan_min, pan_max, tilt_min, tilt_max
        except PhidgetException as e:
            print(f"Error reading position limits: {e}", file=sys.stderr)
            return None
    
    def check_position_valid(self, x, y):
        """
        Check if a relative position (x, y) is within servo limits.
        
        Args:
            x: Relative X position in degrees
            y: Relative Y position in degrees
            
        Returns:
            Tuple of (valid, error_message)
        """
        limits = self.get_position_limits()
        if limits is None:
            return False, "Unable to read position limits"
        
        pan_min, pan_max, tilt_min, tilt_max = limits
        
        # Calculate absolute target positions
        pan_target = self.pan_zero + x
        tilt_target = self.tilt_zero + y
        
        errors = []
        
        # Check pan limits
        if pan_target < pan_min:
            errors.append(f"Pan position {pan_target:.1f}° below minimum {pan_min:.1f}°")
        elif pan_target > pan_max:
            errors.append(f"Pan position {pan_target:.1f}° above maximum {pan_max:.1f}°")
        
        # Check tilt limits
        if tilt_target < tilt_min:
            errors.append(f"Tilt position {tilt_target:.1f}° below minimum {tilt_min:.1f}°")
        elif tilt_target > tilt_max:
            errors.append(f"Tilt position {tilt_target:.1f}° above maximum {tilt_max:.1f}°")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, None
    
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


def interactive_mode(controller):
    """
    Run interactive command loop for issuing saccade commands.
    
    Args:
        controller: SaccadeController instance
    """
    print("\n" + "="*60)
    print("Saccade Control System - Interactive Mode")
    print("="*60)
    print("\nAvailable commands:")
    print("  saccade <x> <y> [accel] [velocity]  - Perform saccade")
    print("  position                             - Show current position")
    print("  limits                               - Show servo position limits")
    print("  zero                                 - Return to zero position")
    print("  disengage                            - Power off servos")
    print("  engage                               - Power on servos")
    print("  help                                 - Show this help message")
    print("  quit / exit                          - Exit program")
    print(f"\nDefaults: accel={DEFAULT_ACCELERATION}°/s², velocity={DEFAULT_MAX_VELOCITY}°/s")
    print("="*60 + "\n")
    
    while True:
        try:
            # Get user input
            user_input = input("saccade> ").strip()
            
            if not user_input:
                continue
            
            # Parse command
            parts = user_input.split()
            command = parts[0].lower()
            
            if command in ['quit', 'exit', 'q']:
                print("Exiting...")
                break
            
            elif command == 'help':
                print("\nCommands:")
                print("  saccade <x> <y> [accel] [velocity]  - Move to position (x,y) in degrees")
                print("  position                             - Display current position")
                print("  limits                               - Show servo position limits")
                print("  zero                                 - Return to zero position")
                print("  disengage                            - Power off servos")
                print("  engage                               - Power on servos")
                print("  quit / exit                          - Exit program\n")
            
            elif command == 'saccade':
                if len(parts) < 3:
                    print("Error: saccade requires x and y positions")
                    print("Usage: saccade <x> <y> [accel] [velocity]")
                    continue
                
                try:
                    x = float(parts[1])
                    y = float(parts[2])
                    accel = float(parts[3]) if len(parts) > 3 else DEFAULT_ACCELERATION
                    velocity = float(parts[4]) if len(parts) > 4 else DEFAULT_MAX_VELOCITY
                    
                    controller.saccade(x, y, acceleration=accel, max_velocity=velocity)
                except ValueError:
                    print("Error: Invalid numeric values")
            
            elif command == 'position':
                x, y = controller.get_current_position()
                if x is not None and y is not None:
                    print(f"Current position: X={x:.2f}°, Y={y:.2f}°")
            
            elif command == 'limits':
                limits = controller.get_position_limits()
                if limits:
                    pan_min, pan_max, tilt_min, tilt_max = limits
                    print(f"\nServo Position Limits (Absolute):")
                    print(f"  Pan (X):  {pan_min:.1f}° to {pan_max:.1f}° (range: {pan_max-pan_min:.1f}°)")
                    print(f"  Tilt (Y): {tilt_min:.1f}° to {tilt_max:.1f}° (range: {tilt_max-tilt_min:.1f}°)")
                    print(f"\nRelative to Zero Position (Pan={controller.pan_zero}°, Tilt={controller.tilt_zero}°):")
                    print(f"  Pan (X):  {pan_min-controller.pan_zero:.1f}° to {pan_max-controller.pan_zero:.1f}°")
                    print(f"  Tilt (Y): {tilt_min-controller.tilt_zero:.1f}° to {tilt_max-controller.tilt_zero:.1f}°")
            
            elif command == 'zero':
                print("Returning to zero position...")
                controller.saccade(0, 0)
            
            elif command == 'disengage':
                controller.disengage()
            
            elif command == 'engage':
                try:
                    controller.servo.setEngaged(PAN_CHANNEL, True)
                    controller.servo.setEngaged(TILT_CHANNEL, True)
                    print("Servos engaged")
                except PhidgetException as e:
                    print(f"Error engaging servos: {e}", file=sys.stderr)
            
            else:
                print(f"Unknown command: {command}")
                print("Type 'help' for available commands")
        
        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'quit' to exit.")
        except EOFError:
            print("\nExiting...")
            break


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Saccade Control System for Servo-based Eye Movement',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The program will connect to the Phidget device, initialize the servos,
and then enter an interactive mode where you can issue saccade commands
immediately without reconnection delays.

Examples:
  # Start with default zero position (90°, 90°)
  %(prog)s
  
  # Start with custom zero positions
  %(prog)s --pan-zero 100 --tilt-zero 85
  
  # Specify custom default acceleration and velocity
  %(prog)s --acceleration 3000 --velocity 500

Once in interactive mode:
  saccade 10 -5           # Saccade to (10°, -5°)
  saccade 15 20 3000 500  # Saccade with custom accel/velocity
  position                # Show current position
  zero                    # Return to zero
  quit                    # Exit
        """
    )
    
    # Global options
    parser.add_argument('--pan-zero', type=float, default=90.0,
                        help='Zero position for pan servo in degrees (default: 90)')
    parser.add_argument('--tilt-zero', type=float, default=90.0,
                        help='Zero position for tilt servo in degrees (default: 90)')
    parser.add_argument('--acceleration', type=float, default=DEFAULT_ACCELERATION,
                        help=f'Default acceleration in deg/s² (default: {DEFAULT_ACCELERATION})')
    parser.add_argument('--velocity', type=float, default=DEFAULT_MAX_VELOCITY,
                        help=f'Default max velocity in deg/s (default: {DEFAULT_MAX_VELOCITY})')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create controller
    controller = SaccadeController(pan_zero=args.pan_zero, tilt_zero=args.tilt_zero)
    
    try:
        # Connect to device
        print("Connecting to Phidget device...")
        if not controller.connect():
            return 1
        
        # Initialize servos
        print("\nInitializing servos...")
        if not controller.initialize(acceleration=args.acceleration, max_velocity=args.velocity):
            return 1
        
        print("System ready!")
        
        # Enter interactive mode
        interactive_mode(controller)
        
        return 0
    
    finally:
        # Always clean up
        controller.close()


if __name__ == '__main__':
    sys.exit(main())

