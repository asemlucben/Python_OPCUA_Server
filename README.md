# Python OPC UA Server

This project is a Python-based OPC UA server that simulates motor instances with attributes such as speed and status. The server allows clients to interact with the motor instances, start and stop them, and monitor their speed and status.

## Setup

1. **Clone the repository:**

```sh
git clone <repository-url>
cd <repository-directory>
```

2. **Create and activate a virtual environment:**

```sh
python -m venv venv
source venv/Scripts/activate  # On Windows
source venv/bin/activate      # On Unix or MacOS
```

3. **Install the required packages:**

```sh
pip install -r requirements.txt
```

## Running the Server

To start the OPC UA server, run the following command:

```sh
python ./main.py
```

The server will start and listen on `opc.tcp://127.0.0.1:4840/server/`.

## Code Overview
- `main.py`: The main script that sets up and runs the OPC UA server.
- `Motor` class: Represents a motor with attributes name, speed, actualSpeed, and status.
- `create_motor_type(server, idx)`: Creates a custom motor type in the OPC UA server.
- `create_motor_instance(server, idx, motor, parent, motor_type)`: Creates an instance of the motor type in the OPC UA server.

## Logging

The server uses Python's built-in logging module to log information and errors. The logging level is set to DEBUG to provide detailed output.

## License

This project is licensed under the GNU GPL V3 License.