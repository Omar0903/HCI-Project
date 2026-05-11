# Configuration
input_folder = '3-class'
class_mapping = {
    'yukari': 'Up',
    'asagi': 'Down',
    'sag': 'Right',
    'sol': 'Left',
    'kirp': 'Blink'
}

def process_and_split_with_trial_numbers(test_size=0.20):
    # 1. Get all .txt files
    if not os.path.exists(input_folder):
        print(f"Error: Folder '{input_folder}' not found.")
        return

    all_files = [f for f in os.listdir(input_folder) if f.endswith('.txt')]
    
    # 2. Extract Unique Trials while keeping their numbers and labels
    # We will store information as a list of dictionaries to easily split later
    unique_trials_info = []
    seen_bases = set()

    for f in all_files:
        lower_f = f.lower()
        for key, val in class_mapping.items():
            if key in lower_f:
                # Extract base name (e.g., asagi10) and trial number (e.g., 10)
                # Regex looks for the key followed by digits
                match = re.search(rf"{key}(\d+)", lower_f)
                if match:
                    trial_num = match.group(1)
                    base_name = f"{key}{trial_num}" # Example: asagi10
                    
                    if base_name not in seen_bases:
                        unique_trials_info.append({
                            'base_name': base_name,
                            'label': val,
                            'number': trial_num
                        })
                        seen_bases.add(base_name)
                break

    # 3. Split the trials (Unique Trials) to ensure H/V stay together
    train_info, test_info = train_test_split(
        unique_trials_info,
        test_size=test_size,
        random_state=42,
        stratify=[t['label'] for t in unique_trials_info]
    )

    def build_dataset(info_list):
        data_rows = []
        for info in info_list:
            base = info['base_name']
            # Search for the H and V files associated with this trial base
            for suffix in ['h.txt', 'v.txt']:
                target_filename = base + suffix
                # Case-insensitive match in the file list
                actual_file = next((f for f in all_files if f.lower() == target_filename), None)
                
                if actual_file:
                    file_path = os.path.join(input_folder, actual_file)
                    with open(file_path, 'r') as f:
                        signal = [int(line.strip()) for line in f if line.strip()]
                    
                    # Construct the row with ALL metadata
                    row = {
                        'Trial_ID': actual_file.replace('.txt', ''),
                        'Trial_Number': info['number'],
                        'Label': info['label'],
                        'Channel': 'H' if 'h' in suffix else 'V'
                    }
                    # Add signal points
                    for i, v in enumerate(signal):
                        row[f'Point_{i}'] = v
                    data_rows.append(row)
        
        return pd.DataFrame(data_rows)

    # 4. Generate DataFrames
    train_df = build_dataset(train_info)
    test_df = build_dataset(test_info)

    # Reorder columns to make sure metadata is at the beginning
    def reorder(df):
        if df.empty: return df
        metadata = ['Trial_ID', 'Trial_Number', 'Label', 'Channel']
        points = sorted([c for c in df.columns if c.startswith('Point_')], 
                        key=lambda x: int(x.split('_')[1]))
        return df[metadata + points]

    train_df = reorder(train_df)
    test_df = reorder(test_df)

    # 5. Save files
    train_df.to_csv('EOG_train.csv', index=False)
    test_df.to_csv('EOG_test.csv', index=False)
    
    print("Files saved successfully with Trial_Number column!")
    print(f"Training trials: {len(train_info)} | Testing trials: {len(test_info)}")

---
import pandas as pd
import numpy as np

def load_csv_to_paired_dictionary(csv_path):
    # 1. Read the CSV file
    df = pd.read_csv(csv_path)
    
    # 2. Create the dictionary to hold the results
    current_data = {}
    
    # 3. Group data by 'Trial_Number' and 'Label' to pair H and V rows
    grouped = df.groupby(['Trial_Number', 'Label'])
    
    for (trial_num, label), group in grouped:
        # Get all columns that start with 'Point_'
        signal_cols = [c for c in df.columns if c.startswith('Point_')]
        
        # Extract Horizontal (H) and Vertical (V) data for this specific trial
        h_row = group[group['Channel'] == 'H']
        v_row = group[group['Channel'] == 'V']
        
        # Convert the row values into a 1D Numpy array
        # We use .iloc[0] because we expect only one H and one V per trial
        if not h_row.empty and not v_row.empty:
            h_sig = h_row[signal_cols].values.flatten()
            v_sig = v_row[signal_cols].values.flatten()
            
            # Use the label as the dictionary key (or f"{label}_{trial_num}" for uniqueness)
            dict_key = f"{label}_{trial_num}"
            current_data[dict_key] = [h_sig, v_sig]
            
    return current_data
