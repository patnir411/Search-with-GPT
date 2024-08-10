from gpt_caller import gpt_call_with_function

def main():
    print("Welcome to the GPT API caller with web search capability!")
    print("Type 'exit' to quit the program.")

    while True:
        user_input = input("\nEnter your query: ")

        if user_input.lower() == 'exit':
            print("Thank you for using the GPT API caller. Goodbye!")
            break

        response = gpt_call_with_function(user_input)
        print("\nGPT Response:")
        print(response)

if __name__ == "__main__":
    main()
    