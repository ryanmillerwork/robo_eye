# Import the AdvancedServo class to control Phidget servo motors
from Phidgets.Devices.AdvancedServo import AdvancedServo
# Import PhidgetException for error handling
from Phidgets.PhidgetException import PhidgetException
# Import time module for adding delays between servo movements
import time

# Create an instance of the AdvancedServo object to control the servo device
srv = AdvancedServo()
# Begin try block to ensure proper cleanup even if errors occur
try:
    # Open a connection to the Phidget device
    srv.openPhidget()
    # Wait up to 5000 milliseconds (5 seconds) for the device to be physically attached
    srv.waitForAttach(5000)
    # Print confirmation message showing device name and serial number
    print("Attached:", srv.getDeviceName(), "SN:", srv.getSerialNum())

    # Loop through servo channels 0 and 1 (2 servos total)
    for ch in range(0, 2):
        # Enable speed ramping for smooth acceleration/deceleration on this channel
        srv.setSpeedRampingOn(ch, True)
        # Set the acceleration rate to 50.0 degrees per second squared
        srv.setAcceleration(ch, 50.0)
        # Set the maximum velocity limit to 100.0 degrees per second
        srv.setVelocityLimit(ch, 100.0)

        # Engage (power on) the servo motor for this channel
        srv.setEngaged(ch, True)
        # Move servo to 90 degrees position, then wait 1 second
        srv.setPosition(ch, 90.0);  time.sleep(1)
        # Move servo to 45 degrees position, then wait 1 second
        srv.setPosition(ch, 45.0);  time.sleep(1)
        # Disengage (power off) the servo motor for this channel
        srv.setEngaged(ch, False)

# Finally block ensures cleanup code runs regardless of success or failure
finally:
    # Begin inner try block for safe device closing
    try:
        # Close the connection to the Phidget device
        srv.closePhidget()
    # Catch any PhidgetException that occurs during closing
    except PhidgetException:
        # Silently ignore exceptions when closing (device may already be disconnected)
        pass
