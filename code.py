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

row=0
column=1

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
ACTIVE_COLOR = (120, 0, 255)
INACTIVE_COLOR = (0, 0, 120)

# the color for the sweeping ticker bar
TICKER_COLOR = (0, 0, 255)
# Our keypad + neopixel driver
trellis = adafruit_trellism4.TrellisM4Express(rotation=90)
trellis.pixels.brightness = (0.31)


#Create a list of all step XY locations
step_list=[]
for y in range(4):
    for x in range(8):
        step_list.append((y, x))


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

    # handle button presses while we're waiting for the next tempo beat
    while time.monotonic() - stamp < 60/tempo:
        # Check for pressed buttons
        pressed = set(trellis.pressed_keys)
        #disabled temporarily for troubleshooting, this is needed to have background color display on startup
        #for step in step_list: 
        #    if step in pressed:
        #        trellis.pixels[step] = ACTIVE_COLOR
        #    else:
        #        trellis.pixels[step] = INACTIVE_COLOR
     
  
        pressed_list=list(pressed)
        if len(pressed_list)>1:
            print(pressed_list)
            line=[]
            path=[]
            first_press=0
            second_press=1

            #
            if pressed_list[first_press][column]==pressed_list[second_press][column]:
                pass
                print('pass')
            elif pressed_list[first_press][column]<pressed_list[second_press][column]:    
                print('problems in first column condition')
                for step in range(pressed_list[first_press][column], pressed_list[second_press][column]+1):
                    line.append((pressed_list[first_press][row], step))
                path=line
                
            else:
                print('problems in second column condition')
                for step in range(pressed_list[second_press][column], pressed_list[first_press][column]+1):
                    line.append((pressed_list[first_press][row], step))
                path=sorted(line, reverse=True)
                
                last_point=(pressed_list[first_press][row], step)
                print(last_point)
                
                
            print(path)
            line=[]

            if pressed_list[first_press][row] == pressed_list[second_press][row]:
                pass
            elif pressed_list[first_press][row] < pressed_list[1][row]:
                print('problems in first row condition')
                for step in range(pressed_list[first_press][row]+1, pressed_list[second_press][row]+1):
                    line.append((step, pressed_list[second_press][column]))
                path+=line
                
            else:
                print('problems in second row condition')
                for step in range(pressed_list[second_press][row], pressed_list[first_press][row]+1):    
                    line.append((step, pressed_list[first_press][column]))    
                path+=sorted(line, reverse=True)

            print(f"Points: {pressed_list}\nPath:\n{path}")

            print(f"\n\n\nPoints: {pressed_list}\nPath:\n{path}\n\n\n") 
            for step in step_list: 
                if step in path:
                    trellis.pixels[step] = ACTIVE_COLOR
                else:
                    trellis.pixels[step] = INACTIVE_COLOR
  
  
  
  
        time.sleep(0.1)  # a little delay here helps avoid debounce annoyances
