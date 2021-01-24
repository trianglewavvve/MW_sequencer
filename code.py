#https://learn.adafruit.com/classic-midi-synth-control-with-trellis-m4/code-with-circuitpython

import time
import random
import board
import busio
import audioio
import adafruit_fancyled.adafruit_fancyled as fancy
import adafruit_trellism4
#import adafruit_adxl34x
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode


##MIDI####################################MIDI#######################################MIDI##
import usb_midi
import adafruit_midi
import time

# TimingClock is worth importing first if present as it
# will make parsing more efficient for this high frequency event
# Only importing what is used will save a little bit of memory

# pylint: disable=unused-import
from adafruit_midi.timing_clock import TimingClock
from adafruit_midi.channel_pressure import ChannelPressure
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend
from adafruit_midi.polyphonic_key_pressure import PolyphonicKeyPressure
from adafruit_midi.program_change import ProgramChange
from adafruit_midi.start import Start
from adafruit_midi.stop import Stop
from adafruit_midi.system_exclusive import SystemExclusive

from adafruit_midi.midi_message import MIDIUnknownEvent

midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0],
    midi_out=usb_midi.ports[1],
    in_channel=(1, 2, 3),
    out_channel=5,
)

tonic_dict = dict(zip(['a', 'b', 'c', 'd', 'e', 'f', 'g'],[0, 2, 3, 5, 7, 8, 10, 12]))
scale_dict={'major':[0, 2, 4, 5, 7, 9, 11], 'major_5th':[0, 4, 7],'major_pent':[0, 2, 4,  7, 9],'minor':[0, 2, 3, 5, 7, 8, 10]}
selected_scale_type='major_pent'
selected_tonic='c'
octave_low=1
octave_high=8
#note_length=24 # quarter note=24
#note_time_interval=192*2
def notes_in_key(tonic=24, scale_type=scale_dict['major'], octave_low=3, octave_high=7, note_offset=21):
    note_list=[]
    for octave in range(octave_low, octave_high):
        root_note=octave*12+tonic+note_offset
        note_list+=[x+root_note for x in scale_type]
    return note_list
current_key=notes_in_key(tonic_dict[selected_tonic], scale_dict[selected_scale_type], octave_low, octave_high)
##MIDI####################################MIDI#######################################MIDI##





# This is the setup to have a "settings" file that could set parameters on startup, currently unused -DF
with open ("settings.txt", "r") as myfile:
    data=myfile.readlines()
#print(data[0])
#print(data[1])

# The keyboard object!
time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)
tempo = 240  # Starting BPM


# four colors for the 4 voices, using 0 or 255 only will reduce buzz
DRUM_COLOR = ((90, 0, 30),
              (90, 0, 30),
              (90, 0, 30),
              (90, 0, 30))

# the color for the sweeping ticker bar
TICKER_COLOR = (60, 0, 255)
INACTIVE_COLOR = (0, 0, 120)

# Our keypad + neopixel driver
trellis = adafruit_trellism4.TrellisM4Express(rotation=90)
trellis.pixels.brightness = (0.31)

# Clear all pixels
trellis.pixels.fill(0)

# Our global state
current_step = 7 # we actually start on the last step since we increment first
# the state of the sequencer
beatset = [[False] * 8, [False] * 8, [False] * 8, [False] * 8]
prior_beatset=beatset
# currently pressed buttons
current_press = set()
key_chars='0123456789abcdefghijklmnopqrstuvwxyz'
rows=['A', 'B', 'C', 'D']
current_step_row=[0, 0, 0, 0]
previous_step_row=[0, 0, 0, 0]
cycle_count=0
dividend_list=[[1, 1, 1, 1], [1, 1, 1, 2], [1, 1, 2, 4], [1, 2, 4, 8]]
idle_count=0
step_list=[]
active_cells=[]
max_active_notes_per_row=4
clear_after_idle_threshold=128
midi_mode=True
note_list=[]
for octave in range(3, 6):
  for note in ['C', 'E', 'F', 'G']:
    note_list.append(f'\\samples\\{note}{octave}.wav')

for y in range(4):
    for x in range(8):
        step_list.append((y, x))
for step in step_list:
    trellis.pixels[step] = INACTIVE_COLOR
SAMPLE_FOLDER = "/samples/"  # the name of the folder containing the samples
# You get 4 voices, they must all have the same sample rate and must
# all be mono or stereo (no mix-n-match!)
VOICES = note_list
# Parse the first file to figure out what format its in
with open(VOICES[0], "rb") as f:
    wav = audioio.WaveFile(f)
    print("%d channels, %d bits per sample, %d Hz sample rate " %
          (wav.channel_count, wav.bits_per_sample, wav.sample_rate))
    # Audio playback object - we'll go with either mono or stereo depending on
    # what we see in the first file
    if wav.channel_count == 1:
        audio = audioio.AudioOut(board.A1)
    elif wav.channel_count == 2:
        audio = audioio.AudioOut(board.A1, right_channel=board.A0)
    else:
        raise RuntimeError("Must be mono or stereo waves!")
    mixer = audioio.Mixer(voice_count=4,
                          sample_rate=wav.sample_rate,
                          channel_count=wav.channel_count,
                          bits_per_sample=wav.bits_per_sample,
                          samples_signed=True)
    audio.play(mixer)
