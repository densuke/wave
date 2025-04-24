import toml

# 設定を読み込む
config = toml.load("config.toml")
DURATION = config["DURATION"]
SAMPLE_RATE = config["SAMPLE_RATE"]
NOISE_LEVEL = config["NOISE_LEVEL"]

from lib.utils import validate_bit_string, validate_noise_level
import wave
import struct
import math
import sys
import random

def generate_tone(bit_string, duration=DURATION, sample_rate=SAMPLE_RATE, noise_level=NOISE_LEVEL):
    """
    0と1の文字列から、それぞれ440Hzと880Hzの音を生成し、ノイズを加えたWAVファイルに保存する。

    :param bit_string: 0と1の並んだ文字列
    :param duration: 各音の長さ（秒）
    :param sample_rate: サンプリングレート
    :param noise_level: ノイズの強さ（0〜5）
    """
    # 周波数のマッピング
    freq_map = {'0': 440, '1': 880}

    # WAVファイルの設定
    output_file = "output.wav"
    amplitude = 32767  # 最大振幅（16ビットPCM）

    # サンプルデータを格納するリスト
    samples = []

    for bit in bit_string:
        if bit not in freq_map:
            print(f"無効な文字: {bit}（スキップします）")
            continue

        frequency = freq_map[bit]
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            sample = amplitude * math.sin(2 * math.pi * frequency * t)
            # ノイズを加える（ノイズレベルに応じて周波数の幅を調整）
            max_noise = 100 + (noise_level * 100)  # ノイズ幅を100Hz単位で増加
            noise = random.uniform(-max_noise, max_noise)
            sample_with_noise = sample + noise
            # 値を16ビット整数の範囲にクリップ
            sample_with_noise = max(-amplitude, min(amplitude, sample_with_noise))
            samples.append(int(sample_with_noise))

    # WAVファイルの書き込み
    with wave.open(output_file, 'w') as wav_file:
        wav_file.setnchannels(1)  # モノラル
        wav_file.setsampwidth(2)  # 16ビット
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack('<' + 'h' * len(samples), *samples))

    print(f"WAVファイルを生成しました: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("使い方: python3 encode.py <01の文字列> [ノイズレベル(0〜5)]")
        sys.exit(1)

    bit_string = sys.argv[1]
    validate_bit_string(bit_string)

    noise_level = int(sys.argv[2]) if len(sys.argv) == 3 else NOISE_LEVEL
    validate_noise_level(noise_level)

    generate_tone(bit_string, noise_level=noise_level)