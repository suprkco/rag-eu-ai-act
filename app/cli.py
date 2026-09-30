"""Terminal access to the same retrieval and generation paths as the API."""
import argparse
import json

from fastapi import HTTPException
from pydantic import ValidationError

from app.main import Question, ask


def render(result):
    lines = [f"rag / {result['mode']}", '', result['answer'], '', 'Sources']
    for index, source in enumerate(result['citations'], 1):
        lines.extend([f"[{index}] {source['title']}", f"    {source['url']}",
                      f"    {source['version']} | snapshot {source['snapshot_date']}"])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Search selected EU AI Act and GDPR articles in your terminal.')
    parser.add_argument('question', nargs='?')
    parser.add_argument('--mode', choices=['extractive', 'ollama'], default='extractive')
    parser.add_argument('--json', action='store_true', help='Emit machine-readable JSON; requires a question')
    args = parser.parse_args()
    if args.json and not args.question:
        parser.error('--json requires a question')

    def run(question):
        result = ask(Question(question=question, mode=args.mode))
        print(json.dumps(result, ensure_ascii=False) if args.json else render(result))

    if args.question:
        try:
            run(args.question)
        except (HTTPException, ValidationError) as error:
            parser.exit(1, f"Request failed: {getattr(error, 'detail', str(error))}\n")
        return
    print('rag / evidence explorer\n20 selected articles | extractive by default\n/quit to exit; each question is independent.\n')
    while True:
        try:
            question = input('> ').strip()
            if question in {'/quit', '/exit'}:
                break
            if question:
                run(question)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        except (HTTPException, ValidationError) as error:
            print(f"Request failed: {getattr(error, 'detail', str(error))}")


if __name__ == '__main__':
    main()
