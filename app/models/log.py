from dataclasses import dataclass


@dataclass
class LogRecord:
    id: int
    filename: str
    status: str

