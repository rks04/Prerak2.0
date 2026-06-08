from enum import Enum

class RuntimeMode(str, Enum):
    MOCK = "mock"
    OLLAMA = "ollama"
