
# Synthehol - Audio Synthesizer and Pitch Shifter

## What we built

Initially, we started out with implementing sine, square and sawtooth waves to generate waves and perform some forms of 
synthesis on it. We have implemented additive synthesis. We wanted to generate some musical sounds and add some 
"drunk-like" effects on it.

Then moved on, we wanted to create a midi synthesizer that would play a midi file or midi stream. 
We wanted to have the synthesizer perform the piece with distortions and "drunk-like" effects and dynamic
pitch shifting with a slurred transition between them.

Honestly, we ended up biting off more than we could chew.

We built the synthesizer and got notes playing, and we got the pitch transitions working, but the other effects
we dreamed of, we didn't get to.  What we did do ended up taking all our efforts.

## How it works

Synthehol is built on python using mido and sounddevice to read midi files, generate messages, and output sound.

Between these two ends, we built a midi message parser, which stores notes in a "Dictionary" map, and a callback
routine that is called by sounddevice to request chunks of sound data.

The callback for sounddevice reads note data from the note dictionary, and for each note, generates small chunks of note samples.
Then it applies attack and decay envelopes, and mixes all the notes together and feeds it to sounddevice for output.

Additionally, there is a chance every second of playback (which can be configured through the command line) that
a transition between pitches will be triggered, with random pitch shift and durration for the transition,
which is applied to the entire song in real time as it plays.

Instead of dynamically generating waveforms, as was done in class, waveforms are created as single cycle "loops".
This allows us to the math for a waveform once, and reuse it for the durration of the note.

Also, we create a "chirp" transition loop for each note when we move from one pitch to another.

## What didn't work / What lessons did we learn

This project was pretty difficult, as it was Gary's first python program and Rajashree's first midi project, and we were 
tackling several concepts and implementations not specifically covered in class.

First we got mido working to read a file and generate messages.  This went ok.

Getting the callback function to work was a bit of learning, but we eventually got that going.

We decided to combine notes from multiple channels into single channel output.

We then implemented wave generators and got songs playing.

Then we hit our first roadblock.  Figuring out how to change frequency on the fly durring a note.

Adjusting the frequency directly in the generator often produced noise due to disconuity in the signal.

Using a naive concept, we figured out the last sample in the old frequency, and the direction the signal was going, up or down.
From this we stepped back in the new signal until we found a place where the signal was going in the same direction and looked
to be continuous with the old signal.  We then used an offset to produce the signal from that point in the frame_clock.

But, not matter how we convolved the ends, it still produced "buzzy" noise durring the transition.

So, back to the drawing board. Doing some research, we found mathematical functions for "sweep/chirp" cosine signal generation,
which worked great, but required we refactor our dynamic signal generation to using loops.

This worked suprisingly well.

But, there was (and is) still noise in the output.  There are clicks when notes start and stop, especially when multiple notes
are playing at once.

We tried convolving the ends of the loops, to no avail, and verified the ramps were working.

Suspecting that there may be issues with additive mixing where zeros are being mixed in, we went from a per-chunk mixing
to a per-sample mixing, taking out the addition of zero value samples.

This didn't do anything to the noise, but it did decrease our under-run threshold, since it increased processing.

We also didn't get any distortions implemented.

Additionally, as more notes simultaneously play, we reach a threshold where output under-runs occur, causing studdering.
I guess we could cause this an undocumented "drunk-effect" feature.

If we were to continue development, we could raise this threshold by generating a static ramp object, then using array slicing
when copying signal and applying the object. Currently both are implemented iteratively, which seems really slow in python.
 
So, in the end, we learned about python, midi messages, callbacks, mixing, looped signal generation, chunked envelope windowing,
frequency transitioning, and signal continuity issues.


## Pre-requisites:
1. python 3.8
2. numpy
3. sounddevice
4. mido

and other imports...

## How to run:
1. python main.py --midi [filename] --drinks [0-100]

   filename is the name of the midi file for input
   drinks is the percentage chance, per second, that a pitch transition will be triggered

   If no filename is specified, it will attempt to open a midi port for connection to a midi device.
   Though, we have no midi devices to test this functionality with, so it may or may not work.

2. python chirp_test.py

   test of loop signal generation for sine and chirp loops

   this sounds mostly noiseless, with a slight hum in sine generation, and an occasional very quiet 'tick'
   at the point of sine/chirp concatenation.

3. python synthesizer.py --speed [>1] --volume [>1]

   speed is the speed at which the notes will be played
   volume is the volume at which the notes will be played