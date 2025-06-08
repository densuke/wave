import wave
import numpy as np
import sys
import shutil
import random

# ノイズ生成関数

def add_noise(samples, sample_rate, noise_level):
    """
    サンプル配列にノイズを加える。
    noise_level: 0(無し)〜8(8=徹底的に酷い)
    """
    if noise_level == 0:
        return samples

    # ホワイトノイズ
    if noise_level == 8:
        white_noise = np.random.normal(0, 25000, samples.shape)
    elif noise_level == 7:
        white_noise = np.random.normal(0, 12000, samples.shape)
    else:
        white_noise = np.random.normal(0, 200 * noise_level, samples.shape)

    # ハムノイズ
    hum_freq = 50 if random.random() < 0.5 else 60
    t = np.arange(len(samples)) / sample_rate
    if noise_level == 8:
        hum_noise = 20000 * np.sin(2 * np.pi * hum_freq * t)
    elif noise_level == 7:
        hum_noise = 10000 * np.sin(2 * np.pi * hum_freq * t)
    else:
        hum_noise = 400 * noise_level * np.sin(2 * np.pi * hum_freq * t)

    # パルスノイズ
    pulse_noise = np.zeros_like(samples)
    if noise_level >= 3:
        if noise_level == 8:
            num_pulses = int(len(samples) * 0.01)
            amp = 32000
        elif noise_level == 7:
            num_pulses = int(len(samples) * 0.005)
            amp = 20000
        else:
            num_pulses = int(len(samples) * 0.0003 * noise_level * (1 + (noise_level-5)*0.5 if noise_level > 5 else 1))
            amp = 6000 * noise_level * (2 if noise_level >= 7 else 1)
        for _ in range(num_pulses):
            idx = random.randint(0, len(samples) - 1)
            val = random.choice([-1, 1]) * amp
            val = int(np.clip(val, -32768, 32767))
            pulse_noise[idx] = val

    # バンドノイズ（FSK信号帯域）
    band_noise = np.zeros_like(samples, dtype=np.float64)
    if noise_level == 8:
        for freq in range(200, 401, 20):
            band_noise += 12000 * np.sin(2 * np.pi * freq * t + np.random.rand()*2*np.pi)
    elif noise_level == 7:
        for freq in range(200, 401, 40):
            band_noise += 6000 * np.sin(2 * np.pi * freq * t + np.random.rand()*2*np.pi)

    if noise_level >= 7:
        noisy = samples + white_noise + hum_noise + pulse_noise + band_noise
    else:
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
