#!/usr/bin/env python3
import argparse
from aubio import source, pitch
import os
import subprocess
import sys

DEFAULT_FIRST = 422.1
DEFAULT_SECOND = 321.7
TOLERANCE = 1.5
MIN_TONE_LENGTH = 0.5


def popTone(pitches, tone, tolerance):
    '''
    trim from the front of the list until the tone is removed
    @return: duration of the tone
    '''
    start_time = pitches[0][0]
    while len(pitches) > 0:
        t,p = pitches.pop(0)
        if abs(p-tone) > tolerance:
            break

    return t - start_time


def findTwoTone(mp3_file, first_freq=DEFAULT_FIRST, second_freq=DEFAULT_SECOND, start_time=0, length=-1):
    '''
    find the start time of the two tone call sequence.
    @return: offset in seconds from start_time
    '''
    downsample = 1
    samplerate = 44100 // downsample
    window_size = 4096 // downsample # fft size
    hop_size = 512  // downsample # hop size

    audio = source(mp3_file, samplerate, hop_size)
    samplerate = audio.samplerate

    pitch_o = pitch("schmitt", window_size, hop_size, samplerate)
    pitch_o.set_unit("Hz")

    pitches = []

    # read and process all frames for pitch
    total_frames = 0
    while True:
        samples, read = audio()
        tone_time = total_frames / float(samplerate)
        total_frames += read
        if read < hop_size:
            break

        # skip ahead to the start time
        if tone_time < start_time:
            continue

        # bail early
        if length > 0 and (start_time + length) > tone_time:
            return None

        # Get the pitch
        p = pitch_o(samples)[0]
        pitches.append((tone_time, p))
        # print("%f %f" % (pitch_time, p))

    # Analyse the pitches to detect the two tones
    while len(pitches) > 0:
        t,p = pitches.pop(0)
        if abs(p-first_freq) < TOLERANCE:
            tone_one_length = popTone(pitches, first_freq, TOLERANCE)
            if tone_one_length >= MIN_TONE_LENGTH:
                tone_one_start = t

                # Discard a few samples between the tones
                pitches.pop(0)
                pitches.pop(0)
                pitches.pop(0)

                t,p = pitches.pop(0)
                if abs(p-second_freq) < TOLERANCE:
                    tone_two_length = popTone(pitches, second_freq, TOLERANCE)
                    if tone_two_length >= MIN_TONE_LENGTH:
                        return tone_one_start - start_time         

    return None


def main():
    parser = argparse.ArgumentParser(description='search a mp3 file for tones')
    parser.add_argument('audio_file', type=str, help='mp3 file')
    parser.add_argument('--start', metavar="N", type=int, default=0,
                        help='start the search N seconds into the file')
    parser.add_argument('--length', metavar="X", type=int, default=-1,
                        help='number of seconds of audio to search')
    parser.add_argument('--first', type=float, default=DEFAULT_FIRST,
                        help='first tone frequency')
    parser.add_argument('--second', type=float, default=DEFAULT_SECOND,
                        help='second tone frequency')
    args = parser.parse_args()

    print("Searching...")
    tone_offset = findTwoTone(args.audio_file, args.first, args.second, args.start, args.length)
    print("Done")
    if tone_offset is None:
        print("Tones not found")
    else:
        print("Tone Time offset: %f" % tone_offset)


if __name__ == "__main__":
    main()