#!/bin/bash

# A script to "slice" a FLAC audio file into 25 min segments with 5 min overlap.
# This script will put audio segments in a folder named tmp_segments
# Segments will be named: [progressive number]_segment.flac
# Segments are converted to mono because stereo is not necessary at this stage
#
# Usage: ./1_segment-slicer.bash recording-name.flac
#
# Last modified by Dr. Nozimo on 02-Feb-2025 (dr.nozimo@gmail.com)

# Input file and output directory
input_file=${1}
output_folder="tmp_segments"  # Directory where the segments will be saved

# Segment parameters
segment_duration=1500  # 20 min
overlap_duration=300  # 5 min

# Ensure the output directory exists
mkdir -p "$output_folder"

# Get the total duration of the audio file (in seconds)
audio_duration=$(ffmpeg -i "$input_file" 2>&1 | grep "Duration" | awk '{print $2}' | tr -d ',')
audio_duration_seconds=$(echo "$audio_duration" | awk -F: '{print ($1 * 3600) + ($2 * 60) + $3}')

# Start slicing
start_time=0
segment_number=0
while [ $start_time -lt $audio_duration_seconds ]; do
    # Calculate the end time for this segment
    end_time=$((start_time + segment_duration))

    # Make sure the end time doesn't exceed the original audio file duration
    if [ $end_time -gt $audio_duration_seconds ]; then
        end_time=$audio_duration_seconds
    fi

    # Output file name (with leading zeros)
    output_file="$output_folder/$(printf "%03d" $segment_number)_segment.flac"

    # Slice the audio and save it to the output file (re-encoding to ensure proper slicing)
    ffmpeg -i "$input_file" -ss $start_time -to $end_time -map_metadata -1 -ac 1 -c:a flac "$output_file" -hide_banner -loglevel error

    echo "Exported segment ${segment_number} of ${1} to $output_file"

    # Update the start time for the next segment (with overlap)
    start_time=$((start_time + segment_duration - overlap_duration))
    segment_number=$((segment_number + 1))
done