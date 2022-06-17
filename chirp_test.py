import numpy as np

# Two versions of the chirp function are provided.  Depending on need
# it is more convenient sometimes to describe a chirp in terms of low
# and high frequencies, along with time length of chirp.  Other times
# it is convenient to describe chirp in terms of number of center frequency,
# bandwidth, repetition rate, and sample rate.
#
# The frequency based version generates the chirp waveform.  The center
# frequency described version simply has its parameters used to generate
# new parameters to call the first version.
#
# See http://en.wikipedia.org/wiki/Chirp for details on derivation.
#
# Mike Markowski, mike.ab3ap@gmail.com
# Mar 4, 2015


# chirp
#
# Generate a frequency sweep from low to high over time.
# Waveform description is based on number of samples.
#
# Inputs
#  fs_Hz: float, sample rate of chirp signal.
#  rep_Hz: float, repetitions per second of chirp.
#  f0_Hz: float, start (lower) frequency in Hz of chirp.
#  f1_Hz: float, stop (upper) frequency in Hz of chirp.
#  phase_rad: float, phase in radians at waveform start, default is 0.
#
# Output
#  Time domain chirp waveform of length numnSamples.

def chirp(fs_Hz, rep_Hz, f0_Hz, f1_Hz, phase_rad=0):

    T_s = 1 / rep_Hz # Period of chirp in seconds.
    c = (f1_Hz - f0_Hz) / T_s # Chirp rate in Hz/s.
    n = int(fs_Hz / rep_Hz) # Samples per repetition.
    t_s = np.linspace(0, T_s, n) # Chirp sample times.

    # Phase, phi_Hz, is integral of frequency, f(t) = ct + f0.
    phi_Hz = (c * t_s**2) / 2 + (f0_Hz * t_s) # Instantaneous phase.
    phi_rad = 2 * np.pi * phi_Hz # Convert to radians.
    phi_rad += phase_rad # Offset by user-specified initial phase.
    # return np.exp(1j * phi_rad) # Complex I/Q.
    return np.expand_dims(np.sin(phi_rad), axis=1) # Just real, or I, component.

# chirpCtr
#
# Convenience function to create a chirp based on center frequency and
# bandwidth.  It simply calculates start and stop freuqncies of chirp and
# calls the chirp creation function.
#
# Inputs
#  fs_Hz: sample rate in Hz of chirp waveform.
#  fc_Hz: float, center frequency in Hz of the chirp.
#  rep_Hz: integer, number of full chirps per second.
#  bw_Hz: float, bandwidth of chirp.
#  phase_rad: phase in radians at waveform start, default is 0.
#
# Output
#  Time domain chirp waveform.

def chirpCtr(fs_Hz, fc_Hz, rep_Hz, bw_Hz, phase_rad=0):
    f0_Hz = fc_Hz - bw_Hz / 2.
    f1_Hz = fc_Hz + bw_Hz / 2.
    return chirp(fs_Hz, rep_Hz, f0_Hz, f1_Hz, phase_rad)

def sine_(f, fs):
    return np.expand_dims((np.sin(2*np.pi*np.arange(fs/f)*f/fs)).astype(np.float32), axis=1)

import sounddevice as sd
import numpy as np


volume = 0.25     # range [0.0, 1.0]
fs = 48000       # sampling rate, Hz, must be integer
f = 440        # sine frequency, Hz, may be float
duration = 1.0 / f   # in seconds, may be float

stream = sd.OutputStream(samplerate=fs, channels=1, dtype='float32')
stream.start()

# generate samples, note conversion to float32 array

#samples = np.expand_dims((np.sin(2*np.pi*np.arange(fs*duration)*f/fs)).astype(np.float32), axis=1)
#while True:
#        stream.write(volume*samples)

# play. May repeat with different volume values (if done interactively)
import random
while True:

    freq = 440

    samples = sine_(freq, fs)
    for x in range(1, 500):
        stream.write(volume*samples)

    rand_freq = random.randint(220,880)

    samples = chirp(fs, 1, freq, rand_freq, 0).astype(np.float32)

    stream.write(volume*samples)

    samples = sine_(rand_freq, fs)
    for x in range(1, 500):
        stream.write(volume*samples)

    samples = chirp(fs, 1, rand_freq, freq, 0).astype(np.float32)

    stream.write(volume*samples)

