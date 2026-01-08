from qm.qua import align, play, wait


RX_SWITCH_DELAY = 230  # clock cycles
AMPLIFIER_UNBLANKING_TIME = 500  # clock cycles
AMPLIFIER_BLANKING_TIME = 500  # clock cycles


def drive_mode(switch, amplifier):
    """
    Configures the hardware such that the receiver switch does not
    allow signal to pass through, and the amplifier is turned on and
    unblanked, ready for driving the system. This adds 4 align() calls
    and 730 clock cycles of wait time.
    """
    align()
    play("voltage_off", switch)  # Open the switch
    align()
    wait(RX_SWITCH_DELAY)  # Switching time
    play("voltage_on", amplifier)  # Turn on the amplifier
    align()
    wait(AMPLIFIER_UNBLANKING_TIME)  # Max characteristic unblanking time
    align()


def readout_mode(switch, amplifier):
    """
    Configures the hardware such that the receiver switch allows signal
    to pass through, and the amplifier off (blanked) for reading out the
    resonator. This adds 4 align() calls and 730 clock cycles of wait time.
    """
    align()
    play("voltage_off", amplifier)  # Ensure Amplifier is off
    align()
    wait(RX_SWITCH_DELAY)
    play("voltage_on", switch)  # Close the switch
    align()
    wait(AMPLIFIER_BLANKING_TIME)
    align()


def safe_mode(switch, amplifier):
    """
    Turns off the amplifier and opens the switch to ensure that no signal
    can pass through. This adds 3 align() calls and 500 clock cycles
    of wait time.
    """
    align()
    play("voltage_off", switch)  # Ensure Switch is open
    play("voltage_off", amplifier)  # Turn off the amplifier
    align()
    wait(RX_SWITCH_DELAY)
    align()
