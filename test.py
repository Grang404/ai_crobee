import pyttsx3
import tempfile
import os


def generate_tts_audio(text):
    """Generate TTS audio using pyttsx3 and return WAV file"""
    try:
        # Initialize pyttsx3 engine
        engine = pyttsx3.init()

        # Create a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            wav_path = temp_wav.name
            print(f"Temporary WAV path: {wav_path}")

            # Generate the WAV file using pyttsx3
            engine.save_to_file(text, wav_path)
            engine.runAndWait()

        # Return the path to the generated WAV file
        return wav_path

    except Exception as e:
        print(f"Error generating TTS audio: {e}")
        return None


if __name__ == "__main__":
    text = "Hello, this is a test of the TTS system!"
    wav_file = generate_tts_audio(text)

    if wav_file:
        print(f"WAV file generated successfully at: {wav_file}")
    else:
        print("Failed to generate TTS audio.")
