import wave
import numpy as np
import sys
import shutil
import random

# ノイズ生成関数

def add_noise(samples, sample_rate, noise_level):
    """
    サンプル配列にノイズを加える。
    noise_level: 0(無し)〜5(かなりひどい)
    """
    if noise_level == 0:
        return samples

    # ホワイトノイズ（強度を下げる）
    white_noise = np.random.normal(0, 500 * noise_level, samples.shape)

    # ハムノイズ（強度を下げる）
    hum_freq = 50 if random.random() < 0.5 else 60
    t = np.arange(len(samples)) / sample_rate
    hum_noise = 1000 * noise_level * np.sin(2 * np.pi * hum_freq * t)

    # パルスノイズ（発生数・振幅を抑える）
    pulse_noise = np.zeros_like(samples)
    if noise_level >= 3:
        num_pulses = int(len(samples) * 0.0005 * noise_level)  # 発生数半減
        for _ in range(num_pulses):
            idx = random.randint(0, len(samples) - 1)
            val = random.choice([-1, 1]) * 10000 * noise_level  # 振幅半減
            val = int(np.clip(val, -32768, 32767))
            pulse_noise[idx] = val

    noisy = samples + white_noise + hum_noise + pulse_noise
    noisy = np.clip(noisy, -32768, 32767)
    return noisy.astype(np.int16)


def main():
    if len(sys.argv) != 3:
        print("使い方: python3 noise.py <wavファイル> <ノイズレベル(0-5)>")
        sys.exit(1)

    wav_path = sys.argv[1]
    noise_level = int(sys.argv[2])
    if not (0 <= noise_level <= 5):
        print("ノイズレベルは0〜5で指定してください")
        sys.exit(1)

    # バックアップ作成
    backup_path = wav_path.rsplit('.', 1)[0] + "_orig.wav"
    shutil.copy2(wav_path, backup_path)
    print(f"バックアップ作成: {backup_path}")

    if noise_level == 0:
        print("ノイズレベル0のため、ファイルは変更しません。")
        return

    # WAV読み込み
    with wave.open(wav_path, 'rb') as wf:
        params = wf.getparams()
        frames = wf.readframes(wf.getnframes())
        samples = np.frombuffer(frames, dtype=np.int16)

    # ノイズ付加
    noisy_samples = add_noise(samples, params.framerate, noise_level)

    # WAV書き込み（上書き）
    with wave.open(wav_path, 'wb') as wf:
        wf.setparams(params)
        wf.writeframes(noisy_samples.tobytes())
    print(f"ノイズを加えたファイルを保存しました: {wav_path}")

if __name__ == "__main__":
    main()
