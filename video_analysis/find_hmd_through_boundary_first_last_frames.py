import argparse
import os
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from scipy.signal import savgol_filter
import matplotlib.pyplot as plt


def compute_gray_blurred(path):
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gray, (5, 5), 0)


def compute_windowed_ssim_drift(frames_dir, window_size=5, verbosity=0):
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.lower().endswith('.jpg')])
    if len(frame_files) <= window_size:
        raise ValueError("Not enough frames for the given window size.")

    ssim_drift = []
    for i in range(len(frame_files) - window_size):
        path1 = os.path.join(frames_dir, frame_files[i])
        path2 = os.path.join(frames_dir, frame_files[i + window_size])
        try:
            img1 = compute_gray_blurred(path1)
            img2 = compute_gray_blurred(path2)
            score, _ = ssim(img1, img2, full=True, data_range=img1.max() - img1.min())
        except Exception as e:
            print(f"[WARN] SSIM computation failed at index {i}: {e}")
            score = 1.0
        ssim_drift.append(score)
        if verbosity >= 2:
            print(f"[DEBUG] SSIM({frame_files[i]} → {frame_files[i+window_size]}) = {score:.4f}")

    return ssim_drift, frame_files


def detect_fade_boundaries(ssim_drift, frame_files, window_size, ssim_threshold, verbosity=0):
    smoothed = savgol_filter(ssim_drift, window_length=window_size, polyorder=2)
    below = np.array(smoothed) < ssim_threshold

    fade_in_start, fade_in_end, fade_out_start, fade_out_end = None, None, None, None

    # Fade-in detection (left to right)
    for i in range(1, len(below)):
        if below[i] and not below[i - 1] and fade_in_start is None:
            fade_in_start = i
        if not below[i] and below[i - 1] and fade_in_start is not None and fade_in_end is None:
            fade_in_end = i
        if fade_in_start is not None and fade_in_end is not None:
            break

    # Fade-out detection (right to left)
    for i in range(len(below) - 2, 0, -1):
        if below[i] and not below[i + 1] and fade_out_end is None:
            fade_out_end = i + 1
        if not below[i] and below[i + 1] and fade_out_end is not None and fade_out_start is None:
            fade_out_start = i + 1
        if fade_out_start is not None and fade_out_end is not None:
            break

    def safe_name(index):
        if index is None or index + window_size >= len(frame_files):
            return None
        return frame_files[index + window_size]  # actual frame of drift

    transitions = {
        "fade_in_start": safe_name(fade_in_start),
        "fade_in_end": safe_name(fade_in_end),
        "fade_out_start": safe_name(fade_out_start),
        "fade_out_end": safe_name(fade_out_end),
    }

    if verbosity >= 1:
        print("[INFO] Fade transition detection:")
        for k, v in transitions.items():
            print(f"  {k.replace('_', ' ').capitalize()}: {v or 'Not detected'}")

    return transitions

def compute_windowed_intensity_mean(frames_dir, window_size=5, verbosity=0):
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.lower().endswith('.jpg')])
    if len(frame_files) <= window_size:
        raise ValueError("Not enough frames for the given window size.")

    intensity_means = []
    for i in range(len(frame_files) - window_size):
        path1 = os.path.join(frames_dir, frame_files[i])
        path2 = os.path.join(frames_dir, frame_files[i + window_size])
        try:
            img1 = compute_gray_blurred(path1)
            img2 = compute_gray_blurred(path2)
            mean_intensity = (np.mean(img1) + np.mean(img2)) / 2
        except Exception as e:
            print(f"[WARN] Intensity mean computation failed at index {i}: {e}")
            mean_intensity = 0.0
        intensity_means.append(mean_intensity)
        if verbosity >= 2:
            print(f"[DEBUG] Intensity Mean({frame_files[i]} → {frame_files[i+window_size]}) = {mean_intensity:.4f}")

    return intensity_means, frame_files

def compute_windowed_intensity_drift(frames_dir, window_size=5, verbosity=0):
    intensity_means, frame_files = compute_windowed_intensity_mean(frames_dir, window_size, verbosity)
    intensity_drift = []
    for i in range(len(intensity_means) - window_size):
        drift = abs(intensity_means[i + window_size] - intensity_means[i])
        intensity_drift.append(drift)
        if verbosity >= 2:
            print(f"[DEBUG] Intensity Drift({frame_files[i]} → {frame_files[i+window_size]}) = {drift:.4f}")
    return intensity_drift, frame_files

