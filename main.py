import json
import timeit
from gptcom import GPTCommunicator,SummarizationPrompter
from openai import OpenAI

# Load config and sample files
config_file = open("config.json")
sample_file = open("samples.json")

# Convert config and sample files into dictionaries
config = json.load(config_file)
samples = json.load(sample_file)

# Close files
config_file.close()
sample_file.close()

# Start timing operation
start_time = timeit.default_timer()

# Create a client connection to OpenAI API
client = OpenAI()

# Create a prompter to make requests
prompter = SummarizationPrompter(GPTCommunicator(client, "gpt-4"),config["prompts"]["summarizer"])

# Prompt OpenAI API for a summary and print it
message = prompter.requestSummary(samples["samples"][1])
print(message)

# Stop timing and print the elapsed time
end_time = timeit.default_timer() - start_time
print("Time Elapsed: {time} seconds".format(time=end_time))

