# tgtg-items-updater
Fetches items from TooGoodToGo on kafka message and put them on other kafka topic.

## How it works
1. message appears on kafka topic `KAFKA_TRIGGER_TOPIC`
2. TooGoodToGo items are fetched using tgtg library
3. items are pushed to kafka topic `KAFKA_OUTPUT_TOPIC`

## Run
In each case you need first to create 2 files: `credentials.json` containing TGTG login credentials, and `query_params.json` with TGTG querying options.

### `credentials.json`
The easiest way to obtain file with credentials is to log in using TGTG client in python using below script.
```python
import json
from tgtg import TgtgClient

client = TgtgClient(email=<your_email>)
credentials = client.login()
# now go to your email box on computer, open email from TooGoodToGo and click button to confirm login
with open("credentials.json", "w") as f:
    f.write(json.dumps(credentials))
```

### `query_params.json`
This file should contain parameters for querying items from TooGoodToGo as below:
```json
{
    "latitude": 0,
    "longitude": 0,
    "radius": 5, // in kilometers
    "favorites_only": false
}
```

### Locally
 Set variables directly in environment or in `.env` file.

```bash
KAFKA_BOOTSTRAP_SERVERS="broker:9092"
KAFKA_TRIGGER_TOPIC="tick"
KAFKA_OUTPUT_TOPIC="available_items"
KAFKA_TIMEOUT=10

TGTG_CREDENTIALS_FILE="credentials.json"
TGTG_QUERY_PARAMS_FILE="query_params.json"
TGTG_SKIP_NOT_AVAILABLE_ITEMS=1
```

Run `main.py` file.

```bash
python main.py
```

### Using Docker
```bash
docker run \
    --network host \
    --volume /directory/with/credentials/and/query/params/files:/src \
    -e KAFKA_BOOTSTRAP_SERVERS="broker:9092" \
    -e KAFKA_TRIGGER_TOPIC="tick" \
    -e KAFKA_OUTPUT_TOPIC="available_items" \
    -e KAFKA_TIMEOUT=10 \
    -e TGTG_CREDENTIALS_FILE="credentials.json" \
    -e TGTG_QUERY_PARAMS_FILE="query_params.json" \
    -e TGTG_SKIP_NOT_AVAILABLE_ITEMS=1 \
    norbiox/tgtg-items-updater
```