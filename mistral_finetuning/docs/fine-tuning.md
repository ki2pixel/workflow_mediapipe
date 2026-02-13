# Mistral AI Fine-Tuning API

API documentation for fine-tuning Mistral models with comprehensive endpoint specifications.

## Table of Contents

- [GET /v1/fine_tuning/jobs](#get-v1fine_tuningjobs)
- [POST /v1/fine_tuning/jobs](#post-v1fine_tuningjobs)
- [GET /v1/fine_tuning/jobs/{job_id}](#get-v1fine_tuningjobsjob_id)
- [POST /v1/fine_tuning/jobs/{job_id}/cancel](#post-v1fine_tuningjobsjob_idcancel)
- [POST /v1/fine_tuning/jobs/{job_id}/start](#post-v1fine_tuningjobsjob_idstart)

---

## GET /v1/fine_tuning/jobs

Retrieve a list of fine-tuning jobs for your organization and user.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 0 | Pagination page number |
| page_size | integer | 100 | Number of items per page |
| created_by_me | boolean | false | Filter jobs created by current user |

### Response

Returns a list object containing fine-tuning job details.

### Code Examples

#### JavaScript

```javascript
import { Mistral } from "@mistralai/mistralai";

const mistral = new Mistral({
  apiKey: "MISTRAL_API_KEY",
});

async function listJobs() {
  const result = await mistral.fineTuning.jobs.list({
    page: 0,
    page_size: 100,
    created_by_me: false
  });
  
  console.log(result);
}

listJobs();
```

#### Python

```python
from mistralai import Mistral
import os

with Mistral(
    api_key=os.getenv("MISTRAL_API_KEY", ""),
) as mistral:
    res = mistral.fine_tuning.jobs.list(
        page=0, 
        page_size=100, 
        created_by_me=False
    )
    print(res)
```

#### cURL

```bash
curl https://api.mistral.ai/v1/fine_tuning/jobs \
  -X GET \
  -H 'Authorization: Bearer YOUR_APIKEY_HERE'
```

---

## POST /v1/fine_tuning/jobs

Create a new fine-tuning job that will be queued for processing.

### Request Body

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model | string | Yes | Model name to fine-tune. Options: "ministral-3b-latest", "ministral-8b-latest", "open-mistral-7b", "open-mistral-nemo", "mistral-small-latest", "mistral-medium-latest", "mistral-large-latest", "pixtral-12b-latest", "codestral-latest" |
| job_type | string | Yes | Job type: "completion" or "classifier" |
| training_files | array[TrainingFile] | Yes | List of training files |
| validation_files | array[string] | No | List of validation file IDs |
| auto_start | boolean | No | If false, returns metadata without starting the job |
| hyperparameters | object | No | Training hyperparameters |
| invalid_sample_skip_percentage | number | 0 | Percentage of invalid samples to skip |
| classifier_targets | array[ClassifierTargetIn] | No | Classifier-specific targets |
| integrations | array[WandbIntegration] | No | List of integrations to enable |
| repositories | array[GithubRepositoryIn] | No | GitHub repositories |
| suffix | string | No | Suffix added to fine-tuned model name |

### Response Types

- **CompletionJobOut**: Completion job response object
- **ClassifierJobOut**: Classifier job response object  
- **LegacyJobMetadataOut**: Metadata response when auto_start is false

### Code Examples

#### JavaScript

```javascript
import { Mistral } from "@mistralai/mistralai";

const mistral = new Mistral({
  apiKey: "MISTRAL_API_KEY",
});

async function createJob() {
  const result = await mistral.fineTuning.jobs.create({
    model: "ministral-3b-latest",
    hyperparameters: {
      learningRate: 0.0001,
    },
    training_files: ["file_id_1", "file_id_2"]
  });

  console.log(result);
}

createJob();
```

#### Python

```python
from mistralai import Mistral
import os

with Mistral(
    api_key=os.getenv("MISTRAL_API_KEY", ""),
) as mistral:
    res = mistral.fine_tuning.jobs.create(
        model="ministral-3b-latest",
        hyperparameters={
            "learning_rate": 0.0001,
        },
        invalid_sample_skip_percentage=0,
        training_files=["file_id_1", "file_id_2"]
    )
    print(res)
```

#### cURL

```bash
curl https://api.mistral.ai/v1/fine_tuning/jobs \
  -X POST \
  -H 'Authorization: Bearer YOUR_APIKEY_HERE' \
  -H 'Content-Type: application/json' \
  -d '{
    "hyperparameters": {
      "learning_rate": 0.0001
    },
    "model": "ministral-3b-latest",
    "training_files": ["file_id_1", "file_id_2"]
  }'
```

#### Response Example

```json
{
  "auto_start": false,
  "created_at": 87,
  "hyperparameters": {
    "learning_rate": 0.0001
  },
  "id": "ipsum eiusmod",
  "model": "ministral-3b-latest",
  "modified_at": 14,
  "status": "QUEUED",
  "training_files": [
    "consequat do"
  ]
}
```

---

## GET /v1/fine_tuning/jobs/{job_id}

Retrieve fine-tuning job details by its UUID.

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | string | Yes | UUID of the job to retrieve |

### Response Types

- **CompletionDetailedJobOut**: Detailed completion job object
- **ClassifierDetailedJobOut**: Detailed classifier job object

### Code Examples

#### JavaScript

```javascript
import { Mistral } from "@mistralai/mistralai";

const mistral = new Mistral({
  apiKey: "MISTRAL_API_KEY",
});

async function getJob() {
  const result = await mistral.fineTuning.jobs.get({
    jobId: "c167a961-ffca-4bcf-93ac-6169468dd389",
  });

  console.log(result);
}

getJob();
```

#### Python

```python
from mistralai import Mistral
import os

with Mistral(
    api_key=os.getenv("MISTRAL_API_KEY", ""),
) as mistral:
    res = mistral.fine_tuning.jobs.get(
        job_id="c167a961-ffca-4bcf-93ac-6169468dd389"
    )
    print(res)
```

#### cURL

```bash
curl https://api.mistral.ai/v1/fine_tuning/jobs/{job_id} \
  -X GET \
  -H 'Authorization: Bearer YOUR_APIKEY_HERE'
```

---

## POST /v1/fine_tuning/jobs/{job_id}/cancel

Request the cancellation of a fine-tuning job.

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | string | Yes | UUID of the job to cancel |

### Response Types

- **CompletionDetailedJobOut**: Detailed completion job object
- **ClassifierDetailedJobOut**: Detailed classifier job object

### Code Examples

#### JavaScript

```javascript
import { Mistral } from "@mistralai/mistralai";

const mistral = new Mistral({
  apiKey: "MISTRAL_API_KEY",
});

async function cancelJob() {
  const result = await mistral.fineTuning.jobs.cancel({
    jobId: "6188a2f6-7513-4e0f-89cc-3f8088523a49",
  });

  console.log(result);
}

cancelJob();
```

#### Python

```python
from mistralai import Mistral
import os

with Mistral(
    api_key=os.getenv("MISTRAL_API_KEY", ""),
) as mistral:
    res = mistral.fine_tuning.jobs.cancel(
        job_id="6188a2f6-7513-4e0f-89cc-3f8088523a49"
    )
    print(res)
```

#### cURL

```bash
curl https://api.mistral.ai/v1/fine_tuning/jobs/{job_id}/cancel \
  -X POST \
  -H 'Authorization: Bearer YOUR_APIKEY_HERE' \
  -H 'Content-Type: application/json'
```

---

## POST /v1/fine_tuning/jobs/{job_id}/start

Request the start of a validated fine-tuning job.

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | string | Yes | UUID of the job to start |

### Response Types

- **CompletionDetailedJobOut**: Detailed completion job object
- **ClassifierDetailedJobOut**: Detailed classifier job object

### Code Examples

#### JavaScript

```javascript
import { Mistral } from "@mistralai/mistralai";

const mistral = new Mistral({
  apiKey: "MISTRAL_API_KEY",
});

async function startJob() {
  const result = await mistral.fineTuning.jobs.start({
    jobId: "56553e4d-0679-471e-b9ac-59a77d671103",
  });

  console.log(result);
}

startJob();
```

#### Python

```python
from mistralai import Mistral
import os

with Mistral(
    api_key=os.getenv("MISTRAL_API_KEY", ""),
) as mistral:
    res = mistral.fine_tuning.jobs.start(
        job_id="56553e4d-0679-471e-b9ac-59a77d671103"
    )
    print(res)
```

#### cURL

```bash
curl https://api.mistral.ai/v1/fine_tuning/jobs/{job_id}/start \
  -X POST \
  -H 'Authorization: Bearer YOUR_APIKEY_HERE' \
  -H 'Content-Type: application/json'
```

---

## Related Endpoints

- [Files API](https://docs.mistral.ai/api/endpoint/files) - Upload and manage training files
- [Models API](https://docs.mistral.ai/api/endpoint/models) - List and manage fine-tuned models