import argparse
import math
import numpy as np
import sounddevice as sd


# calculate the amplitude of the note
def amplitude_calculator(volume):
    return math.pow(10, (-6 * (10 - volume)) / 20)


# get the note frequency of each midi key
def frequency_calculator(root):
    return 440 * math.pow(2, (root - 69) / 12)


# generate square wave samples
def square_wave(amplitude, frequency, sample_length):
    square_wave_samples = np.array([amplitude * (4 * math.floor(frequency * (x / sample_length)) - 2 *
                                                 math.floor(2 * frequency * (x / sample_length)) + 1) for x in
                                    range(0, sample_length)])
    return square_wave_samples


# generate sine wave samples
def sine_wave(amplitude, frequency, sample_length):
    sine_wave_samples = np.array([amplitude * np.sin(2.0 * np.pi * frequency * (x / sample_length)) for x in
                                   range(0, sample_length)])
    return sine_wave_samples


# generate sawtooth wave samples
def sawtooth_wave(amplitude, frequency, sample_length):
    sawtooth_wave_samples = np.array(
        [amplitude * (frequency * (x / sample_length) - math.floor(frequency * x / sample_length)) for x in
         range(0, sample_length)])
    return sawtooth_wave_samples


# implemented additive synthesis
def add_waves(sine_samples, sawtooth_samples, square_samples):
    return sine_samples + sawtooth_samples + square_samples


# get notes in scale
def get_major_scale_notes(root_midi_keynumber):
    scales = np.zeros(8)
    scales[0] = root_midi_keynumber
    scales[1] = root_midi_keynumber + 2
    scales[2] = root_midi_keynumber + 4
    scales[3] = root_midi_keynumber + 5
    scales[4] = root_midi_keynumber + 7
    scales[5] = root_midi_keynumber + 9
    scales[6] = root_midi_keynumber + 11
    scales[7] = root_midi_keynumber + 12
    return scales

# set sampling rate and root key
sampling_rate = 48000
root = 48

# get the values from command line
parser = argparse.ArgumentParser()

# get the volume and speed to generate samples
parser.add_argument('--speed', default=1, type=int, required=False)
parser.add_argument('--volume', default=5.0, type=int, required=False)
args = parser.parse_args()

volume = args.volume
speed = args.speed

stream = sd.OutputStream(samplerate=sampling_rate, channels=1, dtype='float32')
stream.start()

# set the sample length to play at given speed
sample_length = int(sampling_rate / speed)

# generate the envelope
envelope = np.ones(sample_length)

for j in range(int(sample_length * 0.1)):
    envelope[j] = (j / (sample_length * 0.1))

for j in range(sample_length - 1, sample_length - 1 - int(sample_length * 0.1), -1):
    envelope[j] = ((sample_length - 1 - j) / (sample_length * 0.1))

while True:
    # get midi keys for every next note
    midi_keys_numbers = get_major_scale_notes(root)

    # play the notes for scale values
    for i in range(8):
        amplitude = amplitude_calculator(volume)
        frequency = frequency_calculator(midi_keys_numbers[i])

        # generate samples for each wave and each note
        square_samples = square_wave(amplitude, frequency, sample_length)
        sine_samples = sine_wave(amplitude, frequency, sample_length)
        sawtooth_samples = sawtooth_wave(amplitude, frequency, sample_length)

        # add samples to generate additive synthesis
        samples = add_waves(sine_samples, sawtooth_samples, square_samples)

        # apply envelope
        all_samples = np.multiply(samples, envelope).astype(np.float32)

        # write samples to output stream
        stream.write(all_samples)

        # after every 8 scales played get the next note and play notes for next scale
        if i == 7:
            if root < 108:
                root = root + 12
            else:
                root = 48


