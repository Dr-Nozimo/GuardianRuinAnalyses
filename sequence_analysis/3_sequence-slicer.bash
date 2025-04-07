#!/bin/bash

# A script to "slice" a FLAC audio file into segments based on start and end times contained in a file.
# This script will put audio segments in a folder named signal_sequences
# Segments will be named: [progressive number]_{start time]seq.flac
#
# Usage: ./3_sequence-slicer.bash [number of threads] [input_audio_file.flac] [timing_file.csv]
#
# Last modified by Dr. Nozimo on 03-Feb-2025 (dr.nozimo@gmail.com)

cpu_threads=$1
input_audio_file=$2
timing_file=$3

# Ensure the output directory exists
output_dir="signal_sequences"  # Directory where the segments will be saved
mkdir -p "$output_dir"

# Prepare a list to hold the commands
commands=()

# Read the times file line by line
sequence_number=0
while IFS="," read -r start_time end_time; do
    # Output file name (with leading zeros)
    output_file="${output_dir}/$(printf "%03d" ${sequence_number})_${start_time}_seq.flac"

    # Construct the ffmpeg command and add it to the list
    commands+=("ffmpeg -i ${input_audio_file} -ss ${start_time} -to ${end_time} -map_metadata -1 -c:a flac -compression_level 12 -compression_level 12 -lpc_type cholesky ${output_file} -hide_banner -loglevel error")
    
    sequence_number=$((sequence_number + 1))
done < "$timing_file"

# Use GNU Parallel to run n commands in parallel (adjust -j as needed)
echo "Running commands in parallel with ${cpu_threads} threads"
parallel -j "${cpu_threads}" ::: "${commands[@]}"

echo "Finished processing all segments in ${output_dir}"