---
def plot_complex_grid(data_dict, rows=20, cols=5):
    trial_keys = list(data_dict.keys())
    total_plots = rows * cols
    
    # Create a large figure
    # Width = 4 units per column, Height = 3 units per row
    fig = plt.figure(figsize=(cols * 4, rows * 3))
    
    for i in range(min(total_plots, len(trial_keys))):
        key = trial_keys[i]
        h_signal = data_dict[key][0]
        v_signal = data_dict[key][1]
        
        # Calculate position for the H signal (Top part of the cell)
        # We use a grid of (rows*2) to stack H and V
        ax_h = plt.subplot(rows * 2, cols, i + 1 + (i // cols) * cols)
        ax_h.plot(h_signal, color='blue', linewidth=0.7)
        ax_h.set_title(f"Trial: {key}", fontsize=8)
        ax_h.tick_params(axis='both', which='both', labelsize=7)
        ax_h.grid(True, alpha=0.2)
        
        # Calculate position for the V signal (Bottom part of the cell)
        ax_v = plt.subplot(rows * 2, cols, i + 1 + (i // cols + 1) * cols)
        ax_v.plot(v_signal, color='red', linewidth=0.7)
        ax_v.tick_params(axis='both', which='both', labelsize=7)
        ax_v.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.show()

def plot_wavelet_grid(X_wavelet, y_labels, rows=10, cols=5):
    total_samples = X_wavelet.shape[0]
    total_plots = min(rows * cols, total_samples)
    
    # Calculate the midpoint because H and V are concatenated
    # Since X_wavelet is [H_features, V_features], the middle index is:
    mid_point = X_wavelet.shape[1] // 2
    
    fig = plt.figure(figsize=(cols * 4, rows * 3))
    
    for i in range(total_plots):
        # Extract the combined row
        feature_row = X_wavelet[i]
        label = y_labels[i]
        
        # Split back into H and V parts
        h_wave = feature_row[:mid_point]
        v_wave = feature_row[mid_point:]
        
        # Position for H (Top)
        ax_h = plt.subplot(rows * 2, cols, i + 1 + (i // cols) * cols)
        ax_h.plot(h_wave, color='blue', linewidth=0.7)
        ax_h.set_title(f"Idx:{i} | {label}", fontsize=8)
        ax_h.tick_params(labelsize=7)
        ax_h.grid(True, alpha=0.2)
        
        # Position for V (Bottom)
        ax_v = plt.subplot(rows * 2, cols, i + 1 + (i // cols + 1) * cols)
        ax_v.plot(v_wave, color='red', linewidth=0.7)
        ax_v.tick_params(labelsize=7)
        ax_v.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.show()

import matplotlib.pyplot as plt
import numpy as np

def plot_psd_grid(X_psd, y_labels, fs=176, rows=10, cols=5):
    total_samples = X_psd.shape[0]
    total_plots = min(rows * cols, total_samples)
    
    # Each row in X_psd has [H_psd, V_psd]
    # The length of one channel's PSD is total_features // 2
    num_features_per_channel = X_psd.shape[1] // 2
    
    # Reconstruct the frequency axis (f) for plotting
    # Periodogram length is (N/2 + 1)
    # We can derive it from the data length
    f = np.linspace(0, fs / 2, num_features_per_channel)
    
    fig = plt.figure(figsize=(cols * 4, rows * 3))
    
    for i in range(total_plots):
        # Extract features and label
        feature_row = X_psd[i]
        label = y_labels[i]
        
        # Split into H and V
        h_psd = feature_row[:num_features_per_channel]
        v_psd = feature_row[num_features_per_channel:]
        
        # --- Position for H (Top) ---
        ax_h = plt.subplot(rows * 2, cols, i + 1 + (i // cols) * cols)
        # We use semilogy for PSD because values vary in orders of magnitude
        ax_h.semilogy(f, h_psd, color='blue', linewidth=0.8) 
        ax_h.set_title(f"Idx:{i} | {label}", fontsize=8)
        ax_h.tick_params(labelsize=7)
        ax_h.grid(True, which='both', alpha=0.2)
        
        # --- Position for V (Bottom) ---
        ax_v = plt.subplot(rows * 2, cols, i + 1 + (i // cols + 1) * cols)
        ax_v.semilogy(f, v_psd, color='red', linewidth=0.8)
        ax_v.set_xlabel("Freq (Hz)", fontsize=7)
        ax_v.tick_params(labelsize=7)
        ax_v.grid(True, which='both', alpha=0.2)

    plt.tight_layout()
    plt.show()

---
def butter_bandpass_filter(Input_Signal,Low_cutoff,High_Cutoff,Sampling_Rate,order):
    nyq=0.5*Sampling_Rate
    low=Low_cutoff/nyq
    high=High_Cutoff/nyq
    Numeator,denminator = butter(order,[low,high],btype='band',analog=False,fs=None)
    filtered=filtfilt(Numeator,denminator,Input_Signal)
    return filtered
---
def create_raw_arrays(data_dict):
    X_list = []
    y_list = []
    
    for key, signals in data_dict.items():
        label = key.split('_')[0]
        
        # signals[0]  Horizontal
        # signals[1]  Vertical
        h_sig = signals[0]
        v_sig = signals[1]
        
        combined_signal = np.concatenate([h_sig, v_sig])
        
        X_list.append(combined_signal)
        y_list.append(label)
    
    return np.array(X_list), np.array(y_list)

---
def ExtractMixFeatures(signal):
    """
    Extracts a combination of Morphological and Statistical features 
    from the time domain signal.
    """
    # --- Morphological Features ---
    peaks, _ = find_peaks(signal)
    if len(peaks) > 0:
        max_peak = np.max(signal[peaks])
    else:
        max_peak = np.max(signal)
        
    # Calculate Area Under the Curve (AUC) using Simpson's rule
    area = simpson(signal)
    
    # --- Statistical Features ---
    mu = np.mean(signal)
    # Calculate the variance (measure of signal spread)
    var = np.var(signal)
    std = np.std(signal)
    
    return [max_peak, area, mu, var, std]
---
def build_mix_features_matrix(data_dict):
    X_mix = []
    
    for key, signals in data_dict.items():
        h_sig = signals[0]
        v_sig = signals[1]
        
        # 1. Extract features for Horizontal channel
        h_features = ExtractMixFeatures(h_sig)
        
        # 2. Extract features for Vertical channel
        v_features = ExtractMixFeatures(v_sig)
        
        # 3. Combine them 
        combined_features = np.concatenate([h_features, v_features])
        
        X_mix.append(combined_features)
        
    return np.array(X_mix)
---
def extract_wavelet_features(signal):
    """
    Fs = 176 Hz, Level = 2.
    Extracts cA2 coefficients covering the 0-22 Hz range.
    """
    coeffs = pywt.wavedec(signal, 'db1', level=2)
    wavelet_features = coeffs[0]
    
    return wavelet_features
---
def build_wavelet_features_matrix(data_dict):
    X_wavelet = []
    
    for key, signals in data_dict.items():
        h_sig = signals[0]
        v_sig = signals[1]
        
        # 1. Extract wavelet coefficients for both channels
        h_wave = extract_wavelet_features(h_sig)
        v_wave = extract_wavelet_features(v_sig)
        
        # 2. Concatenate H and V wavelet features
        # This will create a long row containing [H_wavelet_coeffs, V_wavelet_coeffs]
        combined_wavelet = np.concatenate([h_wave, v_wave])
        
        X_wavelet.append(combined_wavelet)
        
    return np.array(X_wavelet)
---
def extract_ar_features(signal, lags=10):  

    model = AutoReg(signal, lags=lags).fit()
    
    return model.params 
---
def build_ar_features_matrix(data_dict, lags):
    X_ar = []
    
    for key, signals in data_dict.items():
        h_sig = signals[0]
        v_sig = signals[1]
        
        # 1. Extract ar coefficients for both channels
        h_ar = extract_ar_features(h_sig, lags)
        v_ar = extract_ar_features(v_sig, lags)
        
        # 2. Concatenate H and V ar features
        combined_ar = np.concatenate([h_ar, v_ar])
        
        X_ar.append(combined_ar)
        
    return np.array(X_ar)
---
import scipy
def extract_psd_features(signal, fs=176):
    
    f, psd = scipy.signal.periodogram(signal, fs, scaling='density')    
    # relevant_indices = np.where(f <= 20)[0]
    # psd_features = psd[relevant_indices]
    
    return f, psd
---
def build_psd_features_matrix(data_dict):
    X_psd = []
    
    for key, signals in data_dict.items():
        h_sig = signals[0]
        v_sig = signals[1]
        
        # 1. Extract psd coefficients for both channels
        _,h_psd = extract_psd_features(h_sig)
        _,v_psd = extract_psd_features(v_sig)
        
        # 2. Concatenate H and V psd features
        combined_psd = np.concatenate([h_psd, v_psd])
        
        X_psd.append(combined_psd)
        
    return np.array(X_psd)
---
# def extract_ar_features2(signal, lags=10):
#     from scipy.signal import detrend
#     import numpy as np
#     from statsmodels.tsa.ar_model import AutoReg
    
#     signal = detrend(signal)
#     std = np.std(signal)
    
#     if std == 0:
#         return np.zeros(lags)
    
#     signal = (signal - np.mean(signal)) / std
    
#     model = AutoReg(signal, lags=lags).fit()
    
#     return model.params  
---
import numpy as np
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

# ========= OvO Model =========
def train_and_evaluate_ovo(X_train, X_test, y_train, y_test, feature_name):
    model = make_pipeline(
        StandardScaler(),
        SVC(kernel='rbf', decision_function_shape='ovo', C=1, gamma='scale')
    )

    # 1. Train the model
    model.fit(X_train, y_train)

    # 2. Predict on Train data (To get Train Accuracy)
    y_train_pred = model.predict(X_train)
    train_acc = accuracy_score(y_train, y_train_pred)

    # 3. Predict on Test data (To get Test Accuracy)
    y_test_pred = model.predict(X_test)
    test_acc = accuracy_score(y_test, y_test_pred)

    # 4. Cross Validation (On Train set)
    cv_score = cross_val_score(model, X_train, y_train, cv=5).mean()

    # Improved Print Statement
    print(f"{feature_name:10} -> Train Acc: {train_acc*100:6.2f}% | Test Acc: {test_acc*100:6.2f}% | CV: {cv_score*100:6.2f}%")

    return test_acc
    
# ========= Run All Features =========
accuracies = {}
accuracies["Raw"] = train_and_evaluate_ovo(X_train_raw, X_test_raw, y_train, y_test, "Raw Data")
accuracies["Mix"] = train_and_evaluate_ovo(X_train_mix, X_test_mix, y_train, y_test, "Mix")
accuracies["Wavelet"] = train_and_evaluate_ovo(X_train_wavelet, X_test_wavelet, y_train, y_test, "Wavelet")
accuracies["AR"] = train_and_evaluate_ovo(X_train_autoreg, X_test_autoreg, y_train, y_test, "AR")
accuracies["PSD"] = train_and_evaluate_ovo(X_train_psd, X_test_psd, y_train, y_test, "PSD")

# ========= Best Feature =========
best_feature = max(accuracies, key=accuracies.get)
print(f"\n🔥 Best Feature using OvO SVM: {best_feature} ({accuracies[best_feature]*100:.2f}%)")
---
# ========= OvR Model =========

def train_and_evaluate_ovr(X_train, X_test, y_train, y_test, feature_name):
    model = make_pipeline(
        StandardScaler(),
        SVC(kernel='rbf', C=1, gamma='scale')
    )

    # 1. Train the model
    model.fit(X_train, y_train)

    # 2. Predict on Train data (To get Train Accuracy)
    y_train_pred = model.predict(X_train)
    train_acc = accuracy_score(y_train, y_train_pred)

    # 3. Predict on Test data (To get Test Accuracy)
    y_test_pred = model.predict(X_test)
    test_acc = accuracy_score(y_test, y_test_pred)

    # 4. Cross Validation (On Train set)
    cv_score = cross_val_score(model, X_train, y_train, cv=5).mean()

    # Improved Print Statement
    print(f"{feature_name:10} -> Train Acc: {train_acc*100:6.2f}% | Test Acc: {test_acc*100:6.2f}% | CV: {cv_score*100:6.2f}%")

    return test_acc
# ========= Run All Features =========
accuracies = {}
accuracies["Raw"] = train_and_evaluate_ovr(X_train_raw, X_test_raw, y_train, y_test, "Raw Data")
accuracies["Mix"] = train_and_evaluate_ovr(X_train_mix, X_test_mix, y_train, y_test, "Mix")
accuracies["Wavelet"] = train_and_evaluate_ovr(X_train_wavelet, X_test_wavelet, y_train, y_test, "Wavelet")
accuracies["AR"] = train_and_evaluate_ovr(X_train_autoreg, X_test_autoreg, y_train, y_test, "AR")
accuracies["PSD"] = train_and_evaluate_ovr(X_train_psd, X_test_psd, y_train, y_test, "PSD")

# ========= Best Feature =========
best_feature = max(accuracies, key=accuracies.get)
print(f"\n🔥 Best Feature using OvR SVM: {best_feature} ({accuracies[best_feature]*100:.2f}%)")