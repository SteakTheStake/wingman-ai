import json
from typing import Literal
from wingmen.wingman import Wingman
from services.open_ai import OpenAi


class OpenAiWingman(Wingman):
    def __init__(self, name: str, config: dict[str, any]):
        super().__init__(name, config)
        self.openai = OpenAi(self.config["openai"]["api_key"])
        self.messages = [
            {
                "role": "system",
                "content": self.config["openai"].get("context"),
            },
        ]

    def _transcribe(self, audio_input_wav: str) -> str:
        transcript = self.openai.transcribe(audio_input_wav)
        return transcript.text

    def _process_transcript(self, transcript: str) -> str:
        self.messages.append({"role": "user", "content": transcript})

        completion = self.openai.ask(
            messages=self.messages,
            tools=self.__get_tools(),
        )

        response_message = completion.choices[0].message
        tool_calls = response_message.tool_calls
        content = response_message.content

        self.messages.append(response_message)

        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                if function_name == "execute_command":
                    function_response = self.__execute_command(**function_args)

                if function_response:
                    self.messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        }
                    )

            second_response = self.openai.ask(
                messages=self.messages,
                model="gpt-3.5-turbo-1106",
            )
            second_content = second_response.choices[0].message.content
            print(second_content)
            self.messages.append(second_response.choices[0].message)
            self._play_audio(second_content)

        return content

    def _finish_processing(self, text: str):
        if text:
            self._play_audio(text)

    def _play_audio(self, text: str):
        response = self.openai.speak(text)
        self.audio_player.stream(response.content)

    def __get_tools(self) -> list[dict[str, any]]:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "execute_command",
                    "description": "Executes a command",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command_name": {
                                "type": "string",
                                "description": "The command to execute",
                                "enum": [
                                    command["name"]
                                    for command in self.config["commands"]
                                ],
                            },
                        },
                        "required": ["command_name"],
                    },
                },
            },
        ]
        return tools

    def __execute_command(self, command_name) -> Literal["Ok"]:
        print(f">>>{command_name}<<<")
        return "Ok"