def compute_windowed_saturation_mean(frames_dir, window_size=5, verbosity=0):
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.lower().endswith('.jpg')])
    if len(frame_files) <= window_size:
        raise ValueError("Not enough frames for the given window size.")

    saturation_means = []
    for i in range(len(frame_files) - window_size):
        path1 = os.path.join(frames_dir, frame_files[i])
        path2 = os.path.join(frames_dir, frame_files[i + window_size])
        try:
            img1 = cv2.imread(path1)
            img2 = cv2.imread(path2)
            hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
            hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
            mean_saturation = (np.mean(hsv1[:, :, 1]) + np.mean(hsv2[:, :, 1])) / 2
        except Exception as e:
            print(f"[WARN] Saturation mean computation failed at index {i}: {e}")
            mean_saturation = 0.0
        saturation_means.append(mean_saturation)
        if verbosity >= 2:
            print(f"[DEBUG] Saturation Mean({frame_files[i]} → {frame_files[i+window_size]}) = {mean_saturation:.4f}")

    return saturation_means, frame_files

def compute_windowed_edge_density(frames_dir, window_size=5, verbosity=0):
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.lower().endswith('.jpg')])
    if len(frame_files) <= window_size:
        raise ValueError("Not enough frames for the given window size.")

    edge_densities = []
    for i in range(len(frame_files) - window_size):
        path1 = os.path.join(frames_dir, frame_files[i])
        path2 = os.path.join(frames_dir, frame_files[i + window_size])
        try:
            img1 = cv2.imread(path1)
            img2 = cv2.imread(path2)
            edges1 = cv2.Canny(img1, 100, 200)
            edges2 = cv2.Canny(img2, 100, 200)
            edge_density = (np.sum(edges1) + np.sum(edges2)) / (edges1.shape[0] * edges1.shape[1] * 255)
        except Exception as e:
            print(f"[WARN] Edge density computation failed at index {i}: {e}")
            edge_density = 0.0
        edge_densities.append(edge_density)
        if verbosity >= 2:
            print(f"[DEBUG] Edge Density({frame_files[i]} → {frame_files[i+window_size]}) = {edge_density:.4f}")

    return edge_densities, frame_files

from scipy.signal import argrelextrema

