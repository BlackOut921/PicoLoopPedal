# Version 2.4-test
#
# Add adafruit_midi to lib folder
#
# _midiNotes[0] = CLEAR(E1)
# _midiNotes[1] = REC/PLAY(F1)
# _midiNotes[2] = STOP(G1)
# _midiNotes[3] = TRACK 1(0)/UNDO(+1)/MUTE(+12)/PLAY(+24)/OVERDUB(+25)
# _midiNotes[4] = TRACK 2(0)/UNDO(+1)/MUTE(+12)/PLAY(+24)/OVERDUB(+25)
# _midiNotes[5] = TRACK 3(0)/UNDO(+1)/MUTE(+12)/PLAY(+24)/OVERDUB(+25)
# _midiNotes[6] = TRACK 4(0)/UNDO(+1)/MUTE(+12)/PLAY(+24)/OVERDUB(+25)

import time
import board
import digitalio
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

# Set Pico to be MIDI out
midi = adafruit_midi.MIDI(
    midi_out=usb_midi.ports[1], out_channel=0,
    midi_in=usb_midi.ports[0], in_channel=0)

# Turn built in LED (GP25) on
led = digitalio.DigitalInOut(board.GP25)
led.direction = digitalio.Direction.OUTPUT
led.value = True

# Setup INPUTs
_btnPins = [board.GP0,
            board.GP1, board.GP2, board.GP3, board.GP4,
            board.GP5, board.GP6, board.GP7, board.GP8]
_btn = []
for i in _btnPins:
    b = digitalio.DigitalInOut(i)
    b.direction = digitalio.Direction.INPUT
    b.pull = digitalio.Pull.UP
    _btn.append(b)

# Setup green LEDs
_ledGreenPins = [board.GP10, board.GP12, board.GP19, board.GP21]
_ledGreen = []
for i in _ledGreenPins:
    led = digitalio.DigitalInOut(i)
    led.direction = digitalio.Direction.OUTPUT
    led.value = False
    _ledGreen.append(led)

# Setup red LEDs
_ledRedPins = [board.GP9, board.GP11, board.GP18, board.GP20]
_ledRed = []
for i in _ledRedPins:
    led = digitalio.DigitalInOut(i)
    led.direction = digitalio.Direction.OUTPUT
    led.value = False
    _ledRed.append(led)

# Setup State LEDs
_ledStatePins = [board.GP22, board.GP26, board.GP27, board.GP28]
_ledState = []
for i in _ledStatePins:
    led = digitalio.DigitalInOut(i)
    led.direction = digitalio.Direction.OUTPUT
    led.value = False
    _ledState.append(led)

# Globals
_mode = 0  # 0=Rec, 1=Play
_state = 0  # 0=None, 1=Record, 2=Overdub, 3=Play, 4=Stop
_selectedTrack = 0
_midiNotes = [40, 41, 43, 53, 55, 57, 59]
_trackMute = [False, False, False, False]  # False=Playing, True=Muted
_btnPressed = [False, False, False, False, False, False, False, False, False]
_lastNote = 0  # Last MIDI note sent
# For REC/PLAY and MODE pedals
_recPedalTimer = 0
_modePedalTimer = 0
_pedalTimerMax = 0.5
# Test
_loopStart = 0
_loopLength = 0
_loopInitial = True
# ---
_pedalPressStart = 0
_pedalPressTimer = 0
_pedalPressTimerMax = 2

def SendNoteOff(i):
    midi.send(NoteOff(i, 127))

def UpdateStateLED():
    for i in _ledState:  # Turn off all _ledState[]
        i.value = False
    if _state == 1:  # Record
        _ledState[0].value = True
    elif _state == 2:  # Overdub
        _ledState[1].value = True
    elif _state == 3:  # Play
        _ledState[2].value = True
    elif _state == 4:  # Stop
        _ledState[3].value = True

# i = (0=None, 1=Record, 2=Overdub, 3=Play, 4=Stop)
def SetState(i):
    global _state
    _state = i
    UpdateStateLED()
    if _state == 0:
        print("RESET")
    elif _state == 1:
        print("REC")
    elif _state == 2:
        print("OVERDUB")
    elif _state == 3:
        print("PLAY")

def NextState():
    SendNote(_midiNotes[1])
    if _state == 0:  # None
        SetState(1)  # Switch to record
        global _loopStart
        _loopStart = time.monotonic()
    elif _state == 1:  # Record
        SetState(2)  # Switch to overdub
        global _loopInitial
        global _loopLength
        if _loopInitial is True:
            _loopInitial = False
            _loopLength = time.monotonic() - _loopStart
            print("_loopLength = ", _loopLength)
    elif _state == 2:  # Overdub
        SetState(3)  # Switch to play
    elif _state == 3:  # Play
        SetState(2)  # Switch to overdub
    elif _state == 4:  # Stop
        SetState(3)  # Switch to play

