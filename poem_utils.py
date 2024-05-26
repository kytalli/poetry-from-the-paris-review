import json
import attr
import os

@attr.s
class Poem:
    title = attr.ib()
    author = attr.ib()
    body = attr.ib()
    issue = attr.ib()
    sent_date = attr.ib()
    msg_id = attr.ib()

    def to_json(self):
        return json.dumps(attr.asdict(self), indent=4)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        return cls(**data)
    
    @staticmethod
    def save_poem_to_file(poem, filename, directory="saved_poems"):
        import os
        if not os.path.exists(directory):
            os.makedirs(directory)
        file_path = os.path.join(directory, filename)
        with open(file_path, 'w') as f:
            f.write(poem.to_json())

    @staticmethod
    def load_poem_from_file(filename, directory="saved_poems"):
        file_path = os.path.join(directory, filename)
        with open(file_path, 'r') as f:
            json_str = f.read()
        return Poem.from_json(json_str)