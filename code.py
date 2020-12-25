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

midiuart = busio.UART(board.SDA, board.SCL, baudrate=31250)
midi_mode = False

# This is the setup to have a "settings" file that could set parameters on startup, currently unused -DF
with open ("settings.txt", "r") as myfile:
    data=myfile.readlines()
#print(data[0])
#print(data[1])

# The keyboard object!
time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)
tempo = 190  # Starting BPM

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
max_active_notes_per_row=4
clear_after_idle_threshold=32
active_cells=[]
for y in range(4):
    for x in range(8):
        step_list.append((y, x))
for step in step_list:
    trellis.pixels[step] = INACTIVE_COLOR
#'Everything above executes a single time on startup'
#Everything below repeats on a loop

while True:
    idle_count+=1
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
        previous_step=current_step_row[y]-1
        if previous_step<0:
            previous_step=7
        if beatset[y][previous_step]:
            color = DRUM_COLOR[y]
        else:
            color=INACTIVE_COLOR
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
                if midi_mode:
                    noteval=100+y*12
                    midiuart.write(bytes([0x90, noteval, 100]))
                else:
                    keyboard_layout.write(key_chars[(y*8+current_step_row[y])])
                    keyboard_layout.write('\n')
            else:
                if  midi_mode:
                    noteval=100+y*12
                    midiuart.write(bytes([0x90, noteval, 0]))


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
        time.sleep(0.01)  # a little delay here helps avoid debounce annoyances3

        
