import argparse
import math
import numpy as np
import sounddevice as sd
import mido
from os import access, R_OK
from os.path import isfile
import random

random.seed()

### for testing how long stuff takes
import time
def mtime():
    return round(time.time() * 1000)
###

tick = round(time.time())

sampling_rate = 44100

frame_clock = 0 # global clock for how many frames have been sent to sounddevice output
midi_clock = 0  # global clock for how many frames have been processed

notes = dict()  # notes playing { midi_number : [ start_frame, end_frame, channels_playing, velocity] }
from enum import IntEnum
class n(IntEnum):
    START = 0
    END = 1
    CHANNELS = 2
    VELOCITY = 3

loops = dict() # loops data for notes { midi_number : [ loop array, loop clock, sweep bool ] }
class loop(IntEnum):
    DATA = 0
    INDEX = 1
    CHIRP = 2
    CHIRP_DONE = 3

playing = False # bool to indicate song has started

# variables used for slured pitch shifting effect
pitch_offset = 0 # current global midi_number offset

pitch_start = 0  # frame number to begin transition to new offset
pitch_stop = 0   # frame number to end transition to new offset
pitch_adjust = 0 # offset to new pitch_offset (will end at pitch_offset + pitch_adjust)

# create PCM of sine tone sweep
# derived from chirp.by
# Mike Markowski, mike.ab3ap@gmail.com
# Mar 4, 2015
# https://udel.edu/~mm/gr/chirp.py
def chirploop(fs_Hz, rep_Hz, f0_Hz, f1_Hz, phase_rad=0):
    T_s = 1 / rep_Hz
    c = (f1_Hz - f0_Hz) / T_s
    n = int(fs_Hz / rep_Hz)
    t_s = np.linspace(0, T_s, n)
    phi_Hz = (c * t_s**2) / 2 + (f0_Hz * t_s)
    phi_rad = 2 * np.pi * phi_Hz
    phi_rad += phase_rad
    return np.expand_dims(np.sin(phi_rad), axis=1)

# return a single cycle loop
# f = frequency
# fs = sample rate
def sineloop(f, fs):
    l = np.expand_dims((np.sin(2*np.pi*np.arange(fs/f)*f/fs)).astype(np.float32), axis=1)
    for i in (-2,1):
        l[i] = (l[i-1] + l[i] + l[i+1]) / 3
    return l

# return frequency from midi_number
def frequency(midi):
    return 440 * math.pow(2, (midi - 69) / 12)

parser = argparse.ArgumentParser()

# specify midi filename, or "default" for default midi source
parser.add_argument('--midi', type=str, required=False)
parser.add_argument('--ramp', type=float, required=False)
parser.add_argument('--drinks', default=0, type=int, required=False)
args = parser.parse_args()

# we specify ramp in number of samples instead of percent of note
# because notes are all of different length
# and we don't know how long they are until after its done playing
if args.ramp is None:
    ramp = 12
else:
    ramp = args.ramp

source = None
file_name = None
inport = None

if args.midi is not None:
    if isfile(args.midi) and access(args.midi, R_OK):
        source = "file"
        file_name = args.midi
        inport = mido.MidiFile(file_name).play()

if args.drinks is not None:
    drinks = args.drinks

# if there is no filename, open a midi port instead (connect a keyboard for example)
if source == None:
        source = "midistream"
        inport = mido.open_input()


