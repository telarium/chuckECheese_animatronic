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

    def run(self):
        try:
            self.detect_wakeword()
            self.recorder.start()
            try:
                pcm_frames = []
                while True:
                    pcm = self.recorder.read()
                    result = self.rhino.process(pcm)
                    if result:
                        break
                    pcm_frames.extend(pcm)

                print("End of utterance detected.")
                inference = self.rhino.get_inference()

                if inference.is_understood:
                    print(f"Intent: {inference.intent}, Slots: {inference.slots}")
                else:
                    print("No intent detected. Converting audio to text...")
                    audio_data = struct.pack(f"<{len(pcm_frames)}h", *pcm_frames)
                    self.process_audio_with_google(audio_data)
            finally:
                self.recorder.stop()
        except Exception as e:
            print(f"Error in run method: {e}")

if __name__ == "__main__":
    try:
        pasquallyAI = VoiceControl()
        pasquallyAI.run()
    except Exception as e:
        print(f"VoiceControl failed to start: {e}")
