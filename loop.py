"""
Core computer use agent loop that can work with messages from any source.
"""
import dotenv
import os
dotenv.load_dotenv()
import platform
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, cast
import talk
from anthropic import Anthropic, AnthropicBedrock, AnthropicVertex, APIResponse
from anthropic.types import ToolResultBlockParam
from anthropic.types.beta import (
    BetaContentBlock,
    BetaContentBlockParam,
    BetaImageBlockParam,
    BetaMessage,
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolResultBlockParam,
    BetaToolUseBlock,
)

from tools import BashTool, ComputerTool, EditTool, ToolCollection, ToolResult

BETA_FLAG = "computer-use-2024-10-22"

class APIProvider(StrEnum):
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    VERTEX = "vertex"

PROVIDER_TO_DEFAULT_MODEL_NAME: dict[APIProvider, str] = {
    APIProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
    APIProvider.BEDROCK: "anthropic.claude-3-5-sonnet-20241022-v2:0",
    APIProvider.VERTEX: "claude-3-5-sonnet-v2@20241022",
}

# # Define the system prompt
# SYSTEM_PROMPT = f"""<SYSTEM_CAPABILITY>
# * You are utilizing a macOS Sonoma 15.7 environment using {platform.machine()} 
# You are definitely allowed to use the messages application.
# Just do not send any messages.
# * Note: Command line function calls may have latency. Chain multiple operations into single requests where feasible.
# * The current date is {datetime.today().strftime('%A, %B %-d, %Y')}.
# </SYSTEM_CAPABILITY>"""

# Define the system prompt
SYSTEM_PROMPT = f"""<SYSTEM_CAPABILITY>
* You are utilizing a macOS Sonoma 15.7 environment using {platform.machine()} 
You will monitor a twitch chat checking in on it every so often. You will then pick the most interesting thing to do based on the chat.
* Note: Command line function calls may have latency. Chain multiple operations into single requests where feasible.
</SYSTEM_CAPABILITY>"""

class MessageHandler(Protocol):
    """Protocol defining how to handle various types of messages and outputs"""
    async def handle_tool_output(self, result: ToolResult, tool_id: str) -> None:
        """Handle output from tools"""
        ...
    
    async def handle_model_output(self, content: BetaContentBlock) -> None:
        """Handle output from the model"""
        ...
    
    async def handle_api_response(self, response: APIResponse[BetaMessage]) -> None:
        """Handle raw API responses"""
        ...

