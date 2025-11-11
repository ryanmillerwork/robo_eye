from Phidgets.Devices.AdvancedServo import AdvancedServo
from Phidgets.PhidgetException import PhidgetException
import time

srv = AdvancedServo()
try:
    srv.openPhidget()
    srv.waitForAttach(5000)
    print("Attached:", srv.getDeviceName(), "SN:", srv.getSerialNum())

    ch = 0
    srv.setSpeedRampingOn(ch, True)
    srv.setAcceleration(ch, 50.0)
    srv.setVelocityLimit(ch, 100.0)

    srv.setEngaged(ch, True)
    srv.setPosition(ch, 90.0);  time.sleep(1)
    srv.setPosition(ch, 45.0);  time.sleep(1)
    srv.setEngaged(ch, False)

    ch = 1
    srv.setSpeedRampingOn(ch, True)
    srv.setAcceleration(ch, 50.0)
    srv.setVelocityLimit(ch, 100.0)

    srv.setEngaged(ch, True)
    srv.setPosition(ch, 90.0);  time.sleep(1)
    srv.setPosition(ch, 45.0);  time.sleep(1)
    srv.setEngaged(ch, False)

finally:
    try:
        srv.closePhidget()
    except PhidgetException:
        pass
