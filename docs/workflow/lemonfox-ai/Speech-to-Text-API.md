# Speech-to-Text API

*   **Powered by Whisper v3** - Convert audio to text quickly and reliably.
*   **Speaker diarization** - Automatically detect who is speaking.
*   **Just $0.50 per 3 hours of speech** - Lowest price on the market.

Use our audio-to-text API to build AI-powered features such as automatically generated subtitles, summaries of podcasts, or audio chats. Our API uses the latest Whisper large-v3 AI model to deliver accurate transcriptions with minimal latency and the most competitive pricing available. Transcribe 30 minutes of audio in under one minute. More than 100 languages are supported.

## API Usage

Our OpenAI compatible API makes it easy to switch. If you haven't already, you will need to [create an API key](#) to authenticate your requests.

*(Toggle: Use OpenAI library)*

### Javascript
```javascript
const body = new FormData();
body.append('file', 'https://output.lemonfox.ai/wikipedia_ai.mp3');
body.append('language', 'english');
body.append('response_format', 'json');

fetch('https://api.lemonfox.ai/v1/audio/transcriptions', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY'
  },
  body: body
})
.then(response => response.json()).then(data => {
  console.log(data['text']);
})
.catch(error => {
  console.error('Error:', error);
});
```

### Python
```python
# pip install requests
import requests

url = "https://api.lemonfox.ai/v1/audio/transcriptions"
headers = {
  "Authorization": "Bearer YOUR_API_KEY"
}
data = {
  "file": "https://output.lemonfox.ai/wikipedia_ai.mp3",
  "language": "english",
  "response_format": "json"
}

response = requests.post(url, headers=headers, data=data)
print(response.json())

# To upload a local file add the files parameter:
# files = {"file": open("/path/to/audio.mp3", "rb")}
# response = requests.post(url, headers=headers, files=files, data=data)
```

### Curl
```bash
curl https://api.lemonfox.ai/v1/audio/transcriptions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F file="https://output.lemonfox.ai/wikipedia_ai.mp3" \
  -F language="english" \
  -F response_format="json"

# To upload a local file use: -F file="@/path/to/audio.mp3"
```

## API Response

Choose between different response formats to get the transcript in the format that best suits your needs. `VTT` and `SRT` are file formats that include timestamps and can be used to display subtitles in video players.

**Example (srt):**
```srt
1
00:00:00,000 --> 00:00:06,420
Artificial intelligence is the intelligence of machines or software, as opposed to the intelligence of humans or animals.

2
00:00:07,040 --> 00:00:12,740
 It is also the field of study in computer science that develops and studies intelligent machines.
```

## API Parameters

The API `POST https://api.lemonfox.ai/v1/audio/transcriptions` takes the following parameters:

### **file**
*File object / URL, required*

The audio file to transcribe. You can either upload a file object to the API or provide a public URL to download the audio file. The upload size is limited to 100MB. When providing the audio file via URL the maximum file size is 1GB.

Supported audio and video file formats: `mp3`, `wav`, `flac`, `aac`, `opus`, `ogg`, `m4a`, `mp4`, `mpeg`, `mov`, `webm`, and more.

---

### **response_format**
*string, optional, default: json*

The format in which the generated transcript is returned. See example API responses above. Must be one of the following: `json`, `text`, `srt`, `verbose_json`, or `vtt`.

`vtt` and `srt` are file formats that can be used to add subtitles to videos. `verbose_json` contains additional information such as the duration of the audio and timestamps for each audio segment.

---

### **speaker_labels**
*boolean, optional*

Set this parameter to `true` to enable speaker diarization. This will add speaker labels to the transcript.

When using speaker diarization you may also add the parameters `min_speakers` and `max_speakers` to your API call to improve the accuracy of the speaker labels. The `min_speakers` and `max_speakers` parameters specify the minimum and maximum number of speakers in the audio file.

**Important:** Make sure to set the `response_format` parameter to `verbose_json` to be able to access the speaker labels. You can find an example response above.

