from __future__ import print_function

import os
from serial import Serial
import sys


class CommandExecutor:
    def __init__(self, connection, retry_count=3):
        if retry_count <= 0:
            raise ValueError("retry_count must be greater than zero")

        if not connection.is_open:
            raise ValueError("connection must be open and connected")

        self.connection = connection
        self.retry_count = retry_count

    def execute(self, command, *args, **kargs):
        retries = 0

        def invoke_command():
            try:
                ## TODO: Add critical section protection here
                return True, command(self.connection, *args, **kargs)
            except Exception as e:
                print("Executing command {} resulted in an exception: {}".format(command.name, e.message))

                return False, None

        (ok, result) = invoke_command()

        while not ok and retries < self.retry_count:
            (status, result) = invoke_command()

            retries += 1

        return result


class Connection:
    def __init__(self, port="/dev/ttyACM0", baud_rate=9600, timeout=0.5):
        if os.access(port, os.R_OK):
            self.port = Serial(port=port, baudrate=baud_rate, timeout=timeout, write_timeout=timeout)
            print("Connecting to", port)
        else:
            raise Exception("port %s does not exists or user does not have permission to it" % port)

        self.timeout = timeout
        self.inter_char_timeout = timeout / 30.0

    @property
    def is_open(self):
        return self.port.is_open

    def open(self):
        if not self.port.is_open:
            self.port.open()

            print("Connection to port '{}' established".format(self.port.port))

    def clear(self):
        self.port.reset_input_buffer()

    def close(self):
        self.port.close()

        print("Connection to port '{}' closed".format(self.port.port))

    def write(self, message):
        return self.port.write(message)

    def write_line(self, message):
        return self.write(message + '\n')

    def read(self, timeout=0.5):
        timeout = min(timeout, self.timeout)
        c = ''
        value = ''
        attempts = 0

        while c != '\n':
            c = self.port.read(1)
            value += c
            attempts += 1

            if attempts * self.inter_char_timeout > timeout:
                return None

        return value.strip()

    def read_int(self, timeout=0.5):
        try:
            return int(self.read(timeout))
        except ValueError:
            return None


class Command:
    def __init__(self, name, command_function):
        self.name = name
        self.function = command_function

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)

    def __str__(self):
        return "[Command: %s, %s]" % (self.name, self.function)


class Arduino:
    def __init__(self, port, baud_rate=9600):
        self.connection = Connection(port, baud_rate=baud_rate)
        self.baud_rate = baud_rate

        self.connection.open()

        self.command_executor = CommandExecutor(self.connection)

        # Poll to see when the device is ready
        print("Testing reliability of connection...standby")
        to_echo = "OK"
        attempt = 0
        echoed_value_successfully = False

        while not echoed_value_successfully and attempt < 3:
            self.connection.clear()
            echoed_value = self.command_executor.execute(EchoCommand(), to_echo)
            echoed_value_successfully = echoed_value == to_echo
            attempt += 1

        if not echoed_value_successfully:
            self.close()

            raise Exception( "Did not get the expected result from the Arduino after %d attempts; a connection "
                             "could " "not be established" % attempt)

        print("Successfully established a connection to the Arduino")

        # Make sure the device and the client have the same baud rate
        try:
            print("Checking that the Arduino's baud rate is", baud_rate)

            actual_baud_rate = self.command_executor.execute(CheckBaudRateCommand(baud_rate))

            print("Baud rates match. Client = {}, Arduino's = {}".format(baud_rate, actual_baud_rate))
        except Exception as e:
            print("Could not connect to the Arduino:", e.message)

            self.close()

    # TODO: Replace with specific methods to do specific command
    def execute_command(self, command, *args, **kargs):
        return self.command_executor.execute(command, *args, **kargs)

    def close(self):
        if self.connection.is_open:
            self.connection.close()


class EchoCommand(Command):
    name = "e"

    def __init__(self):
        def echo(connection, to_echo):
            write_failed = True
            expected_write_length = len(EchoCommand.name)

            if connection.write(EchoCommand.name) == expected_write_length:
                expected_write_length = len(to_echo) + len("\n")

                if connection.write_line(to_echo) == expected_write_length:
                    write_failed = False

            if write_failed:
                print("Could not write the value '{}' to {} to be echoed".format(to_echo, connection.port.port))

            return connection.read()

        Command.__init__(self, EchoCommand.name, echo)


class CheckBaudRateCommand(Command):
    name = "b"

    def __init__(self, baud_rate):
        def check_baud_rate(connection):
            connection.write(CheckBaudRateCommand.name)

            actual_baud_rate = connection.read_int()

            if baud_rate != actual_baud_rate:
                raise Exception("Baud rate on Arduino is %d not %d" % (actual_baud_rate, baud_rate))

            return actual_baud_rate

        Command.__init__(self, CheckBaudRateCommand.name, check_baud_rate)

if __name__ == "__main__":
    ## TODO: Use proper handling of command line args
    if len(sys.argv) > 1:
        portName = sys.argv[1]
    else:
        portName = "/dev/ttyACM0"

    ## TODO: Get baud rate from command line
    #baud_rate = 9600

    try:
        arduino = Arduino(portName) #, baud_rate)
    except Exception as e:
        print("Could not connect to the Arduino:", e.message)

        sys.exit(1)

    # TODO: Do stuff
    result = arduino.execute_command(EchoCommand(), "HELLO!!!!")

    print("result = ", result)

    arduino.close()
