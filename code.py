#https://learn.adafruit.com/classic-midi-synth-control-with-trellis-m4/code-with-circuitpython
import time
import board
import busio
import audioio
import adafruit_fancyled.adafruit_fancyled as fancy
import adafruit_trellism4
import adafruit_adxl34x
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

midiuart = busio.UART(board.SDA, board.SCL, baudrate=31250)

#midi_mode = True
midi_mode = False

with open ("settings.txt", "r") as myfile:
    data=myfile.readlines()
#print(data[0])
#print('\n******\n')
#print(print(data[1]))
# The keyboard object!
time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)
tempo = 120
  # Starting BPM
# You can use the accelerometer to speed/slow down tempo by tilting!
ENABLE_TILT_TEMPO = False
MIN_TEMPO = 10
MAX_TEMPO = 400
SAMPLE_FOLDER = "/samples/"  # the name of the folder containing the samples
# You get 4 voices, they must all have the same sample rate and must
# all be mono or stereo (no mix-n-match!)
VOICES = [SAMPLE_FOLDER+"rats_clip1.wav",
          SAMPLE_FOLDER+"rats_clip2.wav",
          SAMPLE_FOLDER+"rats_clip3.wav",
          SAMPLE_FOLDER+"rats_clip4.wav"]
# four colors for the 4 voices, using 0 or 255 only will reduce buzz
DRUM_COLOR = ((120, 0, 255),
              (120, 0, 255),
              (120, 0, 255),
              (120, 0, 255))

# the color for the sweeping ticker bar
TICKER_COLOR = (0, 0, 255)
# Our keypad + neopixel driver
trellis = adafruit_trellism4.TrellisM4Express(rotation=90)
trellis.pixels.brightness = (0.31)
# Our accelerometer
i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)

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
    #for x in range(1, 4):
#        trellis.pixels[(v, x)] = DRUM_COLOR[v]
    sample = audioio.WaveFile(wave_file)
    # debug play back on load!
    #mixer.play(sample, voice=0)
#    for x in range(4, 7):
#        trellis.pixels[(v, x)] = DRUM_COLOR[v]
    while mixer.playing:
        pass
#    trellis.pixels[(v, 7)] = DRUM_COLOR[v]
    samples.append(sample)
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
###########################################################################################
################ Everything above executes a single time on startup'#######################
###############################Everything below repeats on a loop##########################
###########################################################################################
while True:
    #print(idle_count)
    idle_count+=1
    stamp = time.monotonic()
    # redraw the last step to remove the ticker bar (e.g. 'normal' view)
    #print(data[0])
###########################################################################################
##### this is where I modified the code in order to accomplish clock division -David F.####
###########################################################################################
    for y in range(4):
        #dividend=2**(y)
        dividend = dividend_list[cycle_count][y]
        #temporarily remove clock division
        dividend=1
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
            color=0
        trellis.pixels[(y, previous_step)] = color
    # next beat!
    # substitute subtraction in order to reverse direction
    current_step = (current_step + 1) % 8
    if sum(current_step_row)==0:
        if cycle_count==3:
            cycle_count=0
        else:
            if idle_count<119:
                cycle_count+=1
    # draw the vertical ticker bar, with selected voices highlighted
    for y in range(4):
        if beatset[y][current_step_row[y]]:
            if previous_step_row[y]!=current_step_row[y]:
                #r, g, b = DRUM_COLOR[y]
                color = (200, 0, 255)
                #print("Playing: ", VOICES[y])
                trellis.pixels[(y, current_step_row[y])] = color
                mixer.play(samples[y], voice=y)
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
##### modified above to create clock division ####
##################################################################
    # handle button presses while we're waiting for the next tempo beat
    # also check the accelerometer if we're using it, to adjust tempo
    while time.monotonic() - stamp < 60/tempo:
        # Check for pressed buttons
        pressed = set(trellis.pressed_keys)
        #print(pressed)
        for down in pressed - current_press:
            print("Pressed down", down)
            idle_count=0
            print(time.monotonic())
            y = down[0]
            x = down[1]
            beatset[y][x] = not beatset[y][x] # enable the voice
            if beatset[y][x]:
                color = DRUM_COLOR[y]
            else:
                color = 0
            trellis.pixels[down] = color
        current_press = pressed

        time.sleep(0.01)  # a little delay here helps avoid debounce annoyances
