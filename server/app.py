"""
Server entry point for openenv validate / multi-mode deployment.
"""
import uvicorn
from app import app  # noqa: F401


def main():
    uvicorn.run("app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
