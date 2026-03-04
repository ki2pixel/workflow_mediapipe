DeepInfra API | OpenAI Speech-to-Text | HTTP/cURL | Python | JavaScript

---

## OpenAI Speech-to-Text HTTP/cURL API

You can POST to our OpenAI Transcriptions and Translations compatible endpoint.

# Create transcription

For a given audio file and model, the endpoint will return the transcription object or a verbose transcription object.

## Request body

*   **file (Required):** The audio file object to transcribe. Supported formats are `flac`, `mp3`, `mp4`, `mpeg`, `mpga`, `m4a`, `ogg`, `wav`, and `webm`.
*   **model (Required):** ID of the model to use. Only `openai/whisper-large-v3` for this case. For other models, refer to [models/automatic-speech-recognition](models/automatic-speech-recognition).
*   **language (Optional):** The language of the input audio. Supplying the input language in ISO-639-1 format can improve accuracy and latency.
*   **prompt (Optional):** An optional text prompt to guide the model's style or continue a previous audio segment. The prompt should match the audio language.
*   **response_format (Optional):** The format of the output. Options include: `json` (default), `text`, `srt`, `verbose_json`, `vtt`.
*   **temperature (Optional):** Controls the sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 make it more focused and deterministic. If set to 0, the model will adjust automatically to increase temperature as needed.
*   **timestamp_granularities[] (Optional):** Specifies the timestamp granularity for transcription. Requires `response_format` to be set to `verbose_json`. Options: `word` - generates timestamps for individual words, `segment` - generates timestamps for segments. Note: There is no additional latency for segment timestamps, but generating word timestamps incurs additional latency.

## Response body

The transcription object or a verbose transcription object.

## Basic request

```bash
curl "https://api.deepinfra.com/v1/openai/audio/transcriptions" \
-H "Content-Type: multipart/form-data" \
-H "Authorization: Bearer 1VpO0iyxf87XUyc34WbQMLt9SKf6n6DM" \
-F file="@/path/to/file/audio.mp3" \
-F model="openai/whisper-large-v3"
```

## Word timestamp request

```bash
curl "https://api.deepinfra.com/v1/openai/audio/transcriptions" \
-H "Content-Type: multipart/form-data" \
-H "Authorization: Bearer 1VpO0iyxf87XUyc34WbQMLt9SKf6n6DM" \
-F file="@/path/to/file/audio.mp3" \
-F model="openai/whisper-large-v3" \
-F response_format="verbose_json" \
-F "timestamp_granularities[]=word"
```

## Segment timestamp request

```bash
curl "https://api.deepinfra.com/v1/openai/audio/transcriptions" \
-H "Content-Type: multipart/form-data" \
-H "Authorization: Bearer 1VpO0iyxf87XUyc34WbQMLt9SKf6n6DM" \
-F file="@/path/to/file/audio.mp3" \
-F model="openai/whisper-large-v3" \
-F response_format="verbose_json" \
-F "timestamp_granularities[]=segment"
```

# Create translation

For a given audio file and model, the endpoint will return the translated text to English.

## Request body

*   **file (Required):** The audio file object to translate. Supported formats are `flac`, `mp3`, `mp4`, `mpeg`, `mpga`, `m4a`, `ogg`, `wav`, and `webm`.
*   **model (Required):** ID of the model to use. Only `openai/whisper-large-v3` for this case. For other models, refer to [models/automatic-speech-recognition](models/automatic-speech-recognition).
*   **prompt (Optional):** An optional text to guide the model's style or continue a previous audio segment. The prompt should be in English.
*   **response_format (Optional):** The format of the output. Options include: `json` (default), `text`, `srt`, `verbose_json`, `vtt`.
*   **temperature (Optional):** The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. If set to 0, the model will use log probability to automatically increase the temperature until certain thresholds are hit.

## Response body

The translated text to English.

## Basic request

```bash
curl "https://api.deepinfra.com/v1/openai/audio/translations" \
-H "Content-Type: multipart/form-data" \
-H "Authorization: Bearer 1VpO0iyxf87XUyc34WbQMLt9SKf6n6DM" \
-F file="@/path/to/file/german.m4a" \
-F model="openai/whisper-large-v3"

{
    "text": "Hello, my name is Wolfgang and I come from Germany. Where are you heading today?"
}
```

## Input fields

# model string
Model name to use

# file string
audio file to transcribe

# language string
The language of the input audio

# prompt string
An optional text to guide the model's style or continue a previous audio segment.

# response_format string
The format of the output
Default value: `"json"`
Allowed values: `json`, `verbose_json`, `text`, `srt`, `vtt`

# temperature number
The sampling temperature, between 0 and 1. Higher values produce more creative results.
Default value: `0`
Range: `0 ≤ temperature ≤ 1`