def compute_metrics_over_window(frames_dir, window_size=5):
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.lower().endswith('.jpg')])
    if len(frame_files) <= window_size:
        raise ValueError("Not enough frames for the given window size.")

    ssim_at_m1 = []
    ssim_drift = []
    intensity_at_m1 = []
    intensity_drift = []
    edge_density_at_m1 = []
    edge_drift = []
    contrast_at_m1 = []
    contrast_drift = []

    def compute_metrics(img_path):
        img = cv2.imread(img_path)
        if img is None:
            raise ValueError(f"Could not read image: {img_path}")
        img_blur = cv2.GaussianBlur(img, (5, 5), 0)
        gray = cv2.cvtColor(img_blur, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        return {
            'gray': gray,
            'intensity': np.mean(gray),
            'edges': np.sum(edges > 0) / edges.size,
            'contrast': np.std(gray)
        }

    for i in range(len(frame_files) - window_size):
        path1 = os.path.join(frames_dir, frame_files[i])
        path2 = os.path.join(frames_dir, frame_files[i + window_size])
        try:
            m1 = compute_metrics(path1)
            m2 = compute_metrics(path2)

            ssim_score, _ = ssim(m1['gray'], m2['gray'], full=True, data_range=255)
            ssim_drift.append(1 - ssim_score)  # Convert to drift
            intensity_at_m1.append(m1['intensity'])
            intensity_drift.append(abs(m1['intensity'] - m2['intensity']))
            edge_density_at_m1.append(m1['edges'])
            edge_drift.append(abs(m1['edges'] - m2['edges']))
            contrast_at_m1.append(m1['contrast'])
            contrast_drift.append(abs(m1['contrast'] - m2['contrast']))
        except Exception as e:
            print(f"[WARN] Failed at frame {i}: {e}")
            ssim_drift.append(0.0)
            intensity_drift.append(0.0)
            intensity_at_m1.append(0.0)
            edge_drift.append(0.0)
            edge_density_at_m1.append(0.0)
            contrast_at_m1.append(0.0)
            contrast_drift.append(0.0)

    # Smooth metrics
    ssim_drift_smoothed = savgol_filter(ssim_drift, window_length=7, polyorder=2)
    intensity_at_m1_smoothed = savgol_filter(intensity_at_m1, window_length=7, polyorder=2)
    intensity_drift_smoothed = savgol_filter(intensity_drift, window_length=7, polyorder=2)
    edge_density_at_m1_smoothed = savgol_filter(edge_density_at_m1, window_length=7, polyorder=2)
    edge_density_drift_smoothed = savgol_filter(edge_drift, window_length=7, polyorder=2)
    contrast_at_m1_smoothed = savgol_filter(contrast_at_m1, window_length=7, polyorder=2)
    contrast_drift_smoothed = savgol_filter(contrast_drift, window_length=7, polyorder=2)


    # Print local maxima of SSIM drift
    maxima_indices = argrelextrema(np.array(ssim_drift_smoothed), np.greater)[0]
    print("[INFO] Local maxima in SSIM Drift:")
    for i in maxima_indices:
        frame_index = i + window_size
        print(f"  Index: {i}, Frame: {frame_files[frame_index] if frame_index < len(frame_files) else 'Out of range'}, SSIM Drift: {ssim_drift_smoothed[i]:.4f}")

    # Plotting
    # Normalize all metrics to [0, 1] for comparable visualization
    def normalize(arr):
        arr = np.array(arr)
        min_val = np.min(arr)
        max_val = np.max(arr)
        if max_val - min_val == 0:
            return arr
        return (arr - min_val) / (max_val - min_val)

    x = list(range(len(ssim_drift)))
    plt.figure(figsize=(12, 8))
    plt.plot(x, normalize(ssim_drift_smoothed), label='1 - SSIM Drift', linewidth=2)
    plt.vlines([92-window_size-1, 168-window_size-1], ymin=0, ymax=1, colors='red', linestyles='dashed', label='Fade in/Out Boundaries')
    plt.plot(x, normalize(intensity_at_m1_smoothed), label='Intensity at M-1', linewidth=2)
    plt.plot(x, normalize(intensity_drift_smoothed), label='Intensity Drift', linewidth=2)
    plt.plot(x, normalize(edge_density_at_m1_smoothed), label='Edge Density at M-1', linewidth=2)
    plt.plot(x, normalize(edge_density_drift_smoothed), label='Edge Density Drift', linewidth=2)
    # plt.plot(x, normalize(contrast_at_m1_smoothed), label='Contrast', linewidth=2)
    # plt.plot(x, normalize(contrast_drift_smoothed), label='Contrast Drift', linewidth=2)
    plt.title("Visual Metric Drift Between Frames (Normalized)")
    plt.xlabel("Frame Index (Start of Window)")
    plt.ylabel("Normalized Metric Value")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    # plt.show()
    plt.savefig(os.path.join(os.path.dirname(frames_dir), f"visual_metric_drift_ssim_{window_size}_normalized.png"))
    print(f"[INFO] Visual metric drift plot saved as 'visual_metric_drift_ssim_{window_size}_normalized.png'")

    return {
        "frame_files": frame_files,
        "ssim": ssim_drift,
        "intensity": intensity_drift,
        "edges": edge_drift,
        "ssim_maxima_indices": maxima_indices
    }

def main():
    parser = argparse.ArgumentParser(description="Detect VR-to-environment fade transitions using windowed SSIM drift.")
    parser.add_argument("frames_dir", type=str, help="Directory containing ordered JPG frames.")
    parser.add_argument("--window", type=int, default=7, help="Window size for SSIM drift.")
    parser.add_argument("--ssim_threshold", type=float, default=0.95, help="SSIM threshold to detect scene change.")
    parser.add_argument("--output", type=str, default="", help="Optional file to write results.")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    verbosity = 2 if args.debug else 1 if args.verbose else 0

    frames_dir = os.path.realpath(args.frames_dir)
    if not os.path.isdir(frames_dir):
        print(f"\033[0;31m[ERROR]\033[0m Frames directory '{frames_dir}' does not exist.")
        exit(1)

    try:
        # ssim_drift, frame_files = compute_windowed_ssim_drift(
        #     frames_dir, window_size=args.window, verbosity=verbosity
        # )
        #
        # intensity_means, _ = compute_windowed_intensity_mean(frames_dir, window_size=args.window, verbosity=verbosity)
        # intensity_drift, _ = compute_windowed_intensity_drift(frames_dir, window_size=args.window, verbosity=verbosity)
        # saturation_mean, _ = compute_windowed_saturation_mean(frames_dir, window_size=args.window, verbosity=verbosity)
        # edge_density, _ = compute_windowed_edge_density(frames_dir, window_size=args.window, verbosity=verbosity)
        #
        # # plot ssim drift if verbosity >= 2
        # if verbosity >= 2:
        #     plt.plot(ssim_drift)
        #
        #     plt.title("SSIM Drift")
        #     plt.xlabel("Frame Index")
        #     plt.ylabel("SSIM")
        #     plt.grid()
        #     plt.show()

        compute_metrics_over_window(frames_dir, window_size=args.window)

        # transitions = detect_fade_boundaries(
        #     ssim_drift, frame_files, args.window, args.ssim_threshold, verbosity=verbosity
        # )

        # print("\n\033[1;32m[RESULTS]\033[0m")
        # for key, val in transitions.items():
        #     print(f"  {key.replace('_', ' ').capitalize()}: {val or 'Not detected'}")
        #
        # if args.output:
        #     with open(args.output, 'w') as f:
        #         for key, val in transitions.items():
        #             f.write(f"{key}: {val or 'Not detected'}\n")
        #     print(f"[INFO] Results saved to {args.output}")

    except Exception as e:
        print(f"\033[0;31m[ERROR]\033[0m {e}")
        exit(1)


if __name__ == "__main__":
    main()