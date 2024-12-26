import os
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

def generate_speech_file(text, output_filename="output.wav"):
    # Load environment variables
    load_dotenv()
    
    # Get Azure credentials from environment variables
    azure_tts_key = os.getenv("AZURE_TTS_KEY")
    azure_region = os.getenv("AZURE_REGION")
    
    if not azure_tts_key or not azure_region:
        raise ValueError("Azure credentials not found in environment variables")
    
    try:
        # Configure Azure Speech SDK
        speech_config = speechsdk.SpeechConfig(
            subscription=azure_tts_key,
            region=azure_region
        )
        
        # Set voice and output format
        speech_config.speech_synthesis_voice_name = "en-US-AndrewMultilingualNeural"
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
        )
        
        # Configure audio output
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_filename)
        
        # Create speech synthesizer
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        # Synthesize text to file
        result = synthesizer.speak_text_async(text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"Speech synthesized successfully. Audio saved to: {output_filename}")
            return True
        else:
            print(f"Speech synthesis failed: {result.reason}")
            return False
            
    except Exception as e:
        print(f"Error generating speech: {e}")
        return False

def main():
    print("Enter the text you want to convert to speech (press Ctrl+C to exit):")
    try:
        while True:
            text = input("> ")
            if text.strip():
                generate_speech_file(text)
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
