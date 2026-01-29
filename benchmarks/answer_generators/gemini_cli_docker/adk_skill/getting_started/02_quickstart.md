# Quickstart

This quickstart guides you through installing the Agent Development Kit (ADK),
setting up a basic agent with multiple tools, and running it locally either in the terminal or in the interactive, browser-based dev UI.

This quickstart assumes a local IDE (VS Code, PyCharm, IntelliJ IDEA, etc.)
with Python 3.10+ or Java 17+ and terminal access. This method runs the
application entirely on your machine and is recommended for internal development.

## 1. Set up Environment & Install ADK

=== "Python"

    Create & Activate Virtual Environment (Recommended):

    ```bash
    # Create
    python -m venv .venv
    # Activate (each new terminal)
    # macOS/Linux: source .venv/bin/activate
    # Windows CMD: .venv\Scripts\activate.bat
    # Windows PowerShell: .venv\Scripts\Activate.ps1
    ```

    Install ADK:

    ```bash
    pip install google-adk
    ```

=== "Java"

    To install ADK and setup the environment, proceed to the following steps.

## 2. Create Agent Project

### Project structure

=== "Python"

    You will need to create the following project structure:

    ```console
    parent_folder/
        multi_tool_agent/
            __init__.py
            agent.py
            .env
    ```

    Create the folder `multi_tool_agent`:

    ```bash
    mkdir multi_tool_agent/
    ```

    ### `__init__.py`

    Now create an `__init__.py` file in the folder:

    ```shell
    echo "from . import agent" > multi_tool_agent/__init__.py
    ```

    Your `__init__.py` should now look like this:

    ```python
    from . import agent

    ```

    ### `agent.py`

    Create an `agent.py` file in the same folder:

    ```shell
    touch multi_tool_agent/agent.py
    ```

    Copy and paste the following code into `agent.py`:

    ```python
    import datetime
    from zoneinfo import ZoneInfo
    from google.adk.agents import Agent

    def get_weather(city: str) -> dict:
        """Retrieves the current weather report for a specified city.

        Args:
            city (str): The name of the city for which to retrieve the weather report.

        Returns:
            dict: status and result or error msg.
        """
        if city.lower() == "new york":
            return {
                "status": "success",
                "report": (
                    "The weather in New York is sunny with a temperature of 25 degrees"
                    " Celsius (77 degrees Fahrenheit)."
                ),
            }
        else:
            return {
                "status": "error",
                "error_message": f"Weather information for '{city}' is not available.",
            }


def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.

    Returns:
        dict: status and result or error msg.
    """ 

    if city.lower() == "new york":
        tz_identifier = "America/New_York"
    else:
        return {
            "status": "error",
            "error_message": (
                f"Sorry, I don't have timezone information for {city}."
            ),
        }

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = (
        f'The current time in {city} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
    )
    return {"status": "success", "report": report}


root_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.5-flash",
    description=(
        "Agent to answer questions about the time and weather in a city."
    ),
    instruction=(
        "You are a helpful agent who can answer user questions about the time and weather in a city."
    ),
    tools=[get_weather, get_current_time],
)

    ```

    ### `.env`

    Create a `.env` file in the same folder:

    ```shell
    touch multi_tool_agent/.env
    ```

    More instructions about this file are described in the next section on [Set up the model].

=== "Java"

    Java projects generally feature the following project structure:

    ```console
    project_folder/
    ├── pom.xml (or build.gradle)
    ├── src/
    ├──     └── main/
    │       └── java/
    │           └── agents/
    │               └── multitool/
    └── test/
    ```

    ### Create `MultiToolAgent.java`

    Create a `MultiToolAgent.java` source file in the `agents.multitool` package
    in the `src/main/java/agents/multitool/` directory.

    Copy and paste the following code into `MultiToolAgent.java`:

    ```java
    package agents.multitool;
    
    import com.google.adk.agents.Agent;
    import com.google.adk.agents.BaseAgent;
    import com.google.adk.tools.FunctionTool;
    import com.google.adk.tools.ToolContext;
    import java.time.ZoneId;
    import java.time.ZonedDateTime;
    import java.time.format.DateTimeFormatter;
    import java.util.List;
    import java.util.Map;
    
    public class MultiToolAgent {
    
        public static BaseAgent ROOT_AGENT = createAgent();
    
        private static BaseAgent createAgent() {
            return new Agent.Builder()
                .setName("weather_time_agent")
                .setModel("gemini-2.5-flash")
                .setDescription("Agent to answer questions about the time and weather in a city.")
                .setInstruction("You are a helpful agent who can answer user questions about the time and weather in a city.")
                .setTools(List.of(
                    FunctionTool.create("get_weather", "Retrieves the current weather report for a specified city.", MultiToolAgent.class),
                    FunctionTool.create("get_current_time", "Returns the current time in a specified city.", MultiToolAgent.class)
                ))
                .build();
        }
    
        public static Map<String, Object> get_weather(String city, ToolContext toolContext) {
            if (city.equalsIgnoreCase("new york")) {
                return Map.of(
                    "status", "success",
                    "report", "The weather in New York is sunny with a temperature of 25 degrees Celsius (77 degrees Fahrenheit)."
                );
            } else {
                return Map.of(
                    "status", "error",
                    "error_message", String.format("Weather information for '%s' is not available.", city)
                );
            }
        }
    
        public static Map<String, Object> get_current_time(String city, ToolContext toolContext) {
            String tzIdentifier;
            if (city.equalsIgnoreCase("new york")) {
                tzIdentifier = "America/New_York";
            } else {
                return Map.of(
                    "status", "error",
                    "error_message", String.format("Sorry, I don't have timezone information for %s.", city)
                );
            }
    
            ZoneId tz = ZoneId.of(tzIdentifier);
            ZonedDateTime now = ZonedDateTime.now(tz);
            String report = String.format("The current time in %s is %s", city, now.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss z"))); 
            return Map.of("status", "success", "report", report);
        }
    }
    ```

