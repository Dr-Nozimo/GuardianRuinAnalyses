#!/bin/bash

# A very simple script to convert an audio recording to FLAC
# Works with WAV files and probably other formats too
#
# Usage: ./1_FLAC-converter.bash [input_audio_file.wav] [output_audio_file.flac]
#
# Modified by Dr. Nozimo on 03-Feb-2025 (dr.nozimo@gmail.com)

ffmpeg -i ${1} -acodec flac -compression_level 12 -lpc_type cholesky -af aresample=out_sample_rate=48000 ${2}
