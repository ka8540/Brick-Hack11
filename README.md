# Lumeo

Lumeo is a real-time speech processing application that utilizes Speechmatics Flow for audio input and output. It provides a user-friendly interface for voice interactions, allowing users to perform various tasks through voice commands.

## Features

- Real-time speech recognition and transcription
- Audio playback of responses
- Integration with Speechmatics Flow for voice processing
- Support for custom tools (e.g., stock price queries, internet searches)
- Chainlit UI for interactive voice conversations

## Requirements

- Python 3.7 or higher
- Required Python packages (install via `pip`):
  - `chainlit`
  - `pyaudio`
  - `speechmatics-flow`
  - `python-dotenv`

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/lumeo.git
   cd lumeo
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables:
   - Create a `.env` file in the root directory and add your Speechmatics authentication token:
     ```
     SPEECHMATICS_AUTH_TOKEN=your_auth_token_here
     ```

## Usage

1. Start the application:
   ```bash
   chainlit run lumeo.py
   ```

2. Open your web browser and navigate to `http://localhost:8000`.

3. Press the `P` key to start talking. The application will listen for your voice input and process it in real-time.

4. The transcriptions will appear in the chat UI, and audio responses will be played back through your selected audio output device.

## Audio Configuration

Lumeo automatically detects and uses your connected headphones or earphones for audio playback. Ensure your audio devices are properly connected before starting the application.

## Contributing

Contributions are welcome! If you have suggestions or improvements, feel free to open an issue or submit a pull request.
