import numpy as np
import wave
import os

def read_wav_file(file_path):
    """WAVファイルを読み取り、サンプルデータを返す"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    with wave.open(file_path, 'r') as wav_file:
        n_frames = wav_file.getnframes()
        frames = wav_file.readframes(n_frames)
        samples = np.frombuffer(frames, dtype=np.int16)
    return samples

def calculate_fft(segment, sample_rate):
    """FFTを計算し、周波数と振幅を返す"""
    fft_result = np.fft.fft(segment, n=2**int(np.ceil(np.log2(len(segment))) + 1))
    freqs = np.fft.fftfreq(len(fft_result), d=1/sample_rate)
    magnitude = np.abs(fft_result)
    return freqs, magnitude

def validate_bit_string(bit_string):
    """ビット列が有効かどうかを検証"""
    if not all(bit in '01' for bit in bit_string):
        raise ValueError("ビット列には0と1のみを含めてください。")

def validate_noise_level(noise_level):
    """ノイズレベルが有効かどうかを検証"""
    if not (0 <= noise_level <= 5):
        raise ValueError("ノイズレベルは0〜5の範囲で指定してください。")