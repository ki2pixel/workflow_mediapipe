Deepinfra API | OpenAI Speech-to-Text | HTTP/cURL deepctl JavaScript

# HTTP/cURL API

You can use cURL or any other http client to run inferences:

```bash
curl -X POST \
  -H "Authorization: bearer 1Vp00iyxf87XUyc34wbQMLt95Kf6n6DM" \
  -F audio=@my_voice.mp3 \
  'https://api.deepinfra.com/v1/inference/openai/wisper-large-v3'
```
copy

which will give you back something similar to:

```json
{
  "text": "",
  "segments": [
    {
      "end": 1.0,
      "id": 0,
      "start": 0.0,
      "text": "Hello"
    },
    {
      "end": 5.0,
      "id": 1,
      "start": 4.0,
      "text": "World"
    }
  ],
  "language": "en",
  "input_length_ms": 0,
  "words": [
    {
      "end": 1.0,
      "start": 0.0,
      "text": "Hello"
    },
    {
      "end": 5.0,
      "start": 4.0,
      "text": "World"
    }
  ],
  "duration": 0.0,
  "request_id": null,
  "inference_status": {
    "status": "unknown",
    "run_time_ms": 0,
    "cost": 0.0,
    "tokens_generated": 0,
    "tokens_input": 0,
    "output_length": 0
  }
}
```
copy

# Input fields

# audio string
audio to transcribe

# task string
task to perform

Default value: `"transcribe"`

Allowed values: `transcribe` `translate`

# initial_prompt string
optional text to provide as a prompt for the first window.

# temperature number
temperature to use for sampling

Default value: `0`

# language string
language that the audio is in; uses detected language if None; use two letter language code (ISO 639-1) (e.g. en, de, ja)

Allowed values: af am ar as az ba bg bn bo br bs ca cs cy da de el en es et eu fa fi fo fr gl gu ha hi hr ht hu hy id is it ja jw ka kk km kn ko la lb ln lo lt lv mg mi mk ml mn mr ms mt my ne n1 nn no oc pa pl ps pt ro ru sa sd si sk sl sn so sq sr su sv sw ta te tg th tk tl tr tt uk ur uz vi yi yo yue zh

# chunk_level string
chunk level, either 'segment' or 'word'

Default value: `"segment"`

Allowed values: segment word

# chunk_length_s integer
chunk length in seconds to split audio

Default value: `30`

Range: `1 <= chunk_length_s <= 30`

# webhook file
The webhook to call when inference is done, by default you will get the output in the response of your inference request

# Output Schema

This is the detailed description of the output parameters in JSON Schema format

```json
{
  "required": [
    "audio"
  ],
  "title": "AutomaticSpeechRecognitionIn",
  "type": "object",
  "properties": {
    "audio": {
      "description": "Audio to transcribe",
      "format": "binary",
      "is_audio": true,
      "required": true,
      "title": "Audio",
      "type": "string"
    },
    "task": {
      "default": "transcribe",
      "description": "Task to perform",
      "enum": [
        "transcribe",
        "translate"
      ],
      "title": "Task",
      "type": "string",
      "example": "transcribe"
    },
    "initial_prompt": {
      "description": "Optional text to provide as a prompt for the first window.",
      "title": "Initial Prompt",
      "type": "string"
    },
    "temperature": {
      "default": 0,
      "description": "Temperature to use for sampling",
      "title": "Temperature",
      "type": "number",
      "example": 0
    },
    "language": {
      "description": "Language that the audio is in; uses detected language if None; use two letter language code (ISO 639-1) (e.g. en, de, ja)",
      "enum": [
        "af",
        "am",
        "ar",
        "as",
        "az",
        "ba",
        "be",
        "bg",
        "bn",
        "bo",
        "br",
        "bs",
        "ca",
        "cs",
        "cy",
        "da",
        "de",
        "el",
        "en",
        "es",
        "et",
        "eu",
        "fa",
        "fi",
        "fo",
        "fr",
        "gl",
        "gu",
        "ha",
        "hi",
        "hr",
        "ht",
        "hu",
        "hy",
        "id",
        "is",
        "it",
        "ja",
        "jw",
        "ka",
        "kk",
        "km",
        "kn",
        "ko",
        "la",
        "lb",
        "ln",
        "lo",
        "lt",
        "lv",
        "mg",
        "mi",
        "mk",
        "ml",
        "mn",
        "mr",
        "ms",
        "mt",
        "my",
        "ne",
        "n1",
        "nn",
        "no",
        "oc",
        "pa",
        "pl",
        "ps",
        "pt",
        "ro",
        "ru",
        "sa",
        "sd",
        "si",
        "sk",
        "sl",
        "sn",
        "so",
        "sq",
        "sr",
        "su",
        "sv",
        "sw",
        "ta",
        "te",
        "tg",
        "th",
        "tk",
        "tl",
        "tr",
        "tt",
        "uk",
        "ur",
        "uz",
        "vi",
        "yi",
        "yo",
        "yue",
        "zh"
      ],
      "title": "Language",
      "type": "string"
    },
    "chunk_level": {
      "default": "segment",
      "description": "Chunk level, either 'segment' or 'word'",
      "enum": [
        "segment",
        "word"
      ],
      "title": "Chunk Level",
      "type": "string",
      "example": "segment"
    },
    "chunk_length_s": {
      "default": 30,
      "description": "Chunk length in seconds to split audio",
      "maximum": 30,
      "minimum": 1,
      "title": "Chunk Length S",
      "type": "integer",
      "example": 30
    },
    "webhook": {
      "description": "The webhook to call when inference is done, by default you will get the output in the response of your inference request",
      "format": "uri",
      "is_base_field": true,
      "maxLength": 2083,
      "minLength": 1,
      "title": "Webhook",
      "type": "string"
    }
  }
}
```

