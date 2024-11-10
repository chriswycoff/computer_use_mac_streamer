import supabase
import os
from supabase import create_client, Client
from typing import Optional, TypedDict

# Add these near the top of the file with other imports
class QueueMessage(TypedDict):
    id: int
    message: str
    recipient: str
    is_processed: bool
    created_at: str
    processed_at: Optional[str]

class SupabaseManager:
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        self.client: Client = create_client(supabase_url, supabase_key)

    async def add_to_queue(self, message: str, recipient: str) -> dict:
        """Add a new message to the queue"""
        data = {
            "message": message,
            "recipient": recipient,
            "is_processed": False
        }
        
        response = self.client.table('message_queue').insert(data).execute()
        return response.data[0]

    async def get_unprocessed_messages(self) -> list[QueueMessage]:
        """Get all unprocessed messages from the queue"""
        response = self.client.table('message_queue')\
            .select('*')\
            .eq('is_processed', False)\
            .order('created_at')\
            .execute()
        return response.data

    async def mark_as_processed(self, message_id: int) -> None:
        """Mark a message as processed"""
        self.client.table('message_queue')\
            .update({"is_processed": True, "processed_at": datetime.now().isoformat()})\
            .eq('id', message_id)\
            .execute()

# Modify the ComputerUseAgent class to include Supabase functionality
class ComputerUseAgent:
    def __init__(
        self,
        api_provider: APIProvider,
        api_key: str,
        model: str | None = None,
        system_prompt_suffix: str = "",
        max_tokens: int = 4096,
        only_n_most_recent_images: int | None = None,
    ):
        # ... (keep existing initialization code) ...
        self.supabase_manager = SupabaseManager()

    async def process_queue(self, message_handler: MessageHandler) -> None:
        """Process all unprocessed messages in the queue"""
        unprocessed_messages = await self.supabase_manager.get_unprocessed_messages()
        
        for queue_message in unprocessed_messages:
            messages = [
                {
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": f"open messages on my computer and message {queue_message['recipient']} '{queue_message['message']}' wait for a reply then reply appropriately"
                    }]
                }
            ]
            
            try:
                await self.process_messages(messages, message_handler)
                await self.supabase_manager.mark_as_processed(queue_message['id'])
            except Exception as e:
                print(f"Error processing message {queue_message['id']}: {str(e)}")

# Modify the main function to include queue processing
async def main():
    """Example usage of the ComputerUseAgent with queue processing"""
    agent = ComputerUseAgent(
        api_provider=APIProvider.ANTHROPIC,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        only_n_most_recent_images=10
    )
    
    # Process the queue
    handler = SimpleMessageHandler()
    await agent.process_queue(handler)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())