def UpdateGreenLEDs():
    for g in _ledGreen:
        g.value = False
    if _mode == 1:
        _ledGreen[0].value = not _trackMute[0]
        _ledGreen[1].value = not _trackMute[1]
        _ledGreen[2].value = not _trackMute[2]
        _ledGreen[3].value = not _trackMute[3]

def UpdateRedLEDs():
    for r in _ledRed:
        r.value = False
    if _mode == 0:
        _ledRed[_selectedTrack - 1].value = True

# i = (1 to 4)
def SelectTrack(i, sendNote=True):
    global _selectedTrack
    _selectedTrack = i
    UpdateRedLEDs()
    if sendNote:
        SendNote(_midiNotes[i + 2], True)  # Select TRACK i
    print("Select TRACK", i)

# i = (-1=Auto, 0=Rec, 1=Play)
def ChangeMode(i=-1, sendNote=True):
    global _mode
    if i != -1:
        _mode = i
    else:
        if _mode == 0:
            _mode = 1
        elif _mode == 1:
            _mode = 0
    UpdateRedLEDs()
    UpdateGreenLEDs()
    if sendNote:
        SendNote(_midiNotes[0] - 2)
    print("REC MODE" if _mode == 0 else "PLAY MODE")

def SendNote(i, _sendNoteOff=False):
    midi.send(NoteOn(i, 127))
    global _lastNote
    _lastNote = i
    if _sendNoteOff:
        SendNoteOff(_lastNote)

def Stop():
    if _state == 0:
        return
    SetState(4)
    SendNote(_midiNotes[2], True)  # Stop all LOOPERS
    print("STOP ALL")

def Clear():
    global _modePedalTimer
    global _recPedalTimer
    global _loopStart
    global _loopLength
    global _loopInitial
    _modePedalTimer = 0
    _recPedalTimer = 0
    _loopStart = 0
    _loopLength = 0
    _loopInitial = True
    Stop()
    SendNote(_midiNotes[0], True)  # Clear
    print("CLEAR")
    for r in _ledRed:  # Turn OFF _redLEDs
        r.value = False
    for g in _ledGreen:  # Turn OFF _greenLEDs
        g.value = False
    for i in _ledState:  # Turn ON _stateLEDs
        i.value = True
    SelectTrack(1)
    ChangeMode(0, False)
    global _trackMute
    if _trackMute[0]:
        SendNote(_midiNotes[3] + 12, True)  # Unmute TRACK 1
        _trackMute[0] = False
    if _trackMute[1]:
        SendNote(_midiNotes[4] + 12, True)  # Unmute TRACK 2
        _trackMute[1] = False
    if _trackMute[2]:
        SendNote(_midiNotes[5] + 12, True)  # Unmute TRACK 3
        _trackMute[2] = False
    if _trackMute[3]:
        SendNote(_midiNotes[6] + 12, True)  # Unmute TRACK 4
        _trackMute[3] = False
    time.sleep(1)
    SetState(0)

def ReleaseButton(i):
    # If _btnPressed[i]=TRUE and _btn[i] is NOT pressed
    if _btnPressed[i] and _btn[i].value:
        _btnPressed[i] = False
        SendNoteOff(_lastNote)

# Toggles mute on TRACK[i]
# i = (1 to 4)
def ToggleMute(i, sendNote=False):
    if sendNote:
        SendNote(_midiNotes[i + 2] + 12)  # Toggle mute TRACK i
    _trackMute[i - 1] = not _trackMute[i - 1]  # Toggle bool[0]
    if _mode == 1:  # if in PLAYEMODE
        _ledGreen[i - 1].value = not _trackMute[i - 1]  # Toggle green LED
    print("TRACK", i, "muted = ", _trackMute[i - 1])

# i = (1 to 4)
def UndoTrack(i=1):
    if _state == 0:
        return
    SendNote(_midiNotes[i + 2] + 24, True)  # Put LOOPER i in playmode
    time.sleep(0.1)
    SendNote(_midiNotes[i + 2] + 1, True)  # Undo LOOPER i
    _ledRed[i - 1].value = False
    time.sleep(0.5)
    _ledRed[i - 1].value = True
    if _state == 2:  # _state == OVERDUB
        SendNote(_midiNotes[i + 2] + 25, True)  # Set LOOPER i back to OVERDUB
    print("UNDO TRACK ", i)
    SelectTrack(i)

# Init
print("Pedal BOOTED")
for i in _ledState:
    i.value = True
    time.sleep(1.25)
Clear()
print("Pedal READY")