**Note:** As OpenAI doesn't support speaker diarization, you can't use the `speaker_labels` parameter with the OpenAI Python or Javascript library.

---

### **prompt**
*string, optional*

A text to guide the transcript's style or continue a previous audio transcript. The prompt should be in the same language as the audio.

**Examples**
*   Prompts can be useful for fixing words or acronyms that the model might get wrong in the audio. For example, the following prompt improves the transcription of the words "NFT" and "DeFi": `The transcript is about blockchain technology, including terms like NFTs and DeFi.` . Alternately, the prompt can be a simple list of words: `NFT, DeFi, DAO, DApp`
*   Sometimes the model skips punctuation in the transcript. You can avoid this by using a simple prompt with punctuation: `Hello, welcome to the podcast.`
*   The model usually skips common filler words. If you want to keep the filler words in your transcript, use a prompt that includes them: `Umm, let's see, hmm... Okay, here's what I'm, like, thinking.`

---

### **language**
*string, optional*

The language of the input audio. If no language is provided we detect the language automatically. Supplying the input language can improve accuracy and latency.

**Supported languages:** `english`, `chinese`, `german`, `spanish`, `russian`, `korean`, `french`, `japanese`, `portuguese`, `turkish`, `polish`, `catalan`, `dutch`, `arabic`, `swedish`, `italian`, `indonesian`, `hindi`, `finnish`, `vietnamese`, `hebrew`, `ukrainian`, `greek`, `malay`, `czech`, `romanian`, `danish`, `hungarian`, `tamil`, `norwegian`, `thai`, `urdu`, `croatian`, `bulgarian`, `lithuanian`, `latin`, `maori`, `malayalam`, `welsh`, `slovak`, `telugu`, `persian`, `latvian`, `bengali`, `serbian`, `azerbaijani`, `slovenian`, `kannada`, `estonian`, `macedonian`, `breton`, `basque`, `icelandic`, `armenian`, `nepali`, `mongolian`, `bosnian`, `kazakh`, `albanian`, `swahili`, `galician`, `marathi`, `punjabi`, `sinhala`, `khmer`, `shona`, `yoruba`, `somali`, `afrikaans`, `occitan`, `georgian`, `belarusian`, `tajik`, `sindhi`, `gujarati`, `amharic`, `yiddish`, `lao`, `uzbek`, `faroese`, `haitian creole`, `pashto`, `turkmen`, `nynorsk`, `maltese`, `sanskrit`, `luxembourgish`, `myanmar`, `tibetan`, `tagalog`, `malagasy`, `assamese`, `tatar`, `hawaiian`, `lingala`, `hausa`, `bashkir`, `javanese`, `sundanese`, `cantonese`, `burmese`, `valencian`, `flemish`, `haitian`, `letzeburgesch`, `pushto`, `panjabi`, `moldavian`, `moldovan`, `sinhalese`, `castilian`, `mandarin`

---

### **callback_url**
*URL, optional*

A URL to which the API will send a POST request when the transcription is ready. The POST request will include the transcript in the specified response format.

The `callback_url` parameter is useful for long audio files that take a while to transcribe. Instead of waiting for the API to finish processing, you can provide a callback URL and the API will send the transcript to that URL when it's ready.

**Note:** As OpenAI doesn't support asynchronous requests, you can't use the `callback_url` parameter with the OpenAI Python or Javascript library.

---

### **translate**
*boolean, optional*

Set this parameter to `true` to translate the audio content to English.

---

### **timestamp_granularities[]**
*array, optional*

Enable word-level timestamps by adding `word` to the array (eg `timestamp_granularities[]=word`). By default only timestamps for each segment are added to the response. To use this feature, `response_format` must be set to `verbose_json`.

---

### **EU-based processing**

By default, API requests are processed by servers around the world. To enable EU-based processing use `eu-api.lemonfox.ai` instead of `api.lemonfox.ai` as the API endpoint. This ensures that your data is processed within the EU.

**Note:** EU-based processing incurs a 20% surcharge, i.e. the price for processing 3 hours of audio is $0.60 (instead of $0.50).