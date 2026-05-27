import time

class SolenoidController:
    """Generic named solenoid controller over a RelayBoard.

    Usage:
        board = RelayBoard()
        solenoids = SolenoidController(board, {'panel': 1, 'lock': 2})
        solenoids.trigger('panel')
        solenoids.pulse('lock', duration=0.3)
    """

    def __init__(self, board, mapping):
        self._board = board
        self._mapping = mapping  # {'name': channel_number}

    def trigger(self, name):
        self._board.set(self._mapping[name], True)

    def release(self, name):
        self._board.set(self._mapping[name], False)

    def pulse(self, name, duration=0.5):
        self.trigger(name)
        time.sleep(duration)
        self.release(name)

    def all_off(self):
        self._board.all_off()