# Output Schema

This is the detailed description of the output parameters in JSON Schema format

```json
{
  "definitions": {
    "InferenceReplyStatus": {
      "properties": {
        "status": {
          "choices": [
            "unknown",
            "queued",
            "running",
            "succeeded",
            "failed"
          ],
          "default": "succeeded",
          "description": "Inference status",
          "title": "Status",
          "type": "string"
        },
        "runtime_ms": {
          "default": 0,
          "description": "Runtime in milliseconds",
          "title": "Runtime Ms",
          "type": "integer"
        },
        "cost": {
          "description": "Estimated cost billed for the request in USD",
          "title": "Cost",
          "type": "number"
        },
        "tokens_generated": {
          "description": "Number of tokens generated",
          "title": "Tokens Generated",
          "type": "integer"
        },
        "tokens_input": {
          "description": "Number of input tokens",
          "title": "Tokens Input",
          "type": "integer"
        },
        "output_length": {
          "description": "Length of the output in seconds",
          "title": "Output Length",
          "type": "integer"
        }
      },
      "title": "InferenceReplyStatus",
      "type": "object"
    },
    "segment": {
      "properties": {
        "id": {
          "description": "Segment ID",
          "title": "Id",
          "type": "integer"
        },
        "seek": {
          "description": "",
          "title": "Seek",
          "type": "integer"
        },
        "start": {
          "description": "Start location in input in seconds from start",
          "title": "Start",
          "type": "number"
        },
        "end": {
          "description": "End location in input in seconds from start",
          "title": "End",
          "type": "number"
        },
        "text": {
          "description": "A piece of the decoded text",
          "examples": [
            "Hello world"
          ],
          "title": "Text",
          "type": "string"
        },
        "tokens": {
          "description": "A list of tokens in the segment",
          "items": {
            "type": "integer"
          },
          "title": "Tokens",
          "type": "array"
        },
        "temperature": {
          "description": "Temperature of the segment",
          "title": "Temperature",
          "type": "number"
        },
        "avg_logprob": {
          "description": "",
          "title": "Avg Logprob",
          "type": "number"
        },
        "compression_ratio": {
          "description": "Compression ratio of the segment",
          "title": "Compression Ratio",
          "type": "number"
        },
        "no_speech_prob": {
          "description": "Probability of no speech in the segment",
          "title": "No Speech Prob",
          "type": "number"
        },
        "confidence": {
          "description": "Confidence of the segment (Only in whisper-timestamped model)",
          "title": "Confidence",
          "type": "number"
        }
      },
      "title": "Segment",
      "type": "object"
    },
    "word": {
      "properties": {
        "word": {
          "description": "Word text",
          "title": "Word",
          "type": "string"
        },
        "start": {
          "description": "Start timestamp",
          "title": "Start",
          "type": "number"
        },
        "end": {
          "description": "End timestamp",
          "title": "End",
          "type": "number"
        },
        "text": {
          "description": "A piece of the decoded text",
          "examples": [
            "Hello",
            "World"
          ],
          "title": "Text",
          "type": "string"
        },
        "tokens": {
          "description": "A list of tokens in the segment (Only in whisper-timestamped model)",
          "items": {
            "$ref": "#/definitions/token"
          },
          "title": "Tokens",
          "type": "array"
        },
        "temperature": {
          "description": "Temperature of the segment",
          "title": "Temperature",
          "type": "number"
        },
        "avg_logprob": {
          "description": "",
          "title": "Avg Logprob",
          "type": "number"
        },
        "compression_ratio": {
          "description": "Compression ratio of the segment",
          "title": "Compression Ratio",
          "type": "number"
        },
        "no_speech_prob": {
          "description": "Probability of no speech in the segment",
          "title": "No Speech Prob",
          "type": "number"
        },
        "confidence": {
          "description": "Confidence of the segment (Only in whisper-timestamped model)",
          "title": "Confidence",
          "type": "number"
        }
      },
      "title": "Word",
      "type": "object"
    },
    "token": {
      "properties": {
        "end": {
          "description": "End timestamp",
          "title": "End",
          "type": "number"
        },
        "start": {
          "description": "Start timestamp",
          "title": "Start",
          "type": "number"
        },
        "text": {
          "description": "A piece of the decoded text",
          "examples": [
            "Hello",
            "World"
          ],
          "title": "Text",
          "type": "string"
        },
        "tokens": {
          "description": "A list of tokens in the segment (Only in whisper-timestamped model)",
          "items": {
            "$ref": "#/definitions/token"
          },
          "title": "Tokens",
          "type": "array"
        },
        "temperature": {
          "description": "Temperature of the segment",
          "title": "Temperature",
          "type": "number"
        },
        "avg_logprob": {
          "description": "",
          "title": "Avg Logprob",
          "type": "number"
        },
        "compression_ratio": {
          "description": "Compression ratio of the segment",
          "title": "Compression Ratio",
          "type": "number"
        },
        "no_speech_prob": {
          "description": "Probability of no speech in the segment",
          "title": "No Speech Prob",
          "type": "number"
        },
        "confidence": {
          "description": "Confidence of the segment (Only in whisper-timestamped model)",
          "title": "Confidence",
          "type": "number"
        }
      },
      "title": "Token",
      "type": "object"
    }
  },
  "title": "AutomaticSpeechRecognitionOut",
  "type": "object",
  "properties": {
    "text": {
      "description": "Transcription",
      "title": "Text",
      "type": "string",
      "example": ""
    },
    "segments": {
      "description": "A list of timestamped pieces",
      "items": {
        "$ref": "#/definitions/segment"
      },
      "type": "array",
      "title": "Segments",
      "example": [
        {
          "end": 1,
          "id": 0,
          "start": 0,
          "text": "Hello"
        },
        {
          "end": 5,
          "id": 1,
          "start": 4,
          "text": "World"
        }
      ]
    },
    "language": {
      "description": "Language code of audio",
      "title": "Language",
      "type": "string",
      "example": "en"
    },
    "input_length_ms": {
      "default": 0,
      "description": "Input Length Ms",
      "title": "Input Length Ms",
      "type": "integer"
    },
    "words": {
      "description": "A list of timestamped words in a segment (Only in whisper-timestamped model)",
      "items": {
        "$ref": "#/definitions/word"
      },
      "type": "array",
      "title": "Words",
      "example": [
        {
          "end": 1,
          "start": 0,
          "text": "Hello"
        },
        {
          "end": 5,
          "start": 4,
          "text": "World"
        }
      ]
    },
    "duration": {
      "description": "Duration of the audio in seconds",
      "title": "Duration",
      "type": "number"
    },
    "request_id": {
      "description": "Request ID",
      "is_base_field": true,
      "title": "Request Id",
      "type": "string"
    },
    "inference_status": {
      "$ref": "#/definitions/InferenceReplyStatus",
      "description": "Object containing the