chunksize = 28
# callback for sounddevice outputstream
#
# sounddevice calls this function, requesting we put 'frames' number of samples of
# the output stream into the array-like 'outdata'
def callback(outdata, frames, time, status):
    if status:
        print(status)
    global frame_clock
    global pitch_offset
    global pitch_start
    global pitch_stop
    global pitch_adjust

    #print(notes, (pitch_offset, pitch_start, pitch_stop, pitch_adjust))

    #space in which to mix different notes
    mixer = np.zeros(np.shape(outdata), dtype=np.float32)
    # mixed = mixer # per-frame
    mixed = 0 # per-chunk

    if playing:
        mixed = 0 # number of notes we have mixed

        for note in list(notes):
            if note in notes and note in loops:

                # if all notes have started chirping, update pitch
                if pitch_stop != 0 and frame_clock > pitch_stop:
                    # update pitch
                    pitch_offset += pitch_adjust
                    pitch_start = 0
                    pitch_stop = 0
                    pitch_adjust = 0
                printme = False
                for x in range(0, frames):
                    i = loops[note][loop.INDEX]
                    if frame_clock + 1 + x >= notes[note][n.START] and (notes[note][n.END] is None or frame_clock + 1 + x <= notes[note][n.END] + ramp):
                        outdata[x] = loops[note][loop.DATA][i]

                    # if the current sample is in the ramp-up window
                    if (frame_clock + 1 + x >= notes[note][n.START] and frame_clock + 1 + x <= notes[note][n.START] + ramp):
                        # multiply by frame in the ramp window (current frame - start frame) / ramp
                        outdata[x] *= (frame_clock + 1 + x - notes[note][n.START]) / ramp
                        #printme = True

                    # if the current sample is in the ramp-down window
                    if notes[note][n.END] is not None and frame_clock + 1 + x >= notes[note][n.END] and frame_clock + 1 + x <= notes[note][n.END] + ramp:
                        # multipily by frame in the ramp window
                        outdata[x] *= 1 - (frame_clock + 1 + x - notes[note][n.END]) / ramp
                        #printme = True

                    loops[note][loop.INDEX] += 1
                    # if we are at the end of the loop for this note
                    if loops[note][loop.INDEX] == len(loops[note][loop.DATA]):
                        # set index to start of loop
                        loops[note][loop.INDEX] = 0
                        # if we just finished a chirp
                        if loops[note][loop.CHIRP] == True:
                            # replace chirp loop with sine loop
                            loops[note][loop.DATA] = sineloop(frequency(note + pitch_offset + pitch_adjust), sampling_rate)
                            loops[note][loop.CHIRP_DONE] = True
                            loops[note][loop.CHIRP] = False
                        # or if we need to start a chirp do it
                        elif pitch_stop != 0 and frame_clock + x + 1 >= pitch_start and frame_clock + x + 1 < pitch_stop and loops[note][loop.CHIRP] == False:
                            loops[note][loop.DATA] = chirploop(sampling_rate,
                                                               1 / ((pitch_stop - pitch_start) / sampling_rate),
                                                               frequency(note + pitch_offset),
                                                               frequency(note + pitch_offset + pitch_adjust),
                                                               0)
                            loops[note][loop.CHIRP] = True
                            loops[note][loop.CHIRP_DONE] = False
                        # or if we are done with this chirp get ready for the next one
                        elif frame_clock > pitch_stop and loops[note][loop.CHIRP_DONE] == True:
                            loops[note][loop.CHIRP_DONE] = False

                if printme == True:
                    print(outdata)
                # print(len(outdata))

                # is the end of the note defined? have we reached the end of the note in this chunk (or before)?
                if notes[note][n.END] != None and frame_clock + frames >= notes[note][n.END]:
                    # then remove it from the notes[] dictionary, since we are done with it.
                    del notes[note]

                # mix the note into the mixer and increment the number we have mixed
                mixer += outdata
                # mixed += outdata.astype(dtype=bool) # per-sample
                mixed += 1 # per-chunk

        # reduce the amplitude of the notes back down to about the levels they should be
        # mixer = np.divide(mixer, mixed, out=np.zeros_like(mixer), where=mixed!=0) # per-sample
        if mixed != 0:
            mixer /= mixed # per-chunk

        # put the finished mix into outdata for the callback to take
        outdata[:] = mixer

        # update how many samples we have processed in the whole song
        frame_clock += frames


stream = sd.OutputStream(samplerate=sampling_rate, channels=1, dtype='float32', callback=callback, blocksize=chunksize)

with stream:
    for msg in inport:

        # note_off messages
        if msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            # update the midi clock, adding the number of samples since the prior note
            midi_clock += math.floor(msg.time * sampling_rate)
            if msg.note in notes:
                # decrement the number of channels wanting to play this note
                notes[msg.note][n.CHANNELS] -= 1
                # are all channels done playing it?
                if notes[msg.note][n.CHANNELS] == 0:
                    # if so, set the end of the note's frame number
                    notes[msg.note][n.END] = midi_clock
                    if source == "midistream":
                        notes[msg.note][n.END] = frame_clock + chunksize + 1
        # note_on messages
        elif msg.type == 'note_on':
            # signal callback to start processing notes
            playing = True
            # update the midi clock, adding the number of samples since the prior note
            midi_clock += math.floor(msg.time * sampling_rate)
            # is the note already set up to play (by a prior channel or note_on signal)?
            if msg.note in notes:
                # if so increment the number of note_on requests for the note
                notes[msg.note][n.CHANNELS] += 1
                # use the highest velocity so far of all requests
                notes[msg.note][n.VELOCITY] = max(notes[msg.note][3], msg.velocity)
            # otherwise initialize a new note
            else:
                notes[msg.note] = [midi_clock, None, 1, msg.velocity]
                loops[msg.note] = [sineloop(frequency(msg.note + pitch_offset), sampling_rate), 0, False, False]
                if source == "midistream":
                    notes[msg.note] = [frame_clock + chunksize + 1, None, 1, msg.velocity]


        # do this stuff once a second
        if round(time.time()) >= tick + 1:
            tick = round(time.time())
            # random pitch shift
            if pitch_adjust == 0 and random.randint(1, 100) <= drinks:
                pitch_adjust = random.randint(-3, 3)
                pitch_start = frame_clock + chunksize
                pitch_stop = int(frame_clock + random.randint(1, 3) * sampling_rate + chunksize)



exit(1)