while True:
    # ----- ----- Clear ----- -----
    if not _btn[0].value:
        if _btnPressed[0] is False:
            _btnPressed[0] = True
            Clear()
    else:
        ReleaseButton(0)

    # ----- ----- REC/PLAY ----- -----
    if not _btn[1].value:
        if _btnPressed[1] is False:
            _btnPressed[1] = True
            if _recPedalTimer == 0:
                _recPedalTimer = time.monotonic()
                NextState()
            else:
                if (time.monotonic() - _recPedalTimer) >= _pedalTimerMax:
                    NextState()
                    _recPedalTimer = 0
    else:
        ReleaseButton(1)

    # ----- ----- Stop ----- -----
    if not _btn[2].value:
        if _btnPressed[2] is False:
            _btnPressed[2] = True
            Stop()
    else:
        ReleaseButton(2)

    # ----- ----- Undo - NOT USED!!! ----- -----
    # if not _btn[3].value:
    # if _btnPressed[3] is False:
    # _btnPressed[3] = True
    # else:
    # ReleaseButton(3)

    # ----- ----- Mode ----- -----
    if not _btn[4].value:
        if _btnPressed[4] is False:
            _btnPressed[4] = True
            if _modePedalTimer == 0:
                _modePedalTimer = time.monotonic()
                ChangeMode()
            else:
                if (time.monotonic() - _modePedalTimer) >= (_pedalTimerMax / 2):
                    ChangeMode()
                    _modePedalTimer = 0
    else:
        ReleaseButton(4)

    # ----- ----- Track 1 ----- -----
    if not _btn[5].value:
        if _btnPressed[5] is False:
            _btnPressed[5] = True
            _pedalPressStart = time.monotonic()
            if _mode == 0:
                SelectTrack(1)
            elif _mode == 1:
                ToggleMute(1, True)
        else:
            _pedalPressTimer = time.monotonic() - _pedalPressStart
            if _pedalPressTimer >= _pedalPressTimerMax:
                _btnPressed[5] = False
                if _mode == 0:
                    UndoTrack(1)
    else:
        ReleaseButton(5)

    # ----- ----- Track 2 ----- -----
    if not _btn[6].value:
        if _btnPressed[6] is False:
            _btnPressed[6] = True
            _pedalPressStart = time.monotonic()
            if _mode == 0:
                SelectTrack(2)
            elif _mode == 1:
                ToggleMute(2, True)
        else:
            _pedalPressTimer = time.monotonic() - _pedalPressStart
            if _pedalPressTimer >= _pedalPressTimerMax:
                _btnPressed[6] = False
                if _mode == 0:
                    UndoTrack(2)
    else:
        ReleaseButton(6)

    # ----- ----- Track 3 ----- -----
    if not _btn[7].value:
        if _btnPressed[7] is False:
            _btnPressed[7] = True
            _pedalPressStart = time.monotonic()
            if _mode == 0:
                SelectTrack(3)
            elif _mode == 1:
                ToggleMute(3, True)
        else:
            _pedalPressTimer = time.monotonic() - _pedalPressStart
            if _pedalPressTimer >= _pedalPressTimerMax:
                _btnPressed[7] = False
                if _mode == 0:
                    UndoTrack(3)
    else:
        ReleaseButton(7)

    # ----- ----- Track 4 ----- -----
    if not _btn[8].value:
        if _btnPressed[8] is False:
            _btnPressed[8] = True
            _pedalPressStart = time.monotonic()
            if _mode == 0:
                SelectTrack(4)
            elif _mode == 1:
                ToggleMute(4, True)
        else:
            _pedalPressTimer = time.monotonic() - _pedalPressStart
            if _pedalPressTimer >= _pedalPressTimerMax:
                _btnPressed[8] = False
                if _mode == 0:
                    UndoTrack(4)
    else:
        ReleaseButton(8)

    msg = midi.receive()
    if msg is not None:
        if isinstance(msg, NoteOn):
            if msg.note == _midiNotes[0]:  # CLEAR
                Clear()
            if msg.note == _midiNotes[1]:  # REC/OVERDUB/PLAY
                NextState()
            if msg.note == _midiNotes[2]:  # STOP
                Stop()
            if msg.note == _midiNotes[0] - 2:  # Change MODE
                ChangeMode()
            if msg.note == _midiNotes[3]:  # Select TRACK 1
                SelectTrack(1)
            if msg.note == _midiNotes[4]:  # Select TRACK 2
                SelectTrack(2)
            if msg.note == _midiNotes[5]:  # Select TRACK 3
                SelectTrack(3)
            if msg.note == _midiNotes[6]:  # Select TRACK 4
                SelectTrack(4)
            if msg.note == _midiNotes[3] + 12:  # Toggle mute TRACK 1
                ToggleMute(1)
            if msg.note == _midiNotes[4] + 12:  # Toggle mute TRACK 2
                ToggleMute(2)
            if msg.note == _midiNotes[5] + 12:  # Toggle mute TRACK 3
                ToggleMute(3)
            if msg.note == _midiNotes[6] + 12:  # Toggle mute TRACK 4
                ToggleMute(4)
