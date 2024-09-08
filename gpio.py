import smbus

# MCP23008 Register Addresses
IODIR           = 0x00   # GPIO direction register
#GPPU           = 0x06    # Pull-up resistor register
GPIOREG         = 0x09    # GPIO register
OLAT            = 0x0A    # Output latch register

class MCP23008:
    def __init__(self, bus, address):
        self.bus = bus
        self.address = address
        self.init_device()

    def init_device(self):
        try:
            # Initialize all GPIO pins as outputs and set to LOW
            self.bus.write_byte_data(self.address, IODIR, 0x00)  # All pins as outputs
            self.bus.write_byte_data(self.address, OLAT, 0x00)   # All pins LOW
        except:
            print("Warning! MCP23008 unavailable at I2C address " + str(self.address))

    def set_pin(self, pin, value):
        try:
            # Set the state of a specific pin (0 or 1)
            current_value = self.bus.read_byte_data(self.address, OLAT)
            if value:
                current_value |= (1 << pin)   # Set bit
            else:
                current_value &= ~(1 << pin)  # Clear bit
            self.bus.write_byte_data(self.address, OLAT, current_value)
        except:
            pass

    def get_pin(self, pin):
        # Get the state of a specific pin
        return (self.bus.read_byte_data(self.address, GPIOREG) >> pin) & 0x01

class GPIO:
    def __init__(self):
        bus = smbus.SMBus(1)  # Initialize I2C bus

        # I2C addresses of the MCP23008 devices
        i2c_addresses = [0x20, 0x21, 0x22]

        # Initialize MCP23008 devices and store them in a list
        self.mcp_devices = [MCP23008(bus, addr) for addr in i2c_addresses]

    # Find MCP23008 device by I2C address
    def set_pin_from_address(self, i2c_address, pin, value):
        for mcp in self.mcp_devices:
            if mcp.address == i2c_address:
                mcp.set_pin(pin,value)
        return None