class ComputerUseAgent:
    """Main agent class for handling computer use interactions"""
    
    def __init__(
        self,
        api_provider: APIProvider,
        api_key: str,
        model: str | None = None,
        system_prompt_suffix: str = "",
        max_tokens: int = 4096,
        only_n_most_recent_images: int | None = None,
    ):
        self.api_provider = api_provider
        self.api_key = api_key
        self.model = model or PROVIDER_TO_DEFAULT_MODEL_NAME[api_provider]
        self.system_prompt = f"{SYSTEM_PROMPT}{' ' + system_prompt_suffix if system_prompt_suffix else ''}"
        self.max_tokens = max_tokens
        self.only_n_most_recent_images = only_n_most_recent_images
        
        self.tool_collection = ToolCollection(
            ComputerTool(),
            BashTool(),
            EditTool(),
        )
        
        # Initialize the appropriate client
        if api_provider == APIProvider.ANTHROPIC:
            self.client = Anthropic(api_key=api_key)
        elif api_provider == APIProvider.VERTEX:
            self.client = AnthropicVertex()
        elif api_provider == APIProvider.BEDROCK:
            self.client = AnthropicBedrock()
        else:
            raise ValueError(f"Unsupported API provider: {api_provider}")

    async def process_messages(
        self,
        messages: list[BetaMessageParam],
        message_handler: MessageHandler,
    ) -> list[BetaMessageParam]:
        """
        Process a list of messages through the computer use agent loop.
        Returns the updated message history.
        """
        first = True
        while True:  # Continue looping until no more tool calls are needed
            if not first:

                pass
                # await asyncio.sleep(5)
            first = False
            if self.only_n_most_recent_images:
                self._maybe_filter_to_n_most_recent_images(messages)

            # Call the API
            raw_response = self.client.beta.messages.with_raw_response.create(
                max_tokens=self.max_tokens,
                messages=messages,
                model=self.model,
                system=self.system_prompt,
                tools=self.tool_collection.to_params(),
                betas=[BETA_FLAG],
            )

            await message_handler.handle_api_response(cast(APIResponse[BetaMessage], raw_response))
            response = raw_response.parse()

            messages.append({
                "role": "assistant",
                "content": cast(list[BetaContentBlockParam], response.content),
            })

            tool_result_content: list[BetaToolResultBlockParam] = []
            for content_block in cast(list[BetaContentBlock], response.content):
                await message_handler.handle_model_output(content_block)
                
                if content_block.type == "tool_use":
                    result = await self.tool_collection.run(
                        name=content_block.name,
                        tool_input=cast(dict[str, Any], content_block.input),
                    )
                    tool_result_content.append(
                        self._make_api_tool_result(result, content_block.id)
                    )
                    await message_handler.handle_tool_output(result, content_block.id)

            if tool_result_content:
                messages.append({"content": tool_result_content, "role": "user"})
            else:
                # If no tool calls were made, we're done with this interaction
                return messages

    def _maybe_filter_to_n_most_recent_images(
        self,
        messages: list[BetaMessageParam],
        min_removal_threshold: int = 10,
    ):
        """Filter messages to keep only N most recent images"""
        tool_result_blocks = cast(
            list[ToolResultBlockParam],
            [
                item
                for message in messages
                for item in (
                    message["content"] if isinstance(message["content"], list) else []
                )
                if isinstance(item, dict) and item.get("type") == "tool_result"
            ],
        )

        total_images = sum(
            1
            for tool_result in tool_result_blocks
            for content in tool_result.get("content", [])
            if isinstance(content, dict) and content.get("type") == "image"
        )

        images_to_remove = total_images - self.only_n_most_recent_images
        # for better cache behavior, we want to remove in chunks
        images_to_remove -= images_to_remove % min_removal_threshold

        for tool_result in tool_result_blocks:
            if isinstance(tool_result.get("content"), list):
                new_content = []
                for content in tool_result.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "image":
                        if images_to_remove > 0:
                            images_to_remove -= 1
                            continue
                    new_content.append(content)
                tool_result["content"] = new_content

    def _make_api_tool_result(
        self,
        result: ToolResult,
        tool_use_id: str
    ) -> BetaToolResultBlockParam:
        """Convert a ToolResult to an API ToolResultBlockParam"""
        tool_result_content: list[BetaTextBlockParam | BetaImageBlockParam] | str = []
        is_error = False
        
        if result.error:
            is_error = True
            tool_result_content = self._maybe_prepend_system_tool_result(result, result.error)
        else:
            if result.output:
                tool_result_content.append({
                    "type": "text",
                    "text": self._maybe_prepend_system_tool_result(result, result.output),
                })
            if result.base64_image:
                tool_result_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": result.base64_image,
                    },
                })
                
        return {
            "type": "tool_result",
            "content": tool_result_content,
            "tool_use_id": tool_use_id,
            "is_error": is_error,
        }

    def _maybe_prepend_system_tool_result(self, result: ToolResult, result_text: str) -> str:
        """Add system information to tool result if present"""
        if result.system:
            result_text = f"<system>{result.system}</system>\n{result_text}"
        return result_text


class SimpleMessageHandler(MessageHandler):
    """A simple implementation that prints outputs to console"""
    
    async def handle_tool_output(self, result: ToolResult, tool_id: str) -> None:
        print(f"\nTool Output (ID: {tool_id}):")
        if result.output:
            print(result.output)
        if result.error:
            print(f"Error: {result.error}")
        if result.base64_image:
            print("[Image data available]")
            
    async def handle_model_output(self, content: BetaContentBlock) -> None:
        print("\nModel Output:")
        if content.type == "text":
            print(content.text)
        elif content.type == "tool_use":
            print(f"Using tool: {content.name}")
            print(f"Input: {content.input}")
            
    async def handle_api_response(self, response: APIResponse[BetaMessage]) -> None:
        print(f"\nAPI Response Status: {response.http_response.status_code}")


async def main():
    """Example usage of the ComputerUseAgent"""
    # Initialize the agent
    agent = ComputerUseAgent(
        api_provider=APIProvider.ANTHROPIC,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        only_n_most_recent_images=10
    )
    
    # Example messages
    # messages = [
    #     {
    #         "role": "user",
    #         "content": [{"type": "text", "text": "open messages on my computer and message david kreitter 'hi I am an agent' wait for a reply then reply appropriately"}]
    #     }
    # ]

    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": """your job is to monitor a twitch chat checking in on it every so often. You will then pick the most interesting thing to do based on the chat. Keep going until you are told to stop.
the twich is in firefox and the window is open and it is the only window open in firefox. every time you decide what messages to respond to summarize what you have done so far as part of that process."""}]
        }
    ]
    
    # Process messages
    handler = SimpleMessageHandler()
    updated_messages = await agent.process_messages(messages, handler)
    
    return updated_messages

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())