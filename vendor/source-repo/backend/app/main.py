import sys
import json
from services.database.query import query_companies, query_data_with_generated_sql

def handler(question, agentSelection="None"):
    if question.lower() == 'q':
        return "Goodbye!"
    if agentSelection.get("stockAgent"):
        return query_companies(question)
    elif agentSelection.get("housingAgent"):
        return query_data_with_generated_sql(question)
    else:
        return "Unknown agent selected."

if __name__ == "__main__":
    """
    Example command-line usage:
      python main.py "What is the stock price of XYZ?" '{"stockAgent": true, "housingAgent": false}'

    or run it with no arguments for a simple interactive test.
    """
    if len(sys.argv) > 2:
        question = sys.argv[1]
        agentSelectionStr = sys.argv[2]
        try:
            agentSelection = json.loads(agentSelectionStr)
        except json.JSONDecodeError:
            agentSelection = {}
        print(handler(question, agentSelection))
    else:
        print("Interactive mode. Type 'q' to quit.\n")
        while True:
            question = input("Your question: ")
            if question.lower() == 'q':
                print("Goodbye!")
                break
            testAgentSelection = {"stockAgent": False, "housingAgent": True}
            answer = handler(question, testAgentSelection)
            print(f"Answer: {answer}\n")