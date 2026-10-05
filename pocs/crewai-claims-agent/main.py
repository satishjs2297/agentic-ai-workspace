"""Run the CrewAI claims agent from PowerShell."""

import os
import sys

from dotenv import load_dotenv

from agent import process_instruction


def main() -> None:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is missing. Copy .env.example to .env and add your key.")

    instruction = " ".join(sys.argv[1:]).strip()
    if not instruction:
        instruction = input("Instruction: ").strip()
    if not instruction:
        raise SystemExit("Please provide an instruction.")

    print(process_instruction(instruction))


if __name__ == "__main__":
    main()
