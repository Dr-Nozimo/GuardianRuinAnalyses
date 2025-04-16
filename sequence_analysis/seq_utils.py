import numpy as np
from scipy import signal
from scipy.ndimage import label

# Window selection
def select_win(win_type, win_size):
    if (win_type == "Hann"):
        win = signal.windows.hann(win_size) # Hann window
    elif (win_type == "Taylor"):
        win = signal.windows.taylor(win_size, nbar=3, sll=25, norm=True) # Taylor window with parameters: nbar (2), sidelobe suppression level (-25)
    elif (win_type == "Rect"):
        win = signal.windows.boxcar(win_size) # Rectangular window
    elif (win_type == "Hamming"):
        win = signal.windows.hamming(win_size) # Rectangular window
    return win

# Spectrogram bandpass filter
def spec_bandpass(spec, f_max, f_bins, f_low, f_high):
    f_bl = int(f_low/f_max*f_bins) # Low frequency bin
    f_bh = int(f_high/f_max*f_bins) # High frequency bin
    return spec[f_bl:f_bh,:]

# Measure time and frequency of detected signals (after correlation and local maxima search)
def meas_time_freq(local_maxima, time_axis, freq_axis):
    times = time_axis[local_maxima[:, 1]] # Time values from indices
    freqs = freq_axis[local_maxima[:, 0]] # Frequency values from indices
    return times, freqs

# Add detected signals to list
def signals2list(signal_type, signals_detected, detected_times, detected_freqs, corr_values):
    for i in range(len(detected_times)):
        signals_detected.append([
            signal_type,  # Signal type
            round(detected_times[i], 2),  # Time rounded to 2 decimal places
            int(detected_freqs[i]),  # Frequency as an integer
            round(corr_values[i], 2)  # Correlation value rounded to 2 decimal places
        ])
    return signals_detected

# Blank the spectrogram based on local maxima
def blank_spectrogram(blanked_spectrogram, local_maxima, t_start_corr, t_end_corr, signal, t_bins, FFT_sample_T):
    for local_max in local_maxima:
        signal_time_width = signal.shape[1] # Calculate signal width (time samples)
        t_idx = local_max[1]  # Time index where signal starts (lower left corner)
        t_start_idx = max(0, t_idx - int(t_start_corr/FFT_sample_T)) # Start time index
        t_end_idx = min(t_bins, t_idx + signal_time_width + int(t_end_corr/FFT_sample_T)) # End time index
        blanked_spectrogram[:, t_start_idx:t_end_idx] = -100 # Blank spectrogram in signal time window
    return blanked_spectrogram

# Remove short detections (noise when detecting tone signals)
def remove_short_detections(arr, min_ones):
    arr = arr.copy()
    labeled, num_features = label(arr)
    for i in range(1, num_features + 1):
        if np.sum(labeled == i) < min_ones:
            arr[labeled == i] = 0
    return arr

# Determine when tones occur
def get_tone_segments(sig_detected):
    det_idx = np.where(sig_detected == 1)[0]
    tone_segm_boundaries = np.where(np.diff(det_idx) > 1)[0] + 1
    return det_idx, np.concatenate(([0], tone_segm_boundaries, [len(det_idx)]))

# Find tone signals based on timing
def find_tone_signals(bin_list, tones_freq_med):
    tone_signals = []
    start_idx = None
    for i, num in enumerate(bin_list):  # Go through detection array
        if num > 0:
            if start_idx is None:  # Beginning of a new sequence of 1s
                start_idx = i
        elif num == 0 and start_idx is not None:  # End the sequence when we hit a 0 after detecting 1s
            tone_signals.append((start_idx, i - 1, tones_freq_med[start_idx]))  # Add median value as third column
            start_idx = None    
    if start_idx is not None:  # If we end with a sequence of 1s and it's still open, close it
        tone_signals.append((start_idx, len(bin_list) - 1, tones_freq_med[start_idx]))  # Add median value as third column
    return tone_signals

