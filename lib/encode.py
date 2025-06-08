from lib.utils import validate_bit_string, validate_noise_level
import wave
import struct
import math
import random
import toml
import io
import argparse

# 設定を読み込む（Windows対応: encoding指定）
def load_config_toml():
    with open("config.toml", "r", encoding="utf-8") as f:
        return toml.load(io.StringIO(f.read()))

config = load_config_toml()
BITRATE = config["BITRATE"]  # 1秒間に何ビット詰め込むか
SAMPLE_RATE = config["SAMPLE_RATE"]
NOISE_LEVEL = config["NOISE_LEVEL"]


def generate_tone(bit_string, duration=None, sample_rate=SAMPLE_RATE, noise_level=NOISE_LEVEL, output_path="output.wav"):
    if duration is None:
        duration = 1.0 / BITRATE  # 1ビットあたりの秒数

    """
    0と1の文字列から、それぞれ440Hzと880Hzの音を生成し、ノイズを加えたWAVファイルに保存する。

    :param bit_string: 0と1の並んだ文字列
    :param duration: 各音の長さ（秒）
    :param sample_rate: サンプリングレート
    :param noise_level: ノイズの強さ（0〜5）
    :param output_path: 出力WAVファイルパス
    """
    # 周波数のマッピング（Bell 202 FSK: 0=1200Hz, 1=2200Hz）
    freq_map = {'0': 1200, '1': 2200}

    amplitude = 32767  # 最大振幅（16ビットPCM）
    samples = []

    for bit in bit_string:
        if bit not in freq_map:
            print(f"無効な文字: {bit}（スキップします）")
            continue
        frequency = freq_map[bit]
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            sample = amplitude * math.sin(2 * math.pi * frequency * t)
            max_noise = 100 + (noise_level * 100)  # ノイズ幅を100Hz単位で増加
            noise = random.uniform(-max_noise, max_noise)
            sample_with_noise = sample + noise
            sample_with_noise = max(-amplitude, min(amplitude, sample_with_noise))
            samples.append(int(sample_with_noise))

    with wave.open(output_path, 'w') as wav_file:
        wav_file.setnchannels(1)  # モノラル
        wav_file.setsampwidth(2)  # 16ビット
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack('<' + 'h' * len(samples), *samples))

    print(f"WAVファイルを生成しました: {output_path}")

def str_to_bitstring(s):
    return ''.join(f'{b:08b}' for b in s.encode('utf-8'))

def file_to_bitstring(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    return ''.join(f'{b:08b}' for b in data)

def main():
    parser = argparse.ArgumentParser(description="文字列またはファイルをFSK音声にエンコード")
    parser.add_argument('input', nargs='?', help='エンコードする文字列')
    parser.add_argument('--file', type=str, help='エンコードするファイルパス')
    parser.add_argument('noise_level', nargs='?', type=int, help='ノイズレベル(0〜5)')
    args = parser.parse_args()

    if args.file:
        bit_string = file_to_bitstring(args.file)
        print(f"[INFO] ファイル {args.file} をビット列に変換してエンコードします")
    elif args.input:
        bit_string = str_to_bitstring(args.input)
    else:
        print("使い方: python3 encode.py <文字列> [ノイズレベル] または --file <ファイルパス> [ノイズレベル]")
        return

    validate_bit_string(bit_string)
    noise_level = args.noise_level if args.noise_level is not None else NOISE_LEVEL
    validate_noise_level(noise_level)
    generate_tone(bit_string, noise_level=noise_level)

if __name__ == "__main__":
    main()
