import json
import timeit
from gptcom import GPTCommunicator,SummarizationPrompter
from openai import OpenAI

# config_file = open("config.json")
sample_file = open("samples.json")

# config = json.load(config_file)
samples = json.load(sample_file)

start_time = timeit.default_timer()

client = OpenAI()
prompter = SummarizationPrompter(GPTCommunicator(client, "gpt-4"))

message = prompter.requestSummary(samples["samples"][1])
print(message)

end_time = timeit.default_timer() - start_time
print("Time Elapsed: {time} seconds".format(time=end_time))

# config_file.close()
sample_file.close()
