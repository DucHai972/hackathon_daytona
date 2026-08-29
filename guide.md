https://www.daytona.io/docs/
https://app.daytona.io/dashboard/onboarding

Get Started
Install and get your Sandboxes running.

Python
TypeScript
1
Install the SDK
Run the following command in your terminal to install the Daytona SDK:

pip install daytona

2
Create an API Key
This API key will have permissions to only manage Sandboxes. For full API permissions, head to the Keys page.

dtn********************eac (in .env file)
3
Create a Sandbox
The example below will create a Sandbox and run a simple code snippet:

from daytona import Daytona, DaytonaConfig

# Define the configuration
config = DaytonaConfig(api_key="your-api-key")

# Initialize the Daytona client
daytona = Daytona(config)

# Create the Sandbox instance
sandbox = daytona.create()

# Run the code securely inside the Sandbox
response = sandbox.process.code_run('print("Hello World from code!")')
if response.exit_code != 0:
  print(f"Error: {response.exit_code} {response.result}")
else:
    print(response.result)

4
Run the Example
Run the following command in your terminal to run the example:

python main.py

5
That's It
It's as easy as that. For more examples check out the Docs.