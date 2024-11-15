import logging
from opcua import Server, ua, instantiate
import time
import threading
import random

# Configure logging
logging.basicConfig(level=logging.WARNING)

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

    def get_temperature(self):
        # Return a random value which simulates the temperature of the motor
        # If motor is running, temperature increases
        # If motor is stopped, temperature decreases
        # With some randomness to simulate real-world conditions
        base_value = 40 if self.status else 20
        return base_value + (self.actualSpeed / 100) + (0.5 - random.random())

def create_motor_type(server: Server, idx: int):
    # Create a new object type "MotorType" under the server's base object type node
    motor_type = server.nodes.base_object_type.add_object_type(idx, "MotorType")

    # Add 'ActualSpeed' as an integer variable with modeling rule set to 'Mandatory'
    actual_speed = motor_type.add_variable(idx, "ActualSpeed", 0, ua.VariantType.Int32)
    actual_speed.set_modelling_rule("Mandatory")  # Ensures this variable is inherited by instances
    # actual_speed.write_attribute(ua.AttributeIds.AccessLevel, ua.AccessLevel.CurrentRead)  # Read-only
    # actual_speed.write_attribute(ua.AttributeIds.ValueRank, -1)  # Scalar value

    # Add 'Status' as a boolean variable with modeling rule set to 'Mandatory'
    status = motor_type.add_variable(idx, "Status", False, ua.VariantType.Boolean)
    status.set_modelling_rule("Mandatory")  # Ensures this variable is inherited by instances
    # status.write_attribute(ua.AttributeIds.AccessLevel, ua.AccessLevel.CurrentRead)  # Read-only
    # status.write_attribute(ua.AttributeIds.ValueRank, -1)  # Scalar value

    # Add 'Temperature' with Celsius as engineering unit and a EURange
    temperature = motor_type.add_variable(idx, "Temperature", 0.0, ua.VariantType.Double)
    temperature.set_modelling_rule("Mandatory")
    # temperature.write_attribute(ua.AttributeIds.AccessLevel, ua.AccessLevel.CurrentRead)  # Read-only
    # temperature.write_attribute(ua.AttributeIds.ValueRank, -1)  # Scalar value

    # Define the engineering unit as Celsius (EUInformation object with code 4408652)
    celsius_unit = ua.EUInformation()
    celsius_unit.NamespaceUri = "http://www.opcfoundation.org/UA/units/un/cefact"
    celsius_unit.UnitId = 4408652  # OPC UA-defined ID for degrees Celsius
    celsius_unit.DisplayName = ua.LocalizedText("°C")
    celsius_unit.Description = ua.LocalizedText("Celsius temperature unit")

    # Add Engineering Units property to the Temperature variable
    eng_units = temperature.add_property(idx, "EngineeringUnits", celsius_unit)
    eng_units.set_modelling_rule("Mandatory")

    # Define the EURange for the Temperature variable (-20 to +70)
    eu_range = ua.Range()
    eu_range.Low = 5.0
    eu_range.High = 50.0

    # Add EURange property to the Temperature variable
    temp_range = temperature.add_property(idx, "EURange", eu_range)
    temp_range.set_modelling_rule("Mandatory")

    # Define input arguments for the Start method
    input_args = [ua.Argument()]
    input_args[0].Name = "Speed"
    input_args[0].DataType = ua.NodeId(ua.ObjectIds.Int32)
    input_args[0].ValueRank = -1
    input_args[0].ArrayDimensions = []
    input_args[0].Description = ua.LocalizedText("Target speed of the motor")
    
    # Add methods with proper input arguments and metadata
    motor_type.add_method(idx, "Start", lambda parent, speed: None, input_args, [])
    motor_type.add_method(idx, "Stop", lambda parent: None)

    return motor_type

def create_motor_instance(server, idx, motor, parent, motor_type):
    motor_node = parent.add_object(idx, motor.name, objecttype=motor_type.nodeid)

    # Define input arguments for the Start method
    input_args = [ua.Argument()]
    input_args[0].Name = "Speed"
    input_args[0].DataType = ua.NodeId(ua.ObjectIds.Int32)
    input_args[0].ValueRank = -1
    input_args[0].ArrayDimensions = []
    input_args[0].Description = ua.LocalizedText("Target speed of the motor")

    # Add methods with proper input arguments and metadata
    motor_node.add_method(idx, "Start", lambda parent, speed: motor.start(speed), input_args, [])
    motor_node.add_method(idx, "Stop", lambda parent: motor.stop())
    
    logging.debug(f"Created motor instance for {motor.name} with ActualSpeed, Status, Start, and Stop methods")
    return motor_node

if __name__ == "__main__":
    server = Server()
    server.set_endpoint(ENDPOINT)
    idx = server.register_namespace("http://asemlucben.local")
    server.set_server_name("asemlucben Example Server")
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])

    # Create a "Demo" folder
    demo_folder = server.nodes.objects.add_folder(idx, "Demo")

    # Create 5 python instances of the Motor class
    motors = [Motor(f"Motor{i}") for i in range(5)]

    # Create MotorType
    motor_type = create_motor_type(server, idx)
    # Create motor instances
    motor_nodes = [create_motor_instance(server, idx, motor, demo_folder, motor_type) for motor in motors]

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
                    temperature_node = motor_node.get_child("2:Temperature")
                    
                    actual_speed_node.set_value(motor.actualSpeed)
                    status_node.set_value(motor.status)
                    temperature_node.set_value(motor.get_temperature())
                except Exception as e:
                    logging.error(f"Error updating motor node: {e}")

    finally:
        server.stop()