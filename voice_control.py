#!/usr/bin/env python3

import pvporcupine
import pvrhino
from pvrecorder import PvRecorder
import openai
import os
import subprocess
import configparser
import struct
from google.cloud import speech

import audioop
import webrtcvad
import time

class VoiceControl:
    def __init__(self, config_file="VoiceControlConfig.txt"):
        self.config = self.load_config(config_file)

        self.pv_access_key = self.config["PicoVoice"]["AccessKey"]
        self.wakeword_path = self.config["PicoVoice"]["WakewordPath"]
        self.rhino_context_path = self.config["PicoVoice"]["RhinoContextPath"]
        self.google_cloud_key_path = self.config["SpeechToText"]["GoogleCloudKeyPath"]
        self.openai_api_key = self.config["ChatGPT"]["OpenAIKey"]
        self.chatgpt_context = self.config["ChatGPT"]["ChatGPTContext"]

        self.initialize_recorder()
        self.initialize_porcupine()
        self.initialize_rhino()

        # Create the VAD object (mode=3 is most aggressive. Try mode=1 or 0 if it's too strict).
        self.vad = webrtcvad.Vad(mode=3)

        # Create an OpenAI client (replace with correct usage in your environment if needed)
        self.openai_client = openai.Client(api_key=self.openai_api_key)

    def load_config(self, config_file):
        config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_file)
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        config = configparser.ConfigParser()
        config.read(config_path)
        return config

    def initialize_recorder(self):
        device_index = self.get_audio_device_index()
        if device_index is None:
            raise RuntimeError("No suitable audio device found.")
        try:
            # NOTE: If you prefer 30ms frames, set frame_length=480 to align neatly with VAD.
            self.recorder = PvRecorder(device_index=device_index, frame_length=512)
        except Exception as e:
            print(f"Failed to initialize PvRecorder: {e}")
            raise

    def initialize_porcupine(self):
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.pv_access_key,
                keyword_paths=[self.wakeword_path],
            )
        except Exception as e:
            print(f"Failed to initialize Porcupine: {e}")
            raise

    def initialize_rhino(self):
        try:
            self.rhino = pvrhino.create(
                access_key=self.pv_access_key,
                context_path=self.rhino_context_path,
                # endpoint_duration_sec=1.5,  # If you still want to tweak this, but not crucial now
            )
        except Exception as e:
            print(f"Failed to initialize Rhino: {e}")
            raise

    def get_audio_device_index(self, device_name=None):
        try:
            result = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
            output = result.stdout

            import re
            pattern = r"card (\d+):.*device (\d+):.*\[(.*)\]"
            matches = re.findall(pattern, output)

            if not matches:
                print("No audio capture devices found!")
                return None

            if device_name:
                for card, device, name in matches:
                    if device_name.lower() in name.lower():
                        print(f"Using audio device: {name} (card {card}, device {device})")
                        return int(card)

            card, device, name = matches[0]
            print(f"Defaulting to first audio device: {name} (card {card}, device {device})")
            return int(card)
        except Exception as e:
            print(f"Error while detecting audio devices: {e}")
            return None

    def send_to_chatgpt(self, text):
        print(f"Sending text to ChatGPT: {text}")
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.chatgpt_context},
                    {"role": "user", "content": text},
                ],
            )
            chat_response = response.choices[0].message.content
            print(f"ChatGPT Response: {chat_response}")
            return chat_response
        except Exception as e:
            print(f"Failed to get response from ChatGPT: {e}")
            return None

    def process_audio_with_google(self, audio_data):
        try:
            client = speech.SpeechClient.from_service_account_file(self.google_cloud_key_path)

            audio = speech.RecognitionAudio(content=audio_data)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-US",
            )

            response = client.recognize(config=config, audio=audio)
            if response.results:
                transcribed_text = response.results[0].alternatives[0].transcript
                print(f"Transcribed text: {transcribed_text}")
                return self.send_to_chatgpt(transcribed_text)
            else:
                print("No speech recognized.")
        except Exception as e:
            print(f"Failed to process audio with Google: {e}")

    def detect_wakeword(self):
        """Blocks until the wake word is detected."""
        print("Listening for wakeword...")
        self.recorder.start()
        try:
            while True:
                pcm = self.recorder.read()
                keyword_index = self.porcupine.process(pcm)
                if keyword_index >= 0:
                    print("Wakeword detected!")
                    break
        finally:
            self.recorder.stop()

    def wait_for_speech(self, max_leading_silence_seconds=3):
        """
        After the wakeword is detected, wait for the user to start speaking.
        If no speech is detected within max_leading_silence_seconds, return False.
        """
        print("Waiting for user to begin speaking...")
        self.recorder.start()
        start_time = time.time()

        try:
            while (time.time() - start_time) < max_leading_silence_seconds:
                pcm_512 = self.recorder.read()
                # Break the 512-sample chunk into 160-sample sub-chunks
                idx = 0
                subchunk_size = 160
                while idx + subchunk_size <= len(pcm_512):
                    subchunk = pcm_512[idx : idx + subchunk_size]
                    idx += subchunk_size

                    pcm_bytes = struct.pack(f"<{len(subchunk)}h", *subchunk)
                    is_speech = self.vad.is_speech(pcm_bytes, sample_rate=16000)
                    if is_speech:
                        print("Speech detected!")
                        return True
            # Timed out
            print("No speech detected in leading silence window. Timing out.")
            return False
        finally:
            self.recorder.stop()

    def record_utterance_vad(self, max_silence_frames=40):
        """
        Once speech has started, record until trailing silence is detected.
        max_silence_frames=40 => ~400ms if sub-chunk=10ms each.
        """
        print("Recording user utterance (waiting for trailing silence)...")

        full_audio_buffer = []
        silent_frame_count = 0

        self.recorder.start()
        try:
            while True:
                pcm_512 = self.recorder.read()
                full_audio_buffer.extend(pcm_512)

                # Break 512-sample chunk into 160-sample sub-chunks
                idx = 0
                subchunk_size = 160
                while idx + subchunk_size <= len(pcm_512):
                    subchunk = pcm_512[idx : idx + subchunk_size]
                    idx += subchunk_size

                    pcm_bytes = struct.pack(f"<{len(subchunk)}h", *subchunk)
                    is_speech = self.vad.is_speech(pcm_bytes, sample_rate=16000)

                    if not is_speech:
                        silent_frame_count += 1
                    else:
                        silent_frame_count = 0

                # If we've detected enough consecutive silent frames, user is done
                if silent_frame_count >= max_silence_frames:
                    print("Trailing silence detected — user finished speaking.")
                    break

        finally:
            self.recorder.stop()

        return full_audio_buffer

    def run_rhino_offline(self, audio_buffer):
        """
        Feed the entire audio buffer to Rhino in one shot (offline).
        Returns Rhino's final inference.
        """
        # Reset Rhino (clear any previous state)
        self.rhino.reset()

        frame_length = self.rhino.frame_length  # typically 512
        index = 0
        while index + frame_length <= len(audio_buffer):
            frame = audio_buffer[index : index + frame_length]
            _ = self.rhino.process(frame)
            index += frame_length

        # After feeding all frames, get final inference
        inference = self.rhino.get_inference()
        return inference

    def run(self):
        """
        Main flow:
          1) Detect wakeword
          2) Wait for user to begin speaking (leading silence)
          3) Record entire utterance until trailing silence
          4) Run Rhino offline:
             - If recognized, handle the intent
             - Else send audio to Google STT -> ChatGPT
        """
        try:
            # 1) Detect wakeword
            self.detect_wakeword()

            # 2) Wait for the user to begin speaking
            if not self.wait_for_speech(max_leading_silence_seconds=3):
                print("No user command after wakeword; going idle...")
                return

            # 3) Record the utterance with trailing silence detection
            audio_buffer = self.record_utterance_vad(max_silence_frames=40)

            # 4) Run Rhino offline
            inference = self.run_rhino_offline(audio_buffer)
            if inference.is_understood:
                print("Rhino recognized an intent!")
                print(f"Intent: {inference.intent}")
                print(f"Slots: {inference.slots}")
            else:
                print("No intent recognized. Sending audio to ChatGPT (via Google STT).")
                audio_data = struct.pack(f"<{len(audio_buffer)}h", *audio_buffer)
                self.process_audio_with_google(audio_data)

        except Exception as e:
            print(f"Error in run method: {e}")


if __name__ == "__main__":
    try:
        pasquallyAI = VoiceControl()
        pasquallyAI.run()
    except Exception as e:
        print(f"VoiceControl failed to start: {e}")