samples = []
# Read the 4 wave files, convert to stereo samples, and store
# (show load status on neopixels and play audio once loaded too!)
for v in range(4):
    #trellis.pixels[(v, 0)] = DRUM_COLOR[v]
    wave_file = open(VOICES[v], "rb")
    # OK we managed to open the wave OK
    sample = audioio.WaveFile(wave_file)
    while mixer.playing:
        pass
    samples.append(sample)
# Clear all pixels

active_notes=[]

#'Everything above executes a single time on startup'
#Everything below repeats on a loop
while True:
    
    #clear all midi notes
    new_note=60
    midi.send(NoteOff(new_note, 0x00))
    
    if len(active_notes)>0:
        for note in active_notes:
            midi.send(NoteOff(note, 0x00))
        active_notes=[]
    
    
    idle_count+=1
    #print(idle_count)
    stamp = time.monotonic()
    # redraw the last step to remove the ticker bar (e.g. 'normal' view)

    if idle_count>clear_after_idle_threshold:
        for row in range(len(beatset)):

            for cell in range(0, len(beatset[row])):
                if beatset[row][cell]==True:
                    active_cells.append(cell)
            if len(active_cells)>0:
                try:
                    deactivated_cell=(row, active_cells[random.randint(0, len(active_cells)-1)])
                    beatset[deactivated_cell[0]][deactivated_cell[1]]=False
                    trellis.pixels[deactivated_cell]=INACTIVE_COLOR
                except:
                    print('FAILED')
                    print(len(active_cells))
                    print(random.randint(0, len(active_cells)-1))
                    #print(row, active_cells[random.randint(0, len(active_cells)-1)])
                #print(deactivated_cell)
            #print(f'row {y} exceeded note limit')


###########################################################################################
##### this is where I modified the code in order to accomplish clock division -David F.####
###########################################################################################

    for y in range(4):
        #dividend=2**(y)
        dividend = dividend_list[cycle_count][y]
        previous_step_row[y]=current_step_row[y]
        if current_step_row[y]<8:
            if (current_step)%dividend==0:
                current_step_row[y]+=1
                if current_step_row[y]==8:
                    current_step_row[y]=0
        #print(current_step_row)

        color = 0
        
        if beatset[y][current_step_row[y]]:
            color = DRUM_COLOR[y]
            trellis.pixels[(y, current_step_row[y])] = color
            #midi.send(NoteOn(new_note, 100))
        previous_step=current_step_row[y]-1
        if previous_step<0:
            previous_step=7
        if beatset[y][previous_step]:
            color = DRUM_COLOR[y]
            #midi.send(NoteOn(new_note, 100))
            print(y, current_step_row[y], y*8+current_step_row[y])
        else:
            color=INACTIVE_COLOR
            #midi.send(NoteOff(new_note, 0x00))
        trellis.pixels[(y, previous_step)] = color

    # next beat!
    current_step = (current_step + 1) % 8
    if sum(current_step_row)==0:
        if cycle_count==3:
            cycle_count=0
        else:
            if idle_count<119:
                cycle_count+=1
            else:
                cycle_count=0

    # draw the vertical ticker bar, with selected voices highlighted
    for y in range(4):
        if beatset[y][current_step_row[y]]:
            if previous_step_row[y]!=current_step_row[y]:
                color = (200, 0, 255)
                trellis.pixels[(y, current_step_row[y])] = color
                new_note=current_key[y*8+current_step_row[y]]
                active_notes.append(new_note)
                if midi_mode:
                    midi.send(NoteOn(new_note, 100))
                else:
                    mixer.play(samples[y], voice=y)
                    keyboard_layout.write(key_chars[(y*8+current_step_row[y])])
                    keyboard_layout.write('\n')
            else:
                if  midi_mode:
                    #midi.send(NoteOff(new_note, 100))
                    #doesn't work
                    pass


        else:
            color = TICKER_COLOR     # no voice on
            trellis.pixels[(y, current_step_row[y])] = color

##################################################################
##### Modified above to create clock division ####
##################################################################

    # handle button presses while we're waiting for the next tempo beat
    # also check the accelerometer if we're using it, to adjust tempo
    while time.monotonic() - stamp < 60/tempo:
        # Check for pressed buttons
        pressed = set(trellis.pressed_keys)
        #print(pressed)
        for down in pressed - current_press:
            idle_count=0
            y = down[0]
            x = down[1]
            beatset[y][x] = not beatset[y][x] # enable the voice
            active_cells=[]
            if beatset[y][x]:
                if sum(beatset[y])>max_active_notes_per_row:
                    for cell in range(0, len(beatset[y])):
                        if beatset[y][cell]==True:
                            active_cells.append(cell)
                    deactivated_cell=(y, active_cells[random.randint(0, len(active_cells)-1)])
                    beatset[deactivated_cell[0]][deactivated_cell[1]]=False
                    trellis.pixels[deactivated_cell]=INACTIVE_COLOR
                    #print(deactivated_cell)
                    #print(f'row {y} exceeded note limit')
                    #print(type(down))
                color = DRUM_COLOR[y]

            else:
                color = INACTIVE_COLOR
            trellis.pixels[down] = color
        current_press = pressed
        time.sleep(0.01)  # a little delay here helps avoid debounce annoyances