# Monster function to translate tones
def translate_tones(tone_signals, FFT_sample_T, seq_name):
    tones_list = [] # List with final output
    i = 0 # Initialize row index
    while i < len(tone_signals):
        duration_samples = tone_signals[i][1] - tone_signals[i][0] # Duration of each sequence, in samples
        row = [tone_signals[i][0], tone_signals[i][1], duration_samples, "", ""] # Add empty 5th column for frequency
        # Check for excessive length
        if (duration_samples > int(2.88*1.1/FFT_sample_T)): # Tone A is usually ~2.88 s, so longer tones mean that A & B or A & C are too close to each other
            raise ValueError("Check for possible A+B or A+C.")
        # Check for tone A
        elif (duration_samples > int(2.88*0.9/FFT_sample_T)): # Tone A is usually ~2.88 s, using 10% margin
            row[3] = "A"
            row[4] = tone_signals[i][2] # Frequency sample
        # Check for excessive length
        elif (duration_samples > int(1.77*1.1/FFT_sample_T)): # Tone B is usually ~1.77 s, so longer tones mean that B & C are too close to each other
            raise ValueError("Check for possible B+C.")
        # Check for B
        elif (duration_samples > int(1.77*0.9/FFT_sample_T)): # Tone B is usually ~1.77 s, using 10% margin
            row[3] = "B"
            row[4] = tone_signals[i][2] # Frequency sample
        # Check for C and split B
        elif (duration_samples > int(0.70*0.70/FFT_sample_T)): # Tone C is made of two tones, the first is usually ~0.70 s, using 30% margin
            if i + 1 < len(tone_signals): # Check if there is a next row
                gap_duration = tone_signals[i + 1][0] - tone_signals[i][1] # Measure duration of gap between tones
                next_duration_samples = tone_signals[i + 1][1] - tone_signals[i + 1][0]
                # Check for split B
                if (gap_duration < int(0.2/FFT_sample_T)): # Tone C gap is ~0.5 s, so if the gap is much shorter, then it's a tone B that has been cut in two
                    B_duration = tone_signals[i + 1][1] - tone_signals[i][0]
                    # Single split in B
                    if (B_duration > int(1.77*0.95/FFT_sample_T)): # Check if B duration is at least 95% of expected duration
                        tones_list.append([tone_signals[i][0], tone_signals[i + 1][1], B_duration, "B", tone_signals[i][2]])  # Merge rows and add "C" label
                        print(f"Seq {seq_name} Warning: Split B signal detected at t = {tone_signals[i][0] * FFT_sample_T:.2f}s")
                        i += 2 # Skip the next row as it was merged with the current one
                        continue
                    # Double split in B
                    else:
                        B_duration = tone_signals[i + 2][1] - tone_signals[i][0]
                        tones_list.append([tone_signals[i][0], tone_signals[i + 2][1], B_duration, "B", tone_signals[i][2]])  # Merge rows and add "C" label
                        print(f"Seq {seq_name} Warning: Double split B signal detected at t = {tone_signals[i][0] * FFT_sample_T:.2f}s")
                        i += 3 # Skip the 2 next rows as they were merged with the current one
                        continue
                # Check for C
                elif (next_duration_samples < int(0.38*1.35/FFT_sample_T)):  # The second tone in C is usually ~0.38 s, using 35% margin
                    tones_list.append([tone_signals[i][0], tone_signals[i + 1][1], (tone_signals[i + 1][1] - tone_signals[i][0]), "C", tone_signals[i][2]])  # Merge rows and add "C" label
                    i += 2 # Skip the next row as it was merged with the current one
                    continue
                else:
                    raise ValueError("C tone only partially detected (missing 2nd half).")
            else:
                raise ValueError("C tone only partially detected (end of tone_signals).")
        else:
            raise ValueError("C tone only partially detected (missing 1st half).")
        
        tones_list.append(row)
        i += 1 # Move to the next row

    return tones_list

# Signal durations (s)
def sig_length(sig_code):
    match sig_code:
        case 'A':
            return 3.00
        case 'B':
            return 1.79
        case 'C':
            return 1.63
        case 'D':
            return 1.61
        case 'E':
            return 1.27
        case 'F':
            return 0.98
        case 'G':
            return 2.12
        case 'X':
            return 16.18

# Tone length metric
def compute_length_metric(tones_list, tone_type, sig_length_func, FFT_sample_T):
    # Precompute expected sample lengths for each tone type
    expected_lengths = {
        "A": int(sig_length_func("A") / FFT_sample_T),
        "B": int(sig_length_func("B") / FFT_sample_T),
        "C": int(sig_length_func("C") / FFT_sample_T),
    }
    # Convert to arrays and initialize length metric
    tone_type_arr = np.array(tone_type)
    length_samples = np.array([row[2] for row in tones_list])
    length_metric = np.zeros(len(length_samples))
    # Loop through tones
    for tone in expected_lengths:
        mask = tone_type_arr == tone
        ref_len = expected_lengths[tone]
        length_metric[mask] = (length_samples[mask] - ref_len) / ref_len
    return length_metric

# Final checks
def validate_list(signals_detected, seq_name):
    # Check 1: EOL occurs only once
    x_count = sum(1 for item in signals_detected if item[0] == 'X')
    if x_count != 1:
        print(f"Seq {seq_name} Error: EOL signal appears more than once!")
        return False
    # Check 2: EOL occurs at the end
    if  signals_detected[-1][0] != 'X':
        print(f"Seq {seq_name} Error: EOL signal found before the end of the sequence!")
        return False
    # Check 3: No consecutive signals of the same type
    for i in range(1, len(signals_detected)):
        if signals_detected[i][0] == signals_detected[i - 1][0]:
            print(f"Seq {seq_name} Error: Consecutive signal '{signals_detected[i][0]}' found at positions {i-1} and {i}.")
            return False
    # Check 4: No excessive gap between signals, set at 90% of 0.98 s (the shortest signal)
    for i in range(1, len(signals_detected)):
        t_gap = signals_detected[i][1] - signals_detected[i-1][1] - sig_length(signals_detected[i-1][0])
        if t_gap > 0.98*0.9:
            t_gap_start = signals_detected[i-1][1] + sig_length(signals_detected[i-1][0])
            print(f"Seq {seq_name} Error: Likely undetected signal at {i} {t_gap_start} s for {t_gap} s")
            return False            
    return True