# timestamp_granularities array
An array specifying the granularity of timestamps to include in the transcription. Possible values are 'segment', 'word'.

## Input Schema

This is the detailed description of the input parameters in JSON Schema format

```json
{
  "required": [
    "model",
    "file"
  ],
  "title": "OpenAISpeechToTextTranscriptionIn",
  "type": "object",
  "properties": {
    "model": {
      "description": "Model name to use",
      "required": true,
      "title": "Model",
      "type": "string",
      "example": "openai/whisper-large-v3-turbo"
    },
    "file": {
      "description": "audio file to transcribe",
      "format": "binary",
      "is_audio": true,
      "required": true,
      "title": "File",
      "type": "string"
    },
    "language": {
      "description": "The language of the input audio",
      "title": "Language",
      "type": "string",
      "example": "en"
    },
    "prompt": {
      "description": "An optional text to guide the model's style or continue a previous audio segment.",
      "title": "Prompt",
      "type": "string",
      "example": "The audio is a conversation between two people"
    },
    "response_format": {
      "default": "json",
      "description": "The format of the output",
      "enum": [
        "json",
        "verbose_json",
        "text",
        "srt",
        "vtt"
      ],
      "title": "Response Format",
      "type": "string",
      "example": "json"
    },
    "temperature": {
      "default": 0,
      "description": "The sampling temperature, between 0 and 1. Higher values produce more creative results.",
      "maximum": 1,
      "minimum": 0,
      "title": "Temperature",
      "type": "number",
      "example": 0
    },
    "timestamp_granularities": {
      "description": "An array specifying the granularity of timestamps to include in the transcription. Possible values are 'segment', 'word'.",
      "items": {
        "enum": [
          "segment",
          "word"
        ],
        "type": "string"
      },
      "title": "Timestamp Granularities",
      "type": "array",
      "example": [
        "segment"
      ]
    }
  }
}
```

## Output Schema

This is the detailed description of the output parameters in JSON Schema format

```json
{
  "definitions": {
    "OpenAISpeechToTextSegment": {
      "properties": {
        "id": {
          "description": "The id of the segment",
          "title": "Id",
          "type": "integer"
        },
        "seek": {
          "description": "The seek of the segment in milliseconds",
          "title": "Seek",
          "type": "integer"
        },
        "start": {
          "description": "The start time of the segment in seconds",
          "title": "Start",
          "type": "number"
        },
        "end": {
          "description": "The end time of the segment in seconds",
          "title": "End",
          "type": "number"
        },
        "text": {
          "description": "The text of the segment",
          "title": "Text",
          "type": "string"
        },
        "tokens": {
          "description": "The tokens of the segment",
          "items": {
            "type": "integer"
          },
          "title": "Tokens",
          "type": "array"
        },
        "temperature": {
          "description": "The temperature of the segment",
          "title": "Temperature",
          "type": "number"
        },
        "avg_logprob": {
          "description": "The average log probability of the segment",
          "title": "Avg Logprob",
          "type": "number"
        },
        "compression_ratio": {
          "description": "The compression ratio of the segment",
          "title": "Compression Ratio",
          "type": "number"
        },
        "no_speech_prob": {
          "description": "The probability of no speech in the segment",
          "title": "No Speech Prob",
          "type": "number"
        }
      },
      "title": "OpenAISpeechToTextSegment",
      "type": "object"
    },
    "OpenAISpeechToTextWord": {
      "properties": {
        "word": {
          "description": "The word in the segment",
          "title": "Word",
          "type": "string"
        },
        "start": {
          "description": "The start time of the word in seconds",
          "title": "Start",
          "type": "number"
        },
        "end": {
          "description": "The end time of the word in seconds",
          "title": "End",
          "type": "number"
        }
      },
      "title": "OpenAISpeechToTextWord",
      "type": "object"
    }
  },
  "required": [
    "text"
  ],
  "title": "OpenAISpeechToTextOut",
  "type": "object",
  "properties": {
    "text": {
      "description": "The transcribed/translated text from the audio input.",
      "title": "Text",
      "type": "string"
    },
    "task": {
      "description": "The task performed, e.g., 'transcribe'.",
      "title": "Task",
      "type": "string"
    },
    "language": {
      "description": "The language of the transcription.",
      "title": "Language",
      "type": "string"
    },
    "duration": {
      "description": "The duration of the audio in seconds.",
      "title": "Duration",
      "type": "number"
    },
    "words": {
      "description": "List of words with their start and end timestamps.",
      "items": {
        "$ref": "#/definitions/OpenAISpeechToTextWord"
      },
      "title": "Words",
      "type": "array"
    },
    "segments": {
      "description": "List of segments with detailed information.",
      "items": {
        "$ref": "#/definitions/OpenAISpeechToTextSegment"
      },
      "title": "Segments",
      "type": "array"
    }
  }
}