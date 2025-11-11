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
import csv
from datetime import datetime
import threading

# Import readline for command history and tab completion
try:
    import readline
    HAS_READLINE = True
except ImportError:
    HAS_READLINE = False


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
    
    def __init__(self, pan_zero=97.0, tilt_zero=93.0):
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
        self.profiling = False
        self.profile_data = []
    
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
            x: Target X position in degrees (relative to pan zero, positive = right)
            y: Target Y position in degrees (relative to tilt zero, positive = up)
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
            # Calculate absolute positions (negate for correct axis directions)
            # Positive x = right = decreasing pan angle
            # Positive y = up = decreasing tilt angle
            pan_target = self.pan_zero - x
            tilt_target = self.tilt_zero - y
            
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
        """Get current servo positions relative to zero (positive x=right, positive y=up)."""
        try:
            pan_abs = self.servo.getPosition(PAN_CHANNEL)
            tilt_abs = self.servo.getPosition(TILT_CHANNEL)
            
            # Convert to relative positions (negate for correct axis directions)
            pan_rel = self.pan_zero - pan_abs
            tilt_rel = self.tilt_zero - tilt_abs
            
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
            x: Relative X position in degrees (positive = right)
            y: Relative Y position in degrees (positive = up)
            
        Returns:
            Tuple of (valid, error_message)
        """
        limits = self.get_position_limits()
        if limits is None:
            return False, "Unable to read position limits"
        
        pan_min, pan_max, tilt_min, tilt_max = limits
        
        # Calculate absolute target positions (negate for correct axis directions)
        pan_target = self.pan_zero - x
        tilt_target = self.tilt_zero - y
        
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
    
    def _profile_thread(self, target_x, target_y, sample_rate_hz=100):
        """
        Background thread to sample position and velocity during movement.
        
        Args:
            target_x: Target X position (relative, positive = right)
            target_y: Target Y position (relative, positive = up)
            sample_rate_hz: Sampling frequency in Hz
        """
        sample_interval = 1.0 / sample_rate_hz
        start_time = time.time()
        target_pan = self.pan_zero - target_x
        target_tilt = self.tilt_zero - target_y
        
        # Tolerance for considering we've reached target (degrees)
        position_tolerance = 0.5
        
        while self.profiling:
            try:
                current_time = time.time() - start_time
                
                # Read positions
                pan_pos = self.servo.getPosition(PAN_CHANNEL)
                tilt_pos = self.servo.getPosition(TILT_CHANNEL)
                
                # Try to read velocities (may not be supported on all devices)
                try:
                    pan_vel = self.servo.getVelocity(PAN_CHANNEL)
                    tilt_vel = self.servo.getVelocity(TILT_CHANNEL)
                except:
                    pan_vel = None
                    tilt_vel = None
                
                # Negate velocities to match axis directions (positive x=right, y=up)
                if pan_vel is not None:
                    pan_vel = -pan_vel
                if tilt_vel is not None:
                    tilt_vel = -tilt_vel
                
                # Convert to relative positions (negate for correct axis directions)
                pan_rel = self.pan_zero - pan_pos
                tilt_rel = self.tilt_zero - tilt_pos
                
                # Record data
                self.profile_data.append({
                    'time': current_time,
                    'pan_abs': pan_pos,
                    'tilt_abs': tilt_pos,
                    'pan_rel': pan_rel,
                    'tilt_rel': tilt_rel,
                    'pan_vel': pan_vel,
                    'tilt_vel': tilt_vel
                })
                
                # Check if we've reached target
                pan_error = abs(pan_pos - target_pan)
                tilt_error = abs(tilt_pos - target_tilt)
                
                if pan_error < position_tolerance and tilt_error < position_tolerance:
                    # Wait a bit more to capture settling
                    time.sleep(0.1)
                    break
                
                time.sleep(sample_interval)
                
            except PhidgetException:
                break
        
        self.profiling = False
    
    def saccade_with_profile(self, x, y, acceleration=DEFAULT_ACCELERATION, 
                            max_velocity=DEFAULT_MAX_VELOCITY, sample_rate_hz=100):
        """
        Perform a saccade while recording motion profile data.
        
        Args:
            x: Target X position in degrees (relative to pan zero, positive = right)
            y: Target Y position in degrees (relative to tilt zero, positive = up)
            acceleration: Acceleration for this saccade
            max_velocity: Max velocity for this saccade
            sample_rate_hz: Sampling frequency for profiling
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            print("Error: Not connected to device", file=sys.stderr)
            return False
        
        # Check position limits
        valid, error_msg = self.check_position_valid(x, y)
        if not valid:
            print(f"Error: Position out of range - {error_msg}", file=sys.stderr)
            return False
        
        # Clear previous profile data
        self.profile_data = []
        
        try:
            # Calculate absolute positions (negate for correct axis directions)
            pan_target = self.pan_zero - x
            tilt_target = self.tilt_zero - y
            
            print(f"Executing profiled saccade to ({x}°, {y}°)")
            print(f"  Absolute positions: Pan={pan_target}°, Tilt={tilt_target}°")
            print(f"  Acceleration: {acceleration}°/s²")
            print(f"  Max velocity: {max_velocity}°/s")
            print(f"  Sampling at {sample_rate_hz} Hz")
            
            # Configure servos
            self.configure_servo(PAN_CHANNEL, acceleration, max_velocity)
            self.configure_servo(TILT_CHANNEL, acceleration, max_velocity)
            
            # Ensure servos are engaged
            self.servo.setEngaged(PAN_CHANNEL, True)
            self.servo.setEngaged(TILT_CHANNEL, True)
            
            # Start profiling thread
            self.profiling = True
            profile_thread = threading.Thread(
                target=self._profile_thread,
                args=(x, y, sample_rate_hz)
            )
            profile_thread.start()
            
            # Small delay to ensure thread is ready
            time.sleep(0.01)
            
            # Execute movement
            self.servo.setPosition(PAN_CHANNEL, pan_target)
            self.servo.setPosition(TILT_CHANNEL, tilt_target)
            
            # Wait for profiling to complete
            profile_thread.join(timeout=10.0)
            self.profiling = False
            
            print(f"Saccade complete - captured {len(self.profile_data)} samples")
            
            # Analyze and display profile
            self._analyze_profile(x, y, acceleration, max_velocity)
            
            return True
            
        except PhidgetException as e:
            self.profiling = False
            print(f"Error during saccade: {e}", file=sys.stderr)
            return False
    
    def _smooth_data(self, data, window=3):
        """Apply simple moving average smoothing."""
        if len(data) < window:
            return data
        smoothed = []
        for i in range(len(data)):
            start = max(0, i - window // 2)
            end = min(len(data), i + window // 2 + 1)
            smoothed.append(sum(data[start:end]) / (end - start))
        return smoothed
    
    def _analyze_profile(self, target_x, target_y, commanded_accel, commanded_vel):
        """
        Analyze the recorded profile data and display statistics.
        
        Args:
            target_x: Commanded target X position
            target_y: Commanded target Y position
            commanded_accel: Commanded acceleration
            commanded_vel: Commanded max velocity
        """
        if not self.profile_data:
            print("No profile data to analyze")
            return
        
        # Calculate statistics
        duration = self.profile_data[-1]['time'] - self.profile_data[0]['time']
        
        # Extract velocity data
        times = [d['time'] for d in self.profile_data]
        pan_velocities = [d['pan_vel'] if d['pan_vel'] is not None else None for d in self.profile_data]
        tilt_velocities = [d['tilt_vel'] if d['tilt_vel'] is not None else None for d in self.profile_data]
        
        # Check if we have velocity data from device
        has_device_velocity = any(v is not None for v in pan_velocities)
        
        # Calculate or estimate velocities
        if not has_device_velocity:
            # Estimate from position
            pan_velocities = [None]
            tilt_velocities = [None]
            for i in range(1, len(self.profile_data)):
                dt = self.profile_data[i]['time'] - self.profile_data[i-1]['time']
                if dt > 0:
                    dp = self.profile_data[i]['pan_rel'] - self.profile_data[i-1]['pan_rel']
                    dt_pan = self.profile_data[i]['tilt_rel'] - self.profile_data[i-1]['tilt_rel']
                    pan_velocities.append(dp / dt)
                    tilt_velocities.append(dt_pan / dt)
                else:
                    pan_velocities.append(None)
                    tilt_velocities.append(None)
        
        # Filter out None values
        pan_vels_clean = [v for v in pan_velocities if v is not None]
        tilt_vels_clean = [v for v in tilt_velocities if v is not None]
        
        peak_pan_vel = max(abs(v) for v in pan_vels_clean) if pan_vels_clean else None
        peak_tilt_vel = max(abs(v) for v in tilt_vels_clean) if tilt_vels_clean else None
        
        # Calculate accelerations with smoothing
        peak_pan_accel = None
        peak_tilt_accel = None
        avg_pan_accel = None
        avg_tilt_accel = None
        
        if len(pan_vels_clean) > 3:
            # Smooth velocities to reduce noise in acceleration calculation
            smoothed_pan_vel = self._smooth_data(pan_vels_clean, window=5)
            
            # Calculate acceleration from smoothed velocity
            pan_accels = []
            for i in range(1, len(smoothed_pan_vel)):
                # Use original time intervals
                valid_indices = [j for j, v in enumerate(pan_velocities) if v is not None]
                if i < len(valid_indices):
                    dt = times[valid_indices[i]] - times[valid_indices[i-1]]
                    if dt > 0:
                        dv = smoothed_pan_vel[i] - smoothed_pan_vel[i-1]
                        pan_accels.append(abs(dv / dt))
            
            if pan_accels:
                # Sort and take 90th percentile to avoid noise spikes
                pan_accels_sorted = sorted(pan_accels)
                idx_90 = int(len(pan_accels_sorted) * 0.9)
                peak_pan_accel = pan_accels_sorted[idx_90] if idx_90 < len(pan_accels_sorted) else pan_accels_sorted[-1]
                # Average acceleration during main movement (middle 80%)
                start_idx = int(len(pan_accels) * 0.1)
                end_idx = int(len(pan_accels) * 0.9)
                if end_idx > start_idx:
                    avg_pan_accel = sum(pan_accels[start_idx:end_idx]) / (end_idx - start_idx)
        
        if len(tilt_vels_clean) > 3:
            # Smooth velocities to reduce noise in acceleration calculation
            smoothed_tilt_vel = self._smooth_data(tilt_vels_clean, window=5)
            
            # Calculate acceleration from smoothed velocity
            tilt_accels = []
            for i in range(1, len(smoothed_tilt_vel)):
                # Use original time intervals
                valid_indices = [j for j, v in enumerate(tilt_velocities) if v is not None]
                if i < len(valid_indices):
                    dt = times[valid_indices[i]] - times[valid_indices[i-1]]
                    if dt > 0:
                        dv = smoothed_tilt_vel[i] - smoothed_tilt_vel[i-1]
                        tilt_accels.append(abs(dv / dt))
            
            if tilt_accels:
                # Sort and take 90th percentile to avoid noise spikes
                tilt_accels_sorted = sorted(tilt_accels)
                idx_90 = int(len(tilt_accels_sorted) * 0.9)
                peak_tilt_accel = tilt_accels_sorted[idx_90] if idx_90 < len(tilt_accels_sorted) else tilt_accels_sorted[-1]
                # Average acceleration during main movement (middle 80%)
                start_idx = int(len(tilt_accels) * 0.1)
                end_idx = int(len(tilt_accels) * 0.9)
                if end_idx > start_idx:
                    avg_tilt_accel = sum(tilt_accels[start_idx:end_idx]) / (end_idx - start_idx)
        
        # Final positions
        final_pan = self.profile_data[-1]['pan_rel']
        final_tilt = self.profile_data[-1]['tilt_rel']
        
        # Position error
        pan_error = final_pan - target_x
        tilt_error = final_tilt - target_y
        
        print("\n" + "="*60)
        print("Motion Profile Analysis")
        print("="*60)
        print(f"Duration: {duration*1000:.1f} ms")
        print(f"Samples: {len(self.profile_data)}")
        print(f"\nCommanded:")
        print(f"  Target: ({target_x:.2f}°, {target_y:.2f}°)")
        print(f"  Max velocity: {commanded_vel:.1f}°/s")
        print(f"  Acceleration: {commanded_accel:.1f}°/s²")
        print(f"\nActual:")
        print(f"  Final position: ({final_pan:.2f}°, {final_tilt:.2f}°)")
        print(f"  Position error: ({pan_error:.2f}°, {tilt_error:.2f}°)")
        
        if peak_pan_vel is not None:
            print(f"  Peak pan velocity: {peak_pan_vel:.1f}°/s")
        if peak_tilt_vel is not None:
            print(f"  Peak tilt velocity: {peak_tilt_vel:.1f}°/s")
        
        if peak_pan_accel is not None:
            print(f"  Peak pan accel (90th %ile): {peak_pan_accel:.1f}°/s²")
        if avg_pan_accel is not None:
            print(f"  Avg pan accel: {avg_pan_accel:.1f}°/s²")
        if peak_tilt_accel is not None:
            print(f"  Peak tilt accel (90th %ile): {peak_tilt_accel:.1f}°/s²")
        if avg_tilt_accel is not None:
            print(f"  Avg tilt accel: {avg_tilt_accel:.1f}°/s²")
        
        if not has_device_velocity:
            print("\n  Note: Velocity/acceleration estimated from position")
            print("        (smoothed with 5-point moving average)")
        
        print("="*60 + "\n")
    
    def save_profile(self, filename=None):
        """
        Save the most recent profile data to a CSV file.
        
        Args:
            filename: Output filename (auto-generated if None)
            
        Returns:
            The filename used, or None if no data to save
        """
        if not self.profile_data:
            print("No profile data to save")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"saccade_profile_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='') as f:
                fieldnames = ['time', 'pan_abs', 'tilt_abs', 'pan_rel', 'tilt_rel', 
                            'pan_vel', 'tilt_vel']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.profile_data)
            
            print(f"Profile data saved to: {filename}")
            return filename
            
        except IOError as e:
            print(f"Error saving profile: {e}", file=sys.stderr)
            return None


class CommandCompleter:
    """Tab completion for interactive commands."""
    
    def __init__(self):
        self.commands = [
            'saccade', 'profile', 'save', 'position', 
            'limits', 'zero', 'disengage', 'engage', 'help', 'quit', 'exit'
        ]
    
    def complete(self, text, state):
        """Return the next possible completion for 'text'."""
        # Get the entire line buffer
        line = readline.get_line_buffer()
        
        # If we're completing the first word (command)
        if not line or line.lstrip() == text:
            options = [cmd for cmd in self.commands if cmd.startswith(text)]
        else:
            # For subsequent words, could add context-specific completion here
            options = []
        
        if state < len(options):
            return options[state]
        return None


def setup_readline():
    """Configure readline for command history and tab completion."""
    if not HAS_READLINE:
        return
    
    # Set up tab completion
    completer = CommandCompleter()
    readline.set_completer(completer.complete)
    readline.parse_and_bind('tab: complete')
    
    # Set up history
    readline.set_history_length(1000)
    
    # Enable better word breaking for tab completion
    readline.set_completer_delims(' \t\n')


def interactive_mode(controller):
    """
    Run interactive command loop for issuing saccade commands.
    
    Args:
        controller: SaccadeController instance
    """
    # Set up readline for history and tab completion
    setup_readline()
    
    print("\n" + "="*60)
    print("Saccade Control System - Interactive Mode")
    print("="*60)
    print("\nAvailable commands:")
    print("  saccade <x> <y> [accel] [velocity]  - Perform saccade")
    print("  profile <x> <y> [accel] [velocity]  - Profiled saccade (records motion)")
    print("  save [filename]                      - Save last profile to CSV")
    print("  position                             - Show current position")
    print("  limits                               - Show servo position limits")
    print("  zero                                 - Return to zero position")
    print("  disengage                            - Power off servos")
    print("  engage                               - Power on servos")
    print("  help                                 - Show this help message")
    print("  quit / exit                          - Exit program")
    print(f"\nDefaults: accel={DEFAULT_ACCELERATION}°/s², velocity={DEFAULT_MAX_VELOCITY}°/s")
    if HAS_READLINE:
        print("\nTip: Use ↑/↓ arrows for history, Tab for command completion")
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
                print("  profile <x> <y> [accel] [velocity]  - Profiled saccade (records motion data)")
                print("  save [filename]                      - Save last profile to CSV file")
                print("  position                             - Display current position")
                print("  limits                               - Show servo position limits")
                print("  zero                                 - Return to zero position")
                print("  disengage                            - Power off servos")
                print("  engage                               - Power on servos")
                print("  quit / exit                          - Exit program")
                if HAS_READLINE:
                    print("\nTips:")
                    print("  - Use ↑/↓ arrow keys to navigate command history")
                    print("  - Press Tab to autocomplete commands")
                print()
            
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
            
            elif command == 'profile':
                if len(parts) < 3:
                    print("Error: profile requires x and y positions")
                    print("Usage: profile <x> <y> [accel] [velocity]")
                    continue
                
                try:
                    x = float(parts[1])
                    y = float(parts[2])
                    accel = float(parts[3]) if len(parts) > 3 else DEFAULT_ACCELERATION
                    velocity = float(parts[4]) if len(parts) > 4 else DEFAULT_MAX_VELOCITY
                    
                    controller.saccade_with_profile(x, y, acceleration=accel, max_velocity=velocity)
                except ValueError:
                    print("Error: Invalid numeric values")
            
            elif command == 'save':
                filename = parts[1] if len(parts) > 1 else None
                controller.save_profile(filename)
            
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
                    # Negate for correct axis directions (positive x=right, positive y=up)
                    print(f"  Pan (X):  {controller.pan_zero-pan_max:.1f}° to {controller.pan_zero-pan_min:.1f}° (left to right)")
                    print(f"  Tilt (Y): {controller.tilt_zero-tilt_max:.1f}° to {controller.tilt_zero-tilt_min:.1f}° (down to up)")
            
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
  # Start with default zero position (97°, 93°)
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
    parser.add_argument('--pan-zero', type=float, default=97.0,
                        help='Zero position for pan servo in degrees (default: 97)')
    parser.add_argument('--tilt-zero', type=float, default=93.0,
                        help='Zero position for tilt servo in degrees (default: 93)')
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

