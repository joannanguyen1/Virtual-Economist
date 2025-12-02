from app import main
import json
import argparse
print("Starting local.py")

def define_args():
    parser = argparse.ArgumentParser(prog="local", description="Run the application locally.")
    parser.add_argument("filename", nargs="?",type=str, help="The filename to process", default="mock_files/human_message.json")
    return parser

def local(args):
    try:
        with open(args.filename, "r", encoding="utf-8") as read_file:
            MOCK_DATA = json.load(read_file)
            print("MOCK_DATA loaded:", MOCK_DATA)
            message = MOCK_DATA["message"]
            print("Message:", message)
    except Exception as e:
        print(f"Error loading data: {e}")
        return
    try:
        print("Calling main.handler with message...")
        main.handler(message)
    except Exception as e:
        print(f"Error calling main.handler: {e}")


if __name__ == "__main__":
    args = define_args().parse_args()
    local(args)