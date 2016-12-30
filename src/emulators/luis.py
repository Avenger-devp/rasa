class LUISEmulator(object):
    def __init__(self):
        self.name = 'luis'

    def normalise_request_json(self, data):
        _data = {}
        _data["text"] = data["q"][0]
        if "model" not in data:
            _data["model"] = "default"
        else:
            _data["model"] = data["model"][0]
        return _data

    def normalise_response_json(self, data):
        return {
            "query": data["text"],
            "topScoringIntent": {
                "intent": "inform",
                "score": None
            },
            "entities": [
                {
                    "entity": e["value"],
                    "type": e["entity"],
                    "startIndex": None,
                    "endIndex": None,
                    "score": None
                } for e in data["entities"]
                ]
        }