## 3. Set up the model

Your agent's ability to understand user requests and generate responses is
powered by a Large Language Model (LLM). Your agent needs to make secure calls
to this external LLM service, which requires authentication credentials. Without
valid authentication, the LLM service will deny the agent's requests, and the
agent will be unable to function.

=== "Gemini - Google AI Studio"
    1. Get an API key from [Google AI Studio](https://aistudio.google.com/apikey).
    2. When using Python, open the **`.env`** file located inside (`multi_tool_agent/`)
    and copy-paste the following code.

        ```env
        GOOGLE_GENAI_USE_VERTEXAI=FALSE
        GOOGLE_API_KEY=PASTE_YOUR_ACTUAL_API_KEY_HERE
        ```

        When using Java, define environment variables:

        ```console
        export GOOGLE_GENAI_USE_VERTEXAI=FALSE
        export GOOGLE_API_KEY=PASTE_YOUR_ACTUAL_API_KEY_HERE
        ```

    3. Replace `PASTE_YOUR_ACTUAL_API_KEY_HERE` with your actual `API KEY`.

=== "Gemini - Google Cloud Vertex AI"
    1. You need an existing
    [Google Cloud](https://cloud.google.com/?e=48754805&hl=en) account and a
    project.
        * Set up a
          [Google Cloud project](https://cloud.google.com/vertex-ai/generative-ai/docs/start/quickstarts/quickstart-multimodal#setup-gcp)
        * Set up the
          [gcloud CLI](https://cloud.google.com/vertex-ai/generative-ai/docs/start/quickstarts/quickstart-multimodal#setup-local)
        * Authenticate to Google Cloud, from the terminal by running
          `gcloud auth login`.
        * [Enable the Vertex AI API](https://console.cloud.google.com/flows/enableapi?apiid=aiplatform.googleapis.com).
    2. When using Python, open the **`.env`** file located inside (`multi_tool_agent/`). Copy-paste
    the following code and update the project ID and location.

        ```env
        GOOGLE_GENAI_USE_VERTEXAI=TRUE
        GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
        GOOGLE_CLOUD_LOCATION=LOCATION
        ```

        When using Java, define environment variables:

        ```console
        export GOOGLE_GENAI_USE_VERTEXAI=TRUE
        export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
        export GOOGLE_CLOUD_LOCATION=LOCATION
        ```

## 4. Run Your Agent

=== "Python"

    Using the terminal, navigate to the parent directory of your agent project
    (e.g. using `cd ..`):

    ```console
    parent_folder/
        multi_tool_agent/
            __init__.py
            agent.py
            .env
    ```

    There are multiple ways to interact with your agent:

    === "Dev UI (adk web)"
        Run the following command to launch the **dev UI**.

        ```shell
        adk web
        ```

    === "Terminal (adk run)"

        Run the following command, to chat with your Weather agent.

        ```
        adk run multi_tool_agent
        ```

    === "API Server (adk api_server)"

        `adk api_server` enables you to create a local FastAPI server in a single
        command, enabling you to test local cURL requests before you deploy your
        agent.

=== "Java"

    Using the terminal, navigate to the parent directory of your agent project
    (e.g. using `cd ..`):

    ```console
    project_folder/
    ├── pom.xml (or build.gradle)
    ├── src/
    ├──     └── main/
    │       └── java/
    │           └── agents/
    │               └── multitool/
    │                   └── MultiToolAgent.java
    └── test/
    ```

    === "Dev UI"

        Run the following command from the terminal to launch the Dev UI.

        ```console
        mvn exec:java \
            -Dexec.mainClass="com.google.adk.web.AdkWebServer" \
            -Dexec.args="--adk.agents.source-dir=src/main/java" \
            -Dexec.classpathScope="compile"
        ```

    === "Maven"

        With Maven, run the `main()` method of your Java class
        with the following command:

        ```console
        mvn compile exec:java -Dexec.mainClass="agents.multitool.MultiToolAgent"
        ```

    === "Gradle"

        With Gradle, the `build.gradle` or `build.gradle.kts` build file
        should have the following Java plugin in its `plugins` section:

        ```groovy
        plugins {
            id("java")
        }
        ```

        Then, elsewhere in the build file, at the top-level,
        create a new task to run the `main()` method of your agent:

        ```groovy
        task runAgent(type: JavaExec) {
            classpath = sourceSets.main.runtimeClasspath
            mainClass = "agents.multitool.MultiToolAgent"
        }
        ```

        Finally, on the command-line, run the following command:

        ```console
        gradle runAgent
        ```
