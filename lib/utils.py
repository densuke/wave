import numpy as np
import wave
import os
import toml
import io
from typing import Any, Dict, Optional

def read_wav_file(file_path: str) -> np.ndarray:
    """WAVファイルを読み取り、サンプルデータを返す"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    with wave.open(file_path, 'r') as wav_file:
        n_frames = wav_file.getnframes()
        frames = wav_file.readframes(n_frames)
        samples = np.frombuffer(frames, dtype=np.int16)
    return samples

def calculate_fft(segment: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    """FFTを計算し、周波数と振幅を返す"""
    fft_result = np.fft.fft(segment, n=2**int(np.ceil(np.log2(len(segment))) + 1))
    freqs = np.fft.fftfreq(len(fft_result), d=1/sample_rate)
    magnitude = np.abs(fft_result)
    return freqs, magnitude

def validate_bit_string(bit_string: str) -> None:
    """ビット列が有効かどうかを検証"""
    if not all(bit in '01' for bit in bit_string):
        raise ValueError("ビット列には0と1のみを含めてください。")

def validate_noise_level(noise_level: int) -> None:
    """ノイズレベルが有効かどうかを検証"""
    if not (0 <= noise_level <= 5):
        raise ValueError("ノイズレベルは0〜5の範囲で指定してください。")

def load_config_toml(config_path: str = "config.toml") -> Dict[str, Any]:
    """config.tomlを読み込んでdictで返す（encoding=utf-8固定）"""
    with open(config_path, "r", encoding="utf-8") as f:
        return toml.load(io.StringIO(f.read()))

def get_config_value(key: str, config_path: str = "config.toml") -> Optional[Any]:
    """config.tomlからkeyの値を取得"""
    config = load_config_toml(config_path)
    return config.get(key)

def set_config_value(key: str, value: Any, config_path: str = "config.toml") -> None:
    """config.tomlのkeyの値をvalueに書き換える（他はそのまま）"""
    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(config_path, "w", encoding="utf-8") as f:
        found = False
        for line in lines:
            if line.strip().startswith(f"{key}"):
                f.write(f"{key} = {value}\n")
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f"{key} = {value}\n")
