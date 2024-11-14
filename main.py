import logging
from opcua import Server, ua
import time
import threading

# Configure logging
logging.basicConfig(level=logging.DEBUG)

ENDPOINT = "opc.tcp://127.0.0.1:4840/server/"

class Motor:
    def __init__(self, name):
        self.name = name
        self.speed = 0
        self.actualSpeed = 0
        self.status = False
        self.lock = threading.Lock()

    def start(self, speed):
        with self.lock:
            self.speed = speed.Value if isinstance(speed, ua.Variant) else speed
            self.status = True
            threading.Thread(target=self.ramp_speed, args=(self.speed,)).start()

    def stop(self):
        with self.lock:
            self.status = False
            threading.Thread(target=self.ramp_speed, args=(0,)).start()

    def ramp_speed(self, target_speed):
        target_speed = target_speed.Value if isinstance(target_speed, ua.Variant) else target_speed
        try:
            while self.actualSpeed != target_speed:
                time.sleep(0.1)
                with self.lock:
                    if self.actualSpeed < target_speed:
                        self.actualSpeed += 1
                    elif self.actualSpeed > target_speed:
                        self.actualSpeed -= 1
        except Exception as e:
            logging.error(f"Error in ramp_speed: {e}")

def create_motor_node(server, idx, motor, parent):
    motor_node = parent.add_object(idx, motor.name)
    
    actual_speed_var = motor_node.add_variable(idx, "ActualSpeed", motor.actualSpeed, ua.VariantType.Int32)
    actual_speed_var.set_writable()  # Allow writing to this variable if needed
    
    status_var = motor_node.add_variable(idx, "Status", motor.status, ua.VariantType.Boolean)
    status_var.set_writable()  # Allow writing to this variable if needed
    
    motor_node.add_method(idx, "Start", lambda parent, speed: motor.start(speed), [ua.VariantType.Int32], [])
    motor_node.add_method(idx, "Stop", lambda parent: motor.stop())
    
    logging.debug(f"Created motor node for {motor.name} with ActualSpeed, Status, Start, and Stop methods")
    return motor_node

if __name__ == "__main__":
    server = Server()
    server.set_endpoint(ENDPOINT)
    idx = server.register_namespace("http://examples.freeopcua.github.io")

    # Create a "Demo" folder
    demo_folder = server.nodes.objects.add_folder(idx, "Demo")

    motors = [Motor(f"Motor{i}") for i in range(5)]
    motor_nodes = [create_motor_node(server, idx, motor, demo_folder) for motor in motors]

    server.start()
    logging.info(f"Server started at {ENDPOINT}")

    try:
        for motor_node in motor_nodes:
            logging.debug(f"Children of {motor_node}: {[child for child in motor_node.get_children()]}")

        while True:
            time.sleep(1)
            for motor, motor_node in zip(motors, motor_nodes):
                try:
                    actual_speed_node = motor_node.get_child("2:ActualSpeed")
                    status_node = motor_node.get_child("2:Status")
                    
                    actual_speed_node.set_value(motor.actualSpeed)
                    status_node.set_value(motor.status)
                except Exception as e:
                    logging.error(f"Error updating motor node: {e}")
    finally:
        server.stop()