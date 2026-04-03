import re
import sys


def extract():
    input = sys.stdin.read()

    tags = re.findall(r"<\s*([\w-]+)[^>]*>([\s\S]*?)<\s*\/\s*\1\s*>", input)

    if not tags:
        print("No tags")
        exit

    for tag in tags:
        subtags = extract_subtags(tag[1])
        print(f"{tag[0]}{':' if subtags else ''}")
        if subtags:
            for subtag in subtags:
                print(f" - {subtag}")


def extract_subtags(input: str) -> list[str]:
    return re.findall(r"<\s*([\w-]+)[^>]*>[\s\S]*?<\s*\/\s*\1\s*>", input)


if __name__ == "__main__":
